"""PDF manuscript -> structured blocks (paragraphs, block quotes, headings, footnotes).

Built for word-processor exports (double-spaced essays with footnotes). Reads character
positions, so footnote markers, italics and block quotes survive.
Run with python3 -I; this directory is added to sys.path by the caller.
"""
import re, html, statistics
from collections import Counter
import fitz
from rows import page_chars, cluster_rows

LIG = {'ﬁ': 'fi', 'ﬂ': 'fl', 'ﬀ': 'ff', 'ﬃ': 'ffi', 'ﬄ': 'ffl', ' ': ' ', ' ': ' ', '­': ''}


def style_of(ch):
    f = ch['font']
    it = ('Ital' in f) or ('Oblique' in f) or ('CMTI' in f) or bool(ch['flags'] & 2)
    bd = ('Bold' in f) or ('CMBX' in f) or bool(ch['flags'] & 16)
    return ('b' if bd else '') + ('i' if it else '')


def runs_from_chars(chars, sup_chars=()):
    """chars: main-size chars of a row; sup_chars: small raised chars to splice in by x position.
    Returns list of (style, text). Style 'sup' marks a footnote reference."""
    # raised digits that sit together form one marker; place it where its first digit starts
    sups = sorted(sup_chars, key=lambda c: c['x0'])
    anchor = {}
    start = None; prev_s = None
    for c in sups:
        if prev_s is not None and c['x0'] - prev_s['x1'] < 0.6 * c['size']:
            anchor[id(c)] = start + 0.0001 * (len([k for k in anchor.values() if int(k) == int(start)]) + 1)
        else:
            start = c['x0']; anchor[id(c)] = start
        prev_s = c
    # word processors reserve a blank the width of the marker in the main text; drop that blank
    def under_marker(c):
        if c['c'] != ' ': return False
        w = max(c['x1'] - c['x0'], 0.01)
        return any(min(c['x1'], s['x1']) - max(c['x0'], s['x0']) > 0.3 * w for s in sups)
    chars = [c for c in chars if not under_marker(c)]
    items = [(c['x0'], 0, 'main', c) for c in chars] + [(anchor[id(c)], -1, 'sup', c) for c in sups]
    items.sort(key=lambda t: (t[0], t[1]))
    items = [(x, kind, c) for x, _, kind, c in items]
    runs = []
    prev = None
    for _, kind, c in items:
        ch = LIG.get(c['c'], c['c'])
        st = 'sup' if kind == 'sup' else style_of(c)
        if prev is not None and kind == 'main' and prev[1] == 'main':
            gap = c['x0'] - prev[2]['x1']
            if gap > 0.28 * c['size'] and not (runs and runs[-1][1].endswith(' ')) and ch != ' ':
                runs.append(['', ' ']) if not runs or runs[-1][0] != st else runs[-1].__setitem__(1, runs[-1][1] + ' ')
        if ch == ' ' and st in ('i', 'b', 'bi'):
            pass  # keep the space in the styled run; trimmed later
        if runs and runs[-1][0] == st:
            runs[-1][1] += ch
        else:
            runs.append([st, ch])
        prev = (c['x0'], kind, c)
    return [(s, t) for s, t in runs if t]


def merge_runs(a, b, joiner):
    out = [list(r) for r in a]
    if joiner:
        if out and out[-1][0] in ('', 'sup') and out[-1][0] == '':
            out[-1][1] += joiner
        else:
            out.append(['', joiner])
    for s, t in b:
        if out and out[-1][0] == s:
            out[-1][1] += t
        else:
            out.append([s, t])
    return [(s, t) for s, t in out]


def runs_text(runs):
    return ''.join(t for s, t in runs if s != 'sup')


def tidy_runs(runs):
    """Move leading/trailing spaces out of styled runs, collapse double spaces, drop empties."""
    out = []
    for s, t in runs:
        t = re.sub(r'[ \t]+', ' ', t)
        if s in ('i', 'b', 'bi') and t.strip():
            lead = len(t) - len(t.lstrip(' ')); trail = len(t) - len(t.rstrip(' '))
            if lead: out.append(['', ' '])
            out.append([s, t.strip(' ')])
            if trail: out.append(['', ' '])
        elif s in ('i', 'b', 'bi'):
            out.append(['', t])
        else:
            out.append([s, t])
    merged = []
    for s, t in out:
        if not t: continue
        if merged and merged[-1][0] == s:
            merged[-1][1] += t
        else:
            merged.append([s, t])
    for m in merged:
        m[1] = re.sub(r' {2,}', ' ', m[1])
    if merged and merged[0][0] == '': merged[0][1] = merged[0][1].lstrip()
    if merged and merged[-1][0] == '': merged[-1][1] = merged[-1][1].rstrip()
    return [(s, t) for s, t in merged if t]


def runs_html(runs, note_ids=None, doc_id=''):
    parts = []
    for s, t in tidy_runs(runs):
        e = html.escape(t, quote=False)
        if s == 'sup':
            n = t.strip()
            marks = [n]
            if note_ids is not None and n not in note_ids:
                for k in range(1, len(n)):
                    if n[:k] in note_ids and n[k:] in note_ids and n[k:].isdigit() and n[:k].isdigit() and int(n[k:]) == int(n[:k]) + 1:
                        marks = [n[:k], n[k:]]
            for j, m in enumerate(marks):
                if note_ids is not None and m in note_ids:
                    sep = '<sup>,</sup>' if j else ''
                    parts.append(f'{sep}<sup class="fnref"><a href="#fn{m}" id="fnref{m}">{m}</a></sup>')
                else:
                    parts.append(f'<sup>{html.escape(m)}</sup>')
        elif s == 'i': parts.append(f'<i>{e}</i>')
        elif s == 'b': parts.append(f'<b>{e}</b>')
        elif s == 'bi': parts.append(f'<b><i>{e}</i></b>')
        else: parts.append(e)
    out = ''.join(parts)
    out = re.sub(r'\s+(<sup class="fnref">)', r'\1', out)   # no space before a note marker
    return out.strip()


def join_rows(prev_runs, next_runs):
    a = runs_text(prev_runs).rstrip(); b = runs_text(next_runs).lstrip()
    if not a: return merge_runs(prev_runs, next_runs, '')
    last = a[-1]; first = b[:1]
    if last in '-‐' and first and (first.islower() or first.isupper()):
        return merge_runs(prev_runs, next_runs, '')          # compound broken at its hyphen
    if last in '—–/' or first in '—':
        return merge_runs(prev_runs, next_runs, '')
    return merge_runs(prev_runs, next_runs, ' ')


def convert(path, cfg=None):
    cfg = cfg or {}
    doc = fitz.open(path)
    allchars = [page_chars(p) for p in doc]
    sizes = Counter(c['size'] for pc in allchars for c in pc if c['c'].strip())
    body = cfg.get('body') or sizes.most_common(1)[0][0]
    main_min = cfg.get('main_min', body - 1.6)           # body and block-quote text
    note_size = cfg.get('note_size')                      # footnote text size
    if note_size is None:
        small = [(s, n) for s, n in sizes.items() if s < main_min and n > 150]
        note_size = max(small, key=lambda t: t[1])[0] if small else None
    H = doc[0].rect.height; W = doc[0].rect.width
    foot_y = cfg.get('foot_y', H - 62)                   # page-number zone
    head_y = cfg.get('head_y', 60)

    pages = []
    for pn, chars in enumerate(allchars):
        main = [c for c in chars if c['size'] >= main_min]
        rows = [r for r in cluster_rows(main) if r['text'].strip()]
        # running header / footer in main size
        rows = [r for r in rows if not ((r['y'] > foot_y or r['y'] < head_y) and re.fullmatch(r'\s*(\S+\s+)?\d+(\s+of\s+\d+)?\s*', r['text']))]
        small = [c for c in chars if c['size'] < main_min]
        used = set()
        for r in rows:
            r['sup'] = []
        for i, c in enumerate(small):
            if not c['c'].strip(): continue
            if not (c['c'].isdigit() or c['c'] in '*†‡'): continue
            best = None
            for r in rows:
                dy = r['y'] - c['y']
                if 1.0 <= dy <= 0.62 * r['size'] and r['x0'] - 3 <= c['x0'] <= r['x1'] + 14:
                    if best is None or dy < best[0]: best = (dy, r)
            if best:
                best[1]['sup'].append(c); used.add(i)
        rest = [c for i, c in enumerate(small) if i not in used]
        # footnote zone
        nrows = []
        if note_size:
            ntext = [c for c in rest if abs(c['size'] - note_size) < 0.6]
            labels = [c for c in rest if c['size'] < note_size - 1.2 and c['c'].strip()]
            nrows = [r for r in cluster_rows(ntext) if r['text'].strip()]
            nrows = [r for r in nrows if not (r['y'] > foot_y and re.fullmatch(r'[\s\d]*(of)?[\s\d]*', r['text']))]
            last_body = max([r['y'] for r in rows], default=0)
            nrows = [r for r in nrows if r['y'] > last_body - 2] if cfg.get('notes_below_body', True) else nrows
            for r in nrows: r['label'] = []
            for c in labels:
                best = None
                for r in nrows:
                    dy = r['y'] - c['y']
                    if 0.5 <= dy <= 0.7 * r['size'] and c['x0'] <= r['x0'] + 2:
                        if best is None or dy < best[0]: best = (dy, r)
                if best: best[1]['label'].append(c)
        pages.append({'rows': rows, 'nrows': nrows})

    # geometry of the body
    xs = Counter(round(r['x0']) for p in pages for r in p['rows'])
    L = cfg.get('left') or xs.most_common(1)[0][0]
    gaps = Counter()
    for p in pages:
        for a, b in zip(p['rows'], p['rows'][1:]):
            gaps[round(b['y'] - a['y'])] += 1
    pitch = cfg.get('pitch') or gaps.most_common(1)[0][0]
    R = max(r['x1'] for p in pages for r in p['rows'])
    center = W / 2
    inds = Counter(round(r['x0'] - L) for p in pages for r in p['rows'] if r['x0'] - L > 14)
    par_ind = cfg.get('par_indent') or (inds.most_common(1)[0][0] if inds else 36)

    blocks = []   # dicts: type, runs, page
    cur = None
    started = not cfg.get('start_after')
    stop = False
    for pn, p in enumerate(pages):
        rows = p['rows']
        if (pn + 1) in cfg.get('front_pages', {}):
            kind = cfg['front_pages'][pn + 1]; fcur = None
            for i, r in enumerate(rows):
                runs = runs_from_chars(r['chars'], r['sup'])
                g = (r['y'] - rows[i - 1]['y']) if i else None
                if fcur is not None and g is not None and g < 1.4 * pitch:
                    fcur['runs'] = join_rows(fcur['runs'], runs)
                else:
                    fcur = {'type': kind, 'runs': runs, 'page': pn + 1}; blocks.append(fcur)
            cur = None
            continue
        for i, r in enumerate(rows):
            text = r['text'].strip()
            if not started:
                if re.search(cfg['start_after'], text): started = True
                continue
            if cfg.get('stop_at') and re.search(cfg['stop_at'], text): stop = True
            if stop: continue
            ind = r['x0'] - L
            gprev = (r['y'] - rows[i - 1]['y']) if i > 0 else None
            gnext = (rows[i + 1]['y'] - r['y']) if i + 1 < len(rows) else None
            runs = runs_from_chars(r['chars'], r['sup'])
            mid = (r['x0'] + r['x1']) / 2
            is_centered = ind > 14 and abs(ind - par_ind) > 5 and abs(mid - center) < 7 and r['x1'] < R - 14
            styles = {s for s, t in runs if t.strip() and s != 'sup'}
            tight = lambda g: g is not None and g < 0.72 * pitch
            small_row = r['size'] < body - 0.6
            in_bq = cur is not None and cur['type'] == 'blockquote'
            bq = (ind > 14 and not is_centered and (small_row or tight(gnext) or (in_bq and tight(gprev)))) or (small_row and ind > 14)
            if cfg.get('no_blockquote'): bq = False
            heading = False
            if r['size'] >= body + 1.5 and len(text) < 120:
                heading = True
            elif is_centered and len(text) < 90 and not bq:
                heading = True
            elif styles and styles <= {'b', 'bi'} and len(text) < 90:
                heading = True
            elif cfg.get('heading_re') and re.fullmatch(cfg['heading_re'], text):
                heading = True
            if heading:
                if cur and cur['type'] == 'h' and gprev is not None and gprev < 1.3 * pitch:
                    cur['runs'] = join_rows(cur['runs'], runs)
                else:
                    cur = {'type': 'h', 'runs': runs, 'page': pn + 1}; blocks.append(cur)
                continue
            if bq:
                if in_bq and (gprev is None or gprev < 1.25 * pitch) and not (ind - cur['ind'] > 12 and tight(gprev) is False):
                    cur['runs'] = join_rows(cur['runs'], runs)
                elif in_bq and i == 0:
                    cur['runs'] = join_rows(cur['runs'], runs)
                else:
                    cur = {'type': 'blockquote', 'runs': runs, 'page': pn + 1, 'ind': ind}; blocks.append(cur)
                continue
            new_par = ind > 14
            if cur is None or cur['type'] != 'p':
                # after a block quote or heading: flush-left text continues the paragraph before a quote
                cont = cur is not None and cur['type'] == 'blockquote' and not new_par
                cur = {'type': 'p', 'runs': runs, 'page': pn + 1, 'cont': cont}; blocks.append(cur)
            elif new_par:
                cur = {'type': 'p', 'runs': runs, 'page': pn + 1, 'center': is_centered}; blocks.append(cur)
            elif gprev is not None and gprev > 1.6 * pitch and not cfg.get('ignore_gaps'):
                cur = {'type': 'p', 'runs': runs, 'page': pn + 1, 'gap': True}; blocks.append(cur)
            else:
                cur['runs'] = join_rows(cur['runs'], runs)

    # footnotes
    notes = {}
    order = []
    last = None
    for p in pages:
        for r in p['nrows']:
            runs = runs_from_chars(r['chars'])
            lab = ''.join(c['c'] for c in sorted(r['label'], key=lambda c: c['x0'])).strip()
            if not lab:
                m = re.match(r'\s*(\d{1,3})\s+(?=\S)', r['text']) if cfg.get('inline_labels') else None
                if m: lab = m.group(1)
            if lab:
                last = lab; order.append(lab); notes[lab] = runs
            elif last:
                notes[last] = join_rows(notes[last], runs)
    return {'blocks': blocks, 'notes': notes, 'order': order, 'body': body, 'left': L, 'pitch': pitch, 'note_size': note_size, 'pages': len(doc)}


def plain(result):
    out = []
    for b in result['blocks']:
        out.append(runs_text(b['runs']))
    for n in result['order']:
        out.append(runs_text(result['notes'][n]))
    return '\n'.join(out)
