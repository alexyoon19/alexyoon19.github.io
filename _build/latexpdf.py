"""LaTeX-made PDF -> structured blocks.

Prose becomes HTML text. Anything typeset in a math font is redrawn from the page's own glyph
outlines (inline or display), tables are redrawn the same way, figures are rendered to PNG.
Run with python3 -I from a caller that puts this directory on sys.path.
"""
import re, html, pathlib
from collections import Counter
import fitz
from rows import page_chars, cluster_rows, order_chars
from glyphs import Glyphs, PageGlyphs, rules_svg, fnum

MATH_FONT = re.compile(r'^(CMMI|CMSY|CMEX|MSAM|MSBM|PazoMath|CMBSY|CMMIB|dsrom|rsfs|eufm)')
FOREIGN = re.compile(r'^(Helvetica|Arial|Times|Garamond|DejaVu|Courier|Symbol|Myriad|Calibri)')
MATHY = set('=+-<>()[]{}|,.:;/0123456789−≥≤≠…×∗* ')
LIG = {'ﬁ': 'fi', 'ﬂ': 'fl', 'ﬀ': 'ff', 'ﬃ': 'ffi', 'ﬄ': 'ffl', ' ': ' ', '­': ''}


def style_of(font):
    if re.search(r'CMTT|SFTT|Courier', font): return 't'
    if re.search(r'CMCSC|-SC$', font): return 'c'
    b = bool(re.search(r'CMBX|Bold|SFBX', font)); i = bool(re.search(r'CMTI|CMBXTI|Ital|SFTI|CMSL', font))
    return ('b' if b else '') + ('i' if i else '')


class Doc:
    def __init__(self, path, cfg):
        self.doc = fitz.open(path); self.cfg = cfg
        self.S = cfg['body']                       # body size in pt
        self.store = Glyphs()
        self.blocks = []; self.notes = []; self.note_ids = []
        self.cur = None; self.pending = []; self.after = 'start'
        self.log = []
        self.media_dir = pathlib.Path(cfg['media_dir']); self.media_dir.mkdir(parents=True, exist_ok=True)
        self.media_url = cfg['media_url']
        self.vocab = set(); self.spell = None
        try:
            from spellchecker import SpellChecker
            self.spell = SpellChecker()
        except Exception:
            pass
        self.toc = {re.sub(r'\W+', '', re.sub(r'^[\d.]+\s*', '', t)).lower(): lvl for lvl, t, _ in self.doc.get_toc()}
        self.fn_expected = 1

    # ------------------------------------------------------------ helpers
    def known(self, w):
        w = w.lower()
        if w in self.vocab: return True
        return bool(self.spell and self.spell.known([w]))

    def rows_of(self, chars, size):
        """Anchor rows from chars near `size`; smaller chars attach as sub/superscripts; rest returned."""
        thr = size - 1.3
        main = [c for c in chars if c['size'] >= thr]
        small = [c for c in chars if c['size'] < thr]
        rows = [r for r in cluster_rows(main, tol=1.6) if r['text'].strip()]
        for r in rows: r['small'] = []
        keep = []
        for r in rows:
            vis = [c for c in r['chars'] if c['c'].strip()]
            host = None
            if len(vis) <= 3 and all(MATH_FONT.match(c['font']) for c in vis):
                cands = [q for q in rows if q is not r and abs(q['y'] - r['y']) < 4.6 and q['x0'] - 3 <= r['x0'] <= q['x1'] + 3 and len([c for c in q['chars'] if c['c'].strip()]) > 3]
                host = min(cands, key=lambda q: abs(q['y'] - r['y'])) if cands else None
            if host is not None: host['small'] += vis
            else: keep.append(r)
        rows = keep
        left = []
        for c in small:
            if not c['c'].strip(): continue
            mid = (c['top'] + c['bot']) / 2; best = None
            for r in rows:
                if r['y'] - 0.95 * size <= mid <= r['y'] + 0.5 * size and r['x0'] - 3 <= c['x0'] <= r['x1'] + 24:
                    d = abs(r['y'] - c['y'])
                    if best is None or d < best[0]: best = (d, r)
            if best: best[1]['small'].append(c)
            else: left.append(c)
        return rows, left

    def segment(self, row, PG, labels=()):
        """Row -> list of items: ('t', style, text) | ('m', chars) | ('fn', number)."""
        S = row['size']
        allc = order_chars([c for c in row['chars']] + row.get('small', []))
        small_ids = {id(c) for c in row.get('small', [])}
        kinds = []
        for c in allc:
            if id(c) in small_ids or MATH_FONT.match(c['font']):
                kinds.append('m')
            else:
                kinds.append('t')
        # footnote markers: raised small digits right after text, numbered as the notes run
        i = 0
        while i < len(allc):
            c = allc[i]
            if id(c) in small_ids and c['c'].isdigit() and row['y'] - c['y'] > 2.2 and not MATH_FONT.match(c['font']):
                j = i
                while j + 1 < len(allc) and id(allc[j + 1]) in small_ids and allc[j + 1]['c'].isdigit() and allc[j + 1]['x0'] - allc[j]['x1'] < 1.2 and abs(allc[j + 1]['y'] - c['y']) < 0.6:
                    j += 1
                num = ''.join(x['c'] for x in allc[i:j + 1])
                prev = next((allc[k] for k in range(i - 1, -1, -1) if allc[k]['c'].strip()), None)
                prev_math = prev is not None and (MATH_FONT.match(prev['font']) or id(prev) in small_ids)
                if num in labels and not prev_math:
                    for k in range(i, j + 1): kinds[k] = 'fn'
                i = j + 1
            else:
                i += 1
        # in non-CM documents the base letter of a sub/superscript is an ordinary italic: draw it with its script
        if self.cfg.get('adopt_base'):
            for i, c in enumerate(allc):
                if kinds[i] == 'm' and id(c) in small_ids and i > 0 and kinds[i - 1] == 't':
                    k = i - 1
                    while k >= 0 and kinds[k] == 't' and allc[k]['c'].strip() and 'i' in style_of(allc[k]['font']) and allc[k + 1]['x0'] - allc[k]['x1'] < 1.5:
                        kinds[k] = 'm'; k -= 1
        # text sandwiched inside a formula (=, brackets, digits) joins the formula
        n = len(allc); i = 0
        while i < n:
            if kinds[i] == 'm':
                j = i + 1
                while j < n and kinds[j] == 't' and allc[j]['c'] in MATHY and j - i <= 7: j += 1
                if j < n and j > i + 1 and kinds[j] == 'm' and allc[j]['x0'] - allc[i]['x1'] < 30 and any(allc[k]['c'].strip() for k in range(i + 1, j)):
                    for k in range(i + 1, j): kinds[k] = 'm'
                i = j if j > i + 1 else i + 1
            else:
                i += 1
        items = []; prevc = None
        for c, k in zip(allc, kinds):
            ch = LIG.get(c['c'], c['c'])
            gap = (c['x0'] - prevc['x1']) if prevc is not None else 0
            if k == 'm':
                if not c['c'].strip(): continue
                if items and items[-1][0] == 'm' and gap < 5.5:
                    items[-1][1].append(c)
                else:
                    if items and items[-1][0] == 't' and gap > 0.19 * S and not items[-1][2].endswith(' '): items[-1][2] += ' '
                    items.append(['m', [c]])
            elif k == 'fn':
                if items and items[-1][0] == 'fn': items[-1][1] += ch
                else: items.append(['fn', ch])
            else:
                st = style_of(c['font'])
                lead = ''
                if prevc is not None and gap > 0.19 * S and ch != ' ' and not (items and items[-1][0] == 't' and items[-1][2].endswith(' ')):
                    lead = ' '
                if items and items[-1][0] == 't' and items[-1][1] == st:
                    items[-1][2] += lead + ch
                else:
                    if lead and items and items[-1][0] == 't': items[-1][2] += lead; lead = ''
                    items.append(['t', st, lead + ch])
            if c['c'].strip(): prevc = c
        out = []
        for it in items:
            if it[0] == 'm':
                svg = PG.render(it[1], baseline=row['y'], em=S, label=''.join(x['c'] for x in it[1]))
                out.append(('m', svg, ''.join(x['c'] for x in it[1])))
            elif it[0] == 'fn':
                out.append(('fn', it[1]))
            else:
                out.append(('t', it[1], it[2]))
        return out

    @staticmethod
    def items_text(items):
        return ''.join(it[2] if it[0] == 't' else (' ' if it[0] == 'm' else '') for it in items)

    def join(self, a, b):
        """Join two item lists across a line break, undoing TeX hyphenation."""
        if not a: return list(b)
        if not b: return list(a)
        a = [list(x) for x in a]; b = [list(x) for x in b]
        if a[-1][0] == 't' and b[0][0] == 't':
            at = a[-1][2].rstrip(); bt = b[0][2].lstrip()
            w1 = re.search(r"([A-Za-z\u00c0-\u00ff']+)-$", at); w2 = re.match(r"[A-Za-z\u00c0-\u00ff']+", bt)
            if w1 and w2:
                x, y = w1.group(1), w2.group(0)
                if self.known(x + y) and not (x[0].isupper() and y[0].isupper()):
                    at = at[:-1]                                   # a word TeX broke: mend it
                elif self.known(x) and self.known(y):
                    pass                                           # a real compound: keep its hyphen
                else:
                    at = at[:-1]; self.log.append('dehyphen? %s|%s' % (x, y))
                a[-1][2] = at; b[0][2] = bt
            elif at.endswith(('\u2014', '/', '-')) or bt.startswith('\u2014') or (a[-1][1] == 't' and b[0][1] == 't') or (at.endswith('\u2013') and bt[:1].isdigit()):
                a[-1][2] = at; b[0][2] = bt                        # dashes and broken URLs join without a space
            else:
                a[-1][2] = at + ' '; b[0][2] = bt
            return self._glue(a, b)
        if a[-1][0] == 't': a[-1][2] = a[-1][2].rstrip() + ' '
        elif b[0][0] == 't': b[0][2] = ' ' + b[0][2].lstrip()
        else: a.append(['t', '', ' '])
        return [tuple(v) for v in a] + [tuple(v) for v in b]

    @staticmethod
    def _glue(a, b):
        if a[-1][0] == 't' and b[0][0] == 't' and a[-1][1] == b[0][1]:
            a[-1][2] += b[0][2]; b = b[1:]
        return [tuple(v) for v in a] + [tuple(v) for v in b]

    ACC = {'\u00b4': '\u0301', '`': '\u0300', '\u00a8': '\u0308', '\u02c6': '\u0302', '\u02dc': '\u0303', '\u00b8': '\u0327', '\u02c7': '\u030c'}

    def fix_accents(self, s):
        import unicodedata
        def rep(m):
            base = {'\u0131': 'i', '\u0237': 'j'}.get(m.group(2), m.group(2))
            return unicodedata.normalize('NFC', base + self.ACC[m.group(1)])
        return re.sub(r'([\u00b4\u00a8\u02c6\u02dc\u00b8\u02c7])\s?([A-Za-z\u0131\u0237])', rep, s)

    def items_html(self, items):
        # glue: a formula and the punctuation or letters touching it stay on one line
        items = [list(x) for x in items]
        for k, it in enumerate(items):
            if it[0] != 'm': continue
            pre = post = ''
            if k > 0 and items[k - 1][0] == 't' and items[k - 1][1] == '':
                m = re.search(r'(\S+)$', items[k - 1][2])
                if m and len(m.group(1)) <= 12: pre = m.group(1); items[k - 1][2] = items[k - 1][2][:m.start()]
            if k + 1 < len(items) and items[k + 1][0] == 't' and items[k + 1][1] == '':
                m = re.match(r'(\S+)', items[k + 1][2])
                if m and len(m.group(1)) <= 12: post = m.group(1); items[k + 1][2] = items[k + 1][2][m.end():]
            if pre or post:
                it[1] = '<span class="nb">' + html.escape(self.fix_accents(pre), quote=False) + it[1] + html.escape(self.fix_accents(post), quote=False) + '</span>'
        parts = []
        for it in items:
            if it[0] == 'm':
                parts.append(it[1])
            elif it[0] == 'fn':
                n = it[1]
                parts.append(f'<sup class="fnref"><a href="#fn{n}" id="fnref{n}">{n}</a></sup>')
            else:
                st, tx = it[1], it[2]
                tx = self.fix_accents(re.sub(r'[ \t]+', ' ', tx))
                e = html.escape(tx, quote=False)
                e = e.replace('``', '“').replace("''", '”')
                if st == 't':
                    lead = ' ' if tx[:1] == ' ' else ''; trail = ' ' if tx[-1:] == ' ' else ''
                    u = re.sub(r'\s+', '', tx)
                    if re.match(r'https?://|www\.', u):
                        e = lead + f'<a href="{html.escape(u if u.startswith("http") else "https://" + u, quote=True)}">{html.escape(u)}</a>' + trail
                    else:
                        e = lead + html.escape(u, quote=False) + trail
                elif st == 'c': e = f'<span class="sc">{e}</span>'
                elif st in ('i', 'b', 'bi') and e.strip():
                    lead = ' ' if e[:1] == ' ' else ''; trail = ' ' if e[-1:] == ' ' else ''
                    core = e.strip()
                    e = lead + {'i': f'<i>{core}</i>', 'b': f'<b>{core}</b>', 'bi': f'<b><i>{core}</i></b>'}[st] + trail
                parts.append(e)
        s = ''.join(parts)
        s = re.sub(r'\s+(<sup class="fnref">)', r'\1', s)
        s = re.sub(r'(</i>)(\s*)<i>', r'\2', s) if False else s
        s = re.sub(r' {2,}', ' ', s)
        return s.strip()

    # ------------------------------------------------------------ flow
    def emit(self, block):
        self.blocks.append(block); self.cur = block
        return block

    def flush_floats(self):
        for f in self.pending: self.blocks.append(f)
        self.pending = []

    def close_par(self):
        self.cur = None

    # ------------------------------------------------------------ floats
    def float_zones(self, page, chars, pn):
        """Return list of zones: dict(rect, kind, graphic rect, caption rows chars...)."""
        zones = []
        drs = page.get_drawings()
        frames = [d['rect'] for d in drs if d['rect'].width > 300 and d['rect'].height > 80 and d['rect'].width < 520]
        # outermost frames only
        frames = [f for f in frames if not any(g != f and g.contains(f) and g.get_area() > f.get_area() for g in frames)]
        S = self.S
        docchars = [c for c in chars if not FOREIGN.match(c['font'])]
        rows = [r for r in self.split_cols(cluster_rows([c for c in docchars if c['size'] >= S - 2.2], tol=1.6)) if r['text'].strip()]
        caps = [r for r in rows if re.match(r'\s*(Figure|Table)\s*\d+\s*[:.]', r['text'])]
        used = []
        for cap in caps:
            kind = 'figure' if cap['text'].lstrip().startswith('Figure') else 'table'
            num = re.search(r'\d+', cap['text']).group(0)
            fr = next((f for f in frames if f.y0 - 2 <= cap['y'] <= f.y1 + 2), None)
            if fr is not None:
                zone = fitz.Rect(fr.x0 - 1, fr.y0 - 1, fr.x1 + 1, fr.y1 + 1)
                inner = [d['rect'] for d in drs if fr.contains(d['rect']) and d['rect'].height < 1.5 and 30 < d['rect'].width < 160 and d['rect'].y0 > cap['y']]
                note_y = min((r.y0 for r in inner), default=None)
                if kind == 'figure':
                    graphic = fitz.Rect(fr.x0 + 1.5, fr.y0 + 1.5, fr.x1 - 1.5, cap['top'] - 3)
                    cap_rows = [r for r in rows if cap['y'] - 1 <= r['y'] <= fr.y1 and (note_y is None or r['y'] < note_y) and r['x0'] >= fr.x0]
                    note_chars = [c for c in docchars if note_y is not None and note_y < c['y'] <= fr.y1 + 1]
                else:
                    graphic = fitz.Rect(fr.x0 + 1.5, cap['bot'] + 3, fr.x1 - 1.5, fr.y1 - 1.5)
                    cap_rows = [cap]; note_chars = []
            else:
                colx0, colx1 = self.column_of(cap)
                next_cap = min([c['y'] for c in caps if c['y'] > cap['y'] + 5] + [1e9])
                hr = sorted([d['rect'] for d in drs if d['rect'].height < 1.6 and d['rect'].width > 0.45 * (colx1 - colx0) and d['rect'].y0 > cap['y'] - 2 and d['rect'].x0 >= colx0 - 30 and d['rect'].x1 <= colx1 + 30
                             and d['rect'].y0 < next_cap - 6 and not any(f.y0 - 3 <= d['rect'].y0 <= f.y1 + 3 for f in frames)], key=lambda r: r.y0)
                imgs = [fitz.Rect(i['bbox']) for i in page.get_image_info()]
                if kind == 'table' and hr:
                    # contiguous run of rules below the caption
                    run = [hr[0]]
                    for r in hr[1:]:
                        if r.y0 - run[-1].y0 < 260: run.append(r)
                        else: break
                    y0 = run[0].y0 - 3; y1 = run[-1].y1 + 3
                    trail = [r for r in rows if y1 - 2 < r['top'] < y1 + 16 and (r['size'] < S - 0.4 or re.match(r'\s*(Note|Notes|Source)\b', r['text']))]
                    stars = [c for c in docchars if y1 - 2 < c['top'] < y1 + 16 and c['size'] < S - 0.4]
                    if trail or stars: y1 = max([r['bot'] for r in trail] + [c['bot'] for c in stars]) + 2
                    graphic = fitz.Rect(min(r.x0 for r in run) - 2, y0, max(r.x1 for r in run) + 2, y1)
                    cap_rows = [r for r in rows if cap['y'] - 1 <= r['y'] < run[0].y0 - 1 and colx0 - 30 <= r['x0'] and r['x1'] <= colx1 + 30]
                    zone = fitz.Rect(min(graphic.x0, colx0) - 3, cap['top'] - 2, max(graphic.x1, colx1) + 3, y1 + 1)
                    note_chars = []
                elif kind == 'figure':
                    above = [i for i in imgs if i.y1 <= cap['top'] + 4 and cap['top'] - i.y1 < 40 and i.x0 >= colx0 - 30 and i.x1 <= colx1 + 30]
                    if not above:
                        self.log.append(f'p{pn+1}: no graphic found for {cap["text"][:30]}'); continue
                    graphic = fitz.Rect(min(i.x0 for i in above), min(i.y0 for i in above), max(i.x1 for i in above), max(i.y1 for i in above))
                    cap_rows = [cap]
                    for r in rows:
                        if r['y'] > cap['y'] + 1 and r['y'] - cap_rows[-1]['y'] < 1.45 * S and colx0 - 3 <= r['x0'] and r['x1'] <= colx1 + 3 and r['size'] <= cap['size'] + 0.3:
                            cap_rows.append(r)
                    zone = fitz.Rect(min(graphic.x0, colx0) - 3, graphic.y0 - 2, max(graphic.x1, colx1) + 3, cap_rows[-1]['bot'] + 2)
                    note_chars = []
                else:
                    self.log.append(f'p{pn+1}: no rules found for {cap["text"][:30]}'); continue
            zones.append({'kind': kind, 'num': num, 'zone': zone, 'graphic': graphic, 'cap_rows': cap_rows, 'note_chars': note_chars, 'y': zone.y0})
        return zones

    def split_cols(self, rows):
        """In a two-column page, cut rows at the gutter unless text runs across it."""
        cols = self.cfg.get('columns')
        if not cols: return rows
        gut = (cols[0][1] + cols[1][0]) / 2
        out = []
        for r in rows:
            left = [c for c in r['chars'] if (c['x0'] + c['x1']) / 2 < gut]; right = [c for c in r['chars'] if (c['x0'] + c['x1']) / 2 >= gut]
            lv = [c for c in left if c['c'].strip()]; rv = [c for c in right if c['c'].strip()]
            if lv and rv and min(c['x0'] for c in rv) - max(c['x1'] for c in lv) > 7:
                for part in (left, right):
                    out += cluster_rows(part, tol=1.6)
            else:
                out.append(r)
        return sorted(out, key=lambda r: r['y'])

    def column_of(self, row):
        cols = self.cfg.get('columns')
        if not cols: return self.cfg['left'], self.cfg['right']
        if row['x0'] < cols[0][1] - 20 and row['x1'] > cols[1][0] + 20: return cols[0][0], cols[1][1]
        mid = (row['x0'] + row['x1']) / 2
        return cols[0] if mid < (cols[0][1] + cols[1][0]) / 2 else cols[1]

    def make_float(self, page, PG, z, pn):
        capchars = [c for r in z['cap_rows'] for c in r['chars']]
        small_all = [c for c in self._page_chars if c['size'] < self.S - 2.2 and z['zone'].contains(fitz.Point(c['ox'], c['y']))]
        rows, _ = self.rows_of(capchars + [c for c in small_all if any(r['y'] - 9 < c['y'] < r['y'] + 4 for r in z['cap_rows'])], z['cap_rows'][0]['size'])
        items = []
        for r in sorted(rows, key=lambda r: r['y']):
            items = self.join(items, self.segment(r, PG))
        cap = self.items_html(items)
        cap = re.sub(r'^<b>\s*((?:Figure|Table)\s*\d+)\s*[:.]?\s*</b>\s*[:.]?\s*', r'\1: ', cap)
        cap = re.sub(r'^(Figure|Table)\s*(\d+)\s*[:.]\s*', lambda m: f'<b>{m.group(1)} {m.group(2)}.</b> ', cap)
        note = ''
        if z['note_chars']:
            size = Counter(c['size'] for c in z['note_chars'] if c['c'].strip()).most_common(1)[0][0]
            nrows, _ = self.rows_of(z['note_chars'], size)
            nitems = []
            for r in sorted(nrows, key=lambda r: r['y']):
                seg = self.segment(r, PG)
                nitems = self.join(nitems, seg)
            note = re.sub(r'^\s*<svg.*?</svg>\s*', '', self.items_html(nitems)) if nitems and nitems[0][0] == 'm' else self.items_html(nitems)
        g = z['graphic']
        if z['kind'] == 'figure':
            pix = page.get_pixmap(matrix=fitz.Matrix(3, 3), clip=g, alpha=False)
            name = f'fig-{z["num"]}.png'
            pix.save(str(self.media_dir / name))
            return {'type': 'figure', 'src': self.media_url + name, 'w': pix.width, 'h': pix.height, 'em': round(g.width / self.S, 2), 'caption': cap, 'note': note}
        chars = [c for c in self._page_chars if g.contains(fitz.Point(c['ox'], c['y'])) or g.contains(fitz.Point((c['x0'] + c['x1']) / 2, (c['top'] + c['bot']) / 2))]
        svg = PG.render(chars, em=self.S, extra=rules_svg(page, g), rect=(g.x0, g.y0, g.x1, g.y1), cls='tb', label=f'Table {z["num"]}')
        return {'type': 'table', 'svg': svg, 'caption': cap, 'note': note}

    # ------------------------------------------------------------ one page
    def page(self, pn):
        page = self.doc[pn]; S = self.S; cfg = self.cfg
        chars = page_chars(page)
        self._page_chars = chars
        PG = PageGlyphs(page, self.store)
        H = page.rect.height
        zones = self.float_zones(page, chars, pn) if cfg.get('floats', True) else []
        def in_zone(c):
            return any(z['zone'].contains(fitz.Point(c['ox'], c['y'])) for z in zones)
        free = [c for c in chars if not in_zone(c) and not FOREIGN.match(c['font'])]
        # page furniture
        top_cut = cfg.get('head_y', 0); bot_cut = cfg.get('foot_y', H - 62)
        free = [c for c in free if top_cut < c['y'] < bot_cut]
        for (p, x0, y0, x1, y1) in cfg.get('skip', []):
            if p == pn + 1: free = [c for c in free if not (y0 <= c['y'] <= y1 and x0 <= c['ox'] <= x1)]
        cols = cfg.get('columns') or [(cfg['left'], cfg['right'])]
        full = [(a, b) for (p, a, b) in cfg.get('fullwidth', []) if p == pn + 1]
        drs = page.get_drawings()
        floats_here = sorted(zones, key=lambda z: z['y'])
        for z in floats_here:
            self.pending.append(self.make_float(page, PG, z, pn))
        regions = []
        for (a, b) in full:
            regions.append((cols[0][0], cols[-1][1], [c for c in free if a <= c['y'] <= b]))
        rest = [c for c in free if not any(a <= c['y'] <= b for a, b in full)]
        if len(cols) == 1:
            regions.append((cols[0][0], cols[0][1], rest))
        else:
            gut = (cols[0][1] + cols[1][0]) / 2
            regions.append((cols[0][0], cols[0][1], [c for c in rest if (c['x0'] + c['x1']) / 2 < gut]))
            regions.append((cols[1][0], cols[1][1], [c for c in rest if (c['x0'] + c['x1']) / 2 >= gut]))
        for (L, R, rc) in regions:
            self.region(page, PG, rc, L, R, drs, pn, zones)

    def region(self, page, PG, chars, L, R, drs, pn, zones):
        S = self.S; cfg = self.cfg
        if not chars: return
        # footnote zone: below the short rule at the left margin
        frule = [d['rect'] for d in drs if d['rect'].height < 1.5 and 0.25 * (R - L) < d['rect'].width < 0.55 * (R - L) and abs(d['rect'].x0 - L) < 3
                 and d['rect'].y0 > 200 and not any(z['zone'].contains(d['rect']) for z in zones)]
        fy = min((r.y0 for r in frule), default=None)
        fy = cfg.get('note_y', {}).get(pn + 1, fy)
        body = [c for c in chars if fy is None or c['y'] < fy]
        foot = [c for c in chars if fy is not None and c['y'] >= fy]
        # footnotes first, so markers in the text can be recognised
        labels = set()
        if foot:
            fs = Counter(c['size'] for c in foot if c['c'].strip() and c['size'] > 7).most_common(1)[0][0]
            frows, fleft = self.rows_of(foot, fs)
            cur = None
            for r in sorted(frows, key=lambda r: r['y']):
                lab = ''
                cand = sorted([c for c in r['small'] + fleft if c['c'].strip() and c['x0'] < r['x0'] + 1 and abs((r['y'] - c['y']) - 3.5) < 3.5 and (c['c'].isdigit() or c['c'] in '*†')], key=lambda c: c['x0'])
                if cand:
                    lab = ''.join(c['c'] for c in cand)
                    r['small'] = [c for c in r['small'] if c not in cand]
                seg = self.segment(r, PG)
                if lab:
                    cur = [lab, seg]; self.notes.append(cur); labels.add(lab)
                elif cur is not None:
                    cur[1] = self.join(cur[1], seg)
                elif self.notes:
                    self.notes[-1][1] = self.join(self.notes[-1][1], seg)
        labels |= {str(self.fn_expected + k) for k in range(0, 3)}
        rows, left = self.rows_of(body, S if not cfg.get('page_size', {}).get(pn + 1) else cfg['page_size'][pn + 1])
        rows.sort(key=lambda r: r['y'])
        for r in rows:
            for w in re.findall(r"[A-Za-z]{3,}", r['text'])[1:-1]:      # not the first or last word: those may be halves
                self.vocab.add(w.lower())
        # ---- display formulas
        def feats(r):
            vis = [c for c in r['chars'] + r['small'] if c['c'].strip()]
            imath = cfg.get('italic_math')
            mcount = sum(1 for c in vis if MATH_FONT.match(c['font']) or c in r['small'] or (imath and 'i' in style_of(c['font'])))
            txt = r['text'].rstrip()
            m = re.search(r'\((\d+[a-z]?)\)$', txt)
            eq = None
            if m and r['x1'] > R - 8:
                tok = [c for c in r['chars'] if c['c'].strip()][-len(m.group(0)):]
                before = [c for c in r['chars'] if c['c'].strip() and c['x1'] <= tok[0]['x0'] + 0.1]
                if not before or tok[0]['x0'] - before[-1]['x1'] > 7.5:
                    eq = (m.group(1), tok)
            plain = ''.join(c['c'] for c in r['chars'] if not MATH_FONT.match(c['font']) and not (eq and c in eq[1]))
            core = [c for c in vis if not (eq and c in eq[1])]
            mathy = sum(1 for c in core if MATH_FONT.match(c['font']) or c in r['small'] or c['c'] in MATHY or (imath and 'i' in style_of(c['font']))) / max(1, len(core))
            first = core[0]['c'] if core else ''
            return mcount / max(1, len(vis)), eq, len(re.findall(r'[A-Za-z]{2,}', plain)), mathy, first
        W = R - L
        ref_y = 1e9 if not self.refs else -1
        for r in rows:
            vis0 = [c for c in r['chars'] if c['c'].strip()]
            if vis0 and all('b' in style_of(c['font']) for c in vis0) and re.fullmatch(r'\s*(References|Bibliography|Works Cited)\s*', r['text']):
                ref_y = min(ref_y, r['y'])
        for r in rows:
            ratio, eq, words, mathy, first = feats(r)
            if r['y'] > ref_y: ratio = 0; mathy = 0; eq = None
            r['eq'] = eq
            body_chars = [c for c in r['chars'] if c['c'].strip() and not (eq and c in eq[1])]
            r['bx0'] = min((c['x0'] for c in body_chars), default=1e9); r['bx1'] = max((c['x1'] for c in body_chars), default=-1e9)
            off = r['bx0'] - L
            centered = off > 0.085 * W
            bullet = bool(re.match(r'\s*[\u2022\u2013]', r['text']))
            loose = words <= 2 and off > 8 and mathy >= 0.6 and (ratio >= 0.3 or eq or first in '=<>\u2264\u2265\u2208\u21d2\u2234\u222a+\u2212' or (words == 0 and ratio > 0))
            r['disp'] = bool(not bullet and (loose or (ratio >= 0.3 and words <= 4 and centered) or (eq and (centered or not body_chars))))
        groups = [{'rows': [r], 'y0': r['top'], 'y1': r['bot']} for r in rows if r['disp']]
        def absorb(g):
            g['x0'] = min([r['bx0'] for r in g['rows']] + [c['x0'] for c in g.get('extra', [])])
            g['x1'] = max([r['bx1'] for r in g['rows']] + [c['x1'] for c in g.get('extra', [])])
            changed = True
            while changed:
                changed = False
                for c in left:
                    if c in g.setdefault('extra', []): continue
                    if g['x0'] - 8 <= c['x0'] <= g['x1'] + 8 and g['y0'] - 14 <= c['y'] <= g['y1'] + 15:
                        g['extra'].append(c); g['y0'] = min(g['y0'], c['top']); g['y1'] = max(g['y1'], c['bot']); g['x0'] = min(g['x0'], c['x0']); g['x1'] = max(g['x1'], c['x1']); changed = True
        for g in groups: absorb(g)
        # centred text lines that belong to a display ("where ...")
        for r in rows:
            if r['disp']: continue
            if r['bx0'] - L > 0.085 * W and r['bx1'] < R - 0.05 * W:
                for g in groups:
                    if g['y0'] - 6 < r['y'] < g['y1'] + 20:
                        r['disp'] = True; g['rows'].append(r); g['y0'] = min(g['y0'], r['top']); g['y1'] = max(g['y1'], r['bot']); absorb(g); break
        # lines of one display sit close together: merge them
        groups.sort(key=lambda g: g['y0'])
        merged = []
        for g in groups:
            if merged and g['y0'] - merged[-1]['y1'] < 15:
                m = merged[-1]; m['rows'] += g['rows']; m['extra'] = m.get('extra', []) + [c for c in g.get('extra', []) if c not in m.get('extra', [])]
                m['y0'] = min(m['y0'], g['y0']); m['y1'] = max(m['y1'], g['y1']); absorb(m)
            else:
                merged.append(g)
        # an aligned block numbers each line: split it so every number keeps its line
        groups = []
        for g in merged:
            numbered = [r for r in g['rows'] if r['eq'] and any(c['c'].strip() and not (c in r['eq'][1]) for c in r['chars'])]
            if len(numbered) >= 2:
                rs = sorted(g['rows'], key=lambda r: r['y']); cur = []
                parts = []
                for r in rs:
                    cur.append(r)
                    if r in numbered: parts.append(cur); cur = []
                if cur: parts[-1] += cur
                for prt in parts:
                    ng = {'rows': prt, 'y0': min(r['top'] for r in prt), 'y1': max(r['bot'] for r in prt), 'extra': []}
                    groups.append(ng)
                # hand each stray limit to the nearest part
                for c in g.get('extra', []):
                    best = min(groups[-len(parts):], key=lambda ng: min(abs(c['y'] - ng['y0']), abs(c['y'] - ng['y1'])) if not (ng['y0'] <= c['y'] <= ng['y1']) else -1)
                    best['extra'].append(c); best['y0'] = min(best['y0'], c['top']); best['y1'] = max(best['y1'], c['bot'])
            else:
                groups.append(g)
        for g in groups:
            g['chars'] = [c for r in g['rows'] for c in r['chars'] + r['small'] if not (r['eq'] and c in r['eq'][1])] + g.get('extra', [])
            vis = [c for c in g['chars'] if c['c'].strip()] or [c for r in g['rows'] for c in r['chars'] if c['c'].strip()]
            g['num'] = next((r['eq'][0] for r in sorted(g['rows'], key=lambda r: r['y']) if r['eq']), '')
            g['y'] = min(r['y'] for r in g['rows'])
            g['rect'] = (min(c['x0'] for c in vis) - 2, g['y0'] - 2, max(c['x1'] for c in vis) + 2, g['y1'] + 2)
            if not g['num'] or not vis: self.log.append(f"p{pn+1} y{g['y']:.0f} display without number: " + ' / '.join(r['text'].strip()[:28] for r in sorted(g['rows'], key=lambda r: r['y']))[:90])
        stray = [c for c in left if not any(c in g['chars'] for g in groups)]
        if stray: self.log.append(f'p{pn+1}: {len(stray)} small chars unplaced: ' + ''.join(c['c'] for c in stray)[:40])
        # ---- walk rows in order
        events = [(r['y'], 'row', r) for r in rows if not r['disp']] + [(g['y'], 'eq', g) for g in groups]
        events.sort(key=lambda e: e[0])
        prev_y = None
        par_ind = cfg.get('par_indent', 17)
        for y, kind, obj in events:
            if kind == 'eq':
                svg = PG.render(obj['chars'], em=S, extra=rules_svg(page, obj['rect']), cls='md', label='equation ' + obj['num'] if obj['num'] else 'equation')
                self.blocks.append({'type': 'eq', 'svg': svg, 'num': obj['num']})
                self.after = 'eq'; self.cur = None; prev_y = obj['y1']
                continue
            r = obj
            text = r['text'].strip()
            ind = r['x0'] - L
            gap = (r['y'] - prev_y) if prev_y is not None else None
            prev_y = r['y']
            vis = [c for c in r['chars'] if c['c'].strip()]
            bold = all(('b' in style_of(c['font'])) for c in vis)
            key = re.sub(r'\W+', '', re.sub(r'^[\d.]+\s*', '', text)).lower()
            # headings
            if bold and (r['size'] >= S + 0.9 or key in self.toc or cfg.get('bold_heads')) and len(text) < 110 and not (self.cur and self.cur['type'] == 'li' and ind > 10):
                seg = [('t', '', it[2]) if it[0] == 't' else it for it in self.segment(r, PG)]
                htxt = self.items_html(seg)
                m = re.match(r'^(\d+(?:\.\d+)*)\.?\s+(.*)$', htxt)
                num, title = (m.group(1), m.group(2)) if m else ('', htxt)
                lvl = self.toc.get(key) or (1 if r['size'] >= S + 2.5 else 2)
                if self.cur and self.cur['type'] in ('h2', 'h3', 'h4') and gap is not None and gap < 1.6 * r['size'] and not num:
                    self.cur['html'] += ' ' + title
                else:
                    self.flush_floats()
                    self.emit({'type': 'h%d' % min(4, lvl + 1), 'html': title, 'num': num})
                self.refs = bool(re.fullmatch(r'(References|Bibliography|Works Cited)', title.strip()))
                self.after = 'h'
                continue
            italic = bool(vis) and all(style_of(c['font']) == 'i' for c in vis)
            if cfg.get('italic_heads') and italic and ind < 4 and len(text) < 70 and not re.search(r'[.,;:]$', text) and not self.refs and (gap is None or gap > 1.15 * cfg.get('pitch', 12.5)):
                self.flush_floats()
                self.emit({'type': 'h4', 'html': self.items_html([('t', '', it[2]) if it[0] == 't' else it for it in self.segment(r, PG)]), 'num': ''})
                self.after = 'h'
                continue
            if self.refs:
                seg = self.segment(r, PG, labels)
                if ind < 5 or self.cur is None or self.cur.get('cls') != 'ref':
                    if self.open_par is not None and self.open_par.get('cls') == 'ref' and ind >= 5 and self.cur is None:
                        self.open_par['items'] = self.join(self.open_par['items'], seg); self.cur = self.open_par
                    else:
                        self.emit({'type': 'p', 'items': seg, 'cls': 'ref'})
                else:
                    self.cur['items'] = self.join(self.cur['items'], seg)
                self.after = 'row'
                continue
            seg = self.segment(r, PG, labels)
            for it in seg:
                if it[0] == 'fn' and it[1].isdigit(): self.fn_expected = max(self.fn_expected, int(it[1]) + 1)
            first_txt = text[:4]
            # list items
            m_bul = re.match(r'^(•|–|\d{1,2}\.|\(\d{1,2}\)|[a-z]\))\s+\S', text) if 6 < ind < 60 else None
            if m_bul and not (self.cur and self.cur['type'] == 'p' and ind < par_ind + 4 and not text.startswith('•') and self.after == 'row' and not re.match(r'^\d{1,2}\.\s+[A-Z]', text)):
                mark = m_bul.group(1)
                # drop the marker from the first text item
                seg2 = [list(x) for x in seg]
                for it in seg2:
                    if it[0] == 't':
                        it[2] = re.sub(r'^\s*(•|–|\d{1,2}\.|\(\d{1,2}\)|[a-z]\))\s*', '', it[2], count=1); break
                    if it[0] == 'm' and mark in ('•',):
                        it[0] = 't'; it[1] = ''; it[2] = ''; it[:] = it[:3]; break
                seg2 = [tuple(x) for x in seg2 if not (x[0] == 't' and x[2] == '')]
                rest = [c for c in vis if c['x0'] > vis[0]['x1'] + 2]
                self.flush_floats()
                self.emit({'type': 'li', 'items': seg2, 'ordered': mark[0].isdigit() or mark.startswith('('), 'textx': rest[0]['x0'] if rest else r['x0'] + 12, 'markx': r['x0']})
                self.after = 'row'
                continue
            if self.cur and self.cur['type'] == 'li':
                if r['x0'] >= self.cur['textx'] - 3 or (r['x0'] > self.cur['markx'] + 4):
                    self.cur['items'] = self.join(self.cur['items'], seg); self.after = 'row'; continue
                self.cur = None; self.after = 'list'
            new_par = (par_ind - 6 <= ind <= par_ind + 9)
            if self.cur and self.cur['type'] == 'p' and not new_par and self.after == 'row' and not (gap is not None and gap > cfg.get('par_gap', {}).get(pn + 1, 1e9)):
                self.cur['items'] = self.join(self.cur['items'], seg)
            elif self.cur is None and self.after in ('eq',) and not new_par and self.blocks and ind < 4:
                self.emit({'type': 'p', 'items': seg, 'cls': 'cont'})
            elif self.cur is None and self.after == 'float_gap':
                self.emit({'type': 'p', 'items': seg, 'cls': ''})
            else:
                if not new_par and self.after in ('row',) and self.cur is None and self.open_par is not None and ind < 4:
                    # paragraph running on from the previous page or column
                    self.open_par['items'] = self.join(self.open_par['items'], seg); self.cur = self.open_par
                else:
                    self.flush_floats()
                    self.emit({'type': 'p', 'items': seg, 'cls': 'cont' if (self.after in ('list',) and not new_par) else ''})
            self.after = 'row'
        # end of region: remember an open paragraph so the next page can continue it
        self.open_par = self.cur if (self.cur and self.cur['type'] in ('p', 'li')) else None
        if self.cur and self.cur['type'] == 'p':
            self.cur = None

    open_par = None
    refs = False

    def run(self, pages):
        for pn in pages:
            self.page(pn)
        self.flush_floats()
        out = []
        for b in self.blocks:
            if 'items' in b:
                b = dict(b); b['html'] = self.items_html(b.pop('items'))
                for k in ('textx', 'markx'): b.pop(k, None)
                if not b['html']: continue
            out.append(b)
        notes = [(n, self.items_html(items)) for n, items in self.notes]
        return {'blocks': out, 'notes': notes, 'glyphdefs': self.store.defs_html()}
