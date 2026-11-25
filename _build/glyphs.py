"""Vector glyph export: turn chosen characters of a PDF page into compact inline SVG.

MuPDF's SVG export writes every glyph outline once (<path id="font_x_y">) and places it with
<use ... transform="matrix(...)">, the last two numbers being the glyph origin on the page.
We look glyphs up by origin, so a formula can be re-drawn exactly, glyph for glyph.
"""
import re, html
import fitz

NUM = re.compile(r'[MLHVCZ]|-?\d*\.?\d+(?:[eE]-?\d+)?')


def path_bbox(d):
    toks = NUM.findall(d)
    xs, ys = [], []
    i = 0; cmd = None; cx = cy = 0.0
    while i < len(toks):
        t = toks[i]
        if t in 'MLHVCZ':
            cmd = t; i += 1
            if cmd == 'Z': continue
        if cmd in ('M', 'L'):
            cx, cy = float(toks[i]), float(toks[i + 1]); i += 2; xs.append(cx); ys.append(cy)
        elif cmd == 'H':
            cx = float(toks[i]); i += 1; xs.append(cx); ys.append(cy)
        elif cmd == 'V':
            cy = float(toks[i]); i += 1; xs.append(cx); ys.append(cy)
        elif cmd == 'C':
            for k in range(3):
                x, y = float(toks[i]), float(toks[i + 1]); i += 2; xs.append(x); ys.append(y)
            cx, cy = x, y
        else:
            i += 1
    if not xs: return (0, 0, 0, 0)
    return (min(xs), min(ys), max(xs), max(ys))


class Glyphs:
    def __init__(self):
        self.ids = {}      # outline -> id
        self.bbox = {}     # id -> unit bbox

    def gid(self, d):
        if d not in self.ids:
            g = 'g%d' % (len(self.ids) + 1)
            self.ids[d] = g; self.bbox[g] = path_bbox(d)
        return self.ids[d]

    def defs_html(self, used=None):
        items = [(g, d) for d, g in self.ids.items() if used is None or g in used]
        return '<svg class="glyphdefs" width="0" height="0" aria-hidden="true"><defs>' + ''.join(f'<path id="{g}" d="{d}"/>' for g, d in items) + '</defs></svg>'


def fnum(v):
    s = ('%.2f' % v).rstrip('0').rstrip('.')
    return s if s not in ('-0', '') else '0'


class PageGlyphs:
    def __init__(self, page, store):
        svg = page.get_svg_image(text_as_path=True)
        self.store = store
        self.defs = dict(re.findall(r'<path id="(font_\w+)" d="([^"]*)"', svg))
        self.uses = {}
        for m in re.finditer(r'<use data-text="[^"]*" xlink:href="#(font_\w+)" transform="matrix\(([^)]*)\)"', svg):
            mt = tuple(float(v) for v in m.group(2).split(','))
            self.uses.setdefault((round(mt[4], 1), round(mt[5], 1)), []).append((m.group(1), mt))
        self.taken = set()

    def find(self, ch):
        """SVG <use> entries drawn at this character's origin."""
        for dx in (0, 0.1, -0.1):
            for dy in (0, 0.1, -0.1):
                k = (round(ch['ox'] + dx, 1), round(ch['y'] + dy, 1))
                if k in self.uses:
                    return self.uses[k]
        return []

    def render(self, chars, baseline=None, em=10.9, extra='', cls='mi', rect=None, pad=0.4, label=''):
        """Inline SVG for the given chars. baseline: y of the text line (for vertical alignment).
        extra: raw SVG markup (rules). rect: force this box instead of the ink box."""
        parts = []; x0 = y0 = 1e9; x1 = y1 = -1e9; seen = set()
        for ch in chars:
            for font_id, mt in self.find(ch):
                key = (font_id, mt)
                if key in seen: continue
                seen.add(key)
                d = self.defs.get(font_id)
                if not d: continue
                g = self.store.gid(d)
                ux0, uy0, ux1, uy1 = self.store.bbox[g]
                a, b, c, dd, e, f = mt
                for ux, uy in ((ux0, uy0), (ux0, uy1), (ux1, uy0), (ux1, uy1)):
                    X = a * ux + c * uy + e; Y = b * ux + dd * uy + f
                    x0 = min(x0, X); x1 = max(x1, X); y0 = min(y0, Y); y1 = max(y1, Y)
                parts.append(f'<use href="#{g}" transform="matrix({fnum(a)} {fnum(b)} {fnum(c)} {fnum(dd)} {fnum(e)} {fnum(f)})"/>')
            if ch['c'].strip():
                x0 = min(x0, ch['x0']); x1 = max(x1, ch['x1'])
        if rect is not None:
            x0, y0, x1, y1 = rect
        else:
            x0 -= pad; y0 -= pad; x1 += pad; y1 += pad
        if not parts and not extra:
            return ''
        w = x1 - x0; h = y1 - y0
        style = f'width:{w / em:.3f}em'
        if baseline is not None:
            style += f';height:{h / em:.3f}em;vertical-align:{-(y1 - baseline) / em:.3f}em'
        lab = f' role="img" aria-label="{html.escape(label, quote=True)}"' if label else ' aria-hidden="true"'
        return f'<svg class="{cls}" viewBox="{fnum(x0)} {fnum(y0)} {fnum(w)} {fnum(h)}" style="{style}"{lab}>{"".join(parts)}{extra}</svg>'


def rules_svg(page, rect):
    """Straight strokes and thin filled bars (table rules, fraction bars) inside rect, as SVG."""
    out = []
    R = fitz.Rect(rect)
    for dr in page.get_drawings():
        r = dr['rect']
        if not R.intersects(r) and not (r.width == 0 or r.height == 0): continue
        if r.x1 < R.x0 - 0.5 or r.x0 > R.x1 + 0.5 or r.y1 < R.y0 - 0.5 or r.y0 > R.y1 + 0.5: continue
        col = dr.get('color') or dr.get('fill') or (0, 0, 0)
        if min(col) > 0.92: continue                          # white underlay
        hexc = '#%02x%02x%02x' % tuple(int(255 * v) for v in col)
        w = dr.get('width') or 0.4
        for it in dr['items']:
            if it[0] == 'l':
                p1, p2 = it[1], it[2]
                out.append(f'<line x1="{fnum(p1.x)}" y1="{fnum(p1.y)}" x2="{fnum(p2.x)}" y2="{fnum(p2.y)}" stroke="{hexc}" stroke-width="{fnum(w)}"/>')
            elif it[0] == 're':
                q = it[1]
                if dr.get('fill') is not None and (q.width < 3 or q.height < 3):
                    out.append(f'<rect x="{fnum(q.x0)}" y="{fnum(q.y0)}" width="{fnum(max(q.width, 0.3))}" height="{fnum(max(q.height, 0.3))}" fill="{hexc}"/>')
                elif dr.get('color') is not None:
                    out.append(f'<rect x="{fnum(q.x0)}" y="{fnum(q.y0)}" width="{fnum(q.width)}" height="{fnum(q.height)}" fill="none" stroke="{hexc}" stroke-width="{fnum(w)}"/>')
    return ''.join(out)
