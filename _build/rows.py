"""Shared low-level reader: chars -> visual rows, with superscripts attached. Trusted script dir only."""
import fitz, re, statistics
from collections import Counter

FLAGS = fitz.TEXT_PRESERVE_WHITESPACE | fitz.TEXT_MEDIABOX_CLIP | fitz.TEXT_PRESERVE_LIGATURES

def order_chars(chars):
    """Left to right, except that characters drawn at (nearly) the same spot keep the order the PDF
    drew them in. A ligature such as 'fi' arrives as f + i with the i placed a hair after the next letter."""
    cs = sorted(chars, key=lambda c: c['x0'])
    changed = True
    while changed:
        changed = False
        for i in range(len(cs) - 1):
            a, b = cs[i], cs[i + 1]
            if b['x0'] - a['x0'] < 0.6 and a.get('seq', 0) > b.get('seq', 0) and a['font'] == b['font'] and abs(a['y'] - b['y']) < 0.1:
                cs[i], cs[i + 1] = b, a; changed = True
    return cs


def page_chars(page):
    out = []
    for b in page.get_text('rawdict', flags=FLAGS)['blocks']:
        if b['type'] != 0: continue
        for l in b['lines']:
            for s in l['spans']:
                for ch in s['chars']:
                    out.append({'c': ch['c'], 'x0': ch['bbox'][0], 'x1': ch['bbox'][2], 'y': ch['origin'][1], 'ox': ch['origin'][0],
                                'top': ch['bbox'][1], 'bot': ch['bbox'][3],
                                'size': round(s['size'], 1), 'font': s['font'], 'flags': s['flags'], 'seq': len(out)})
    return out

def cluster_rows(chars, tol=2.0):
    """Group chars into rows by baseline."""
    rows = []
    for ch in sorted(chars, key=lambda c: (c['y'], c['x0'])):
        for r in rows[::-1][:6]:
            if abs(r['y'] - ch['y']) <= tol:
                r['chars'].append(ch); break
        else:
            rows.append({'y': ch['y'], 'chars': [ch]})
    for r in rows:
        r['chars'] = order_chars(r['chars'])
        vis = [c for c in r['chars'] if c['c'].strip()]
        if not vis: vis = r['chars']
        r['x0'] = min(c['x0'] for c in vis); r['x1'] = max(c['x1'] for c in vis)
        r['size'] = Counter(c['size'] for c in vis).most_common(1)[0][0]
        r['text'] = ''.join(c['c'] for c in r['chars'])
        r['top'] = min(c['top'] for c in vis); r['bot'] = max(c['bot'] for c in vis)
    rows.sort(key=lambda r: r['y'])
    return rows
