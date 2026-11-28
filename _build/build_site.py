"""Build the whole site into ./out from content.py, the paper files in ./papers and ./assets."""
import json, math, pathlib, re, shutil, sys, html

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import content as C

OUT = HERE / 'out'
PAPERS = HERE / 'papers'
SITE_URL = 'https://alexyoon19.github.io/'

# ---------------------------------------------------------------- colour: three field inks, mixed in OKLab
HUE = {'phys': 255, 'econ': 145, 'phil': 25}
CHROMA = 0.12


def oklab_to_hex(L, a, b):
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    rgb = [4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
           -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
           -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s]
    out = []
    for c in rgb:
        c = min(1.0, max(0.0, c))
        c = 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
        out.append(round(c * 255))
    return '#%02x%02x%02x' % tuple(out)


def ink(deg):
    r = math.radians(deg)
    return CHROMA * math.cos(r), CHROMA * math.sin(r)


INK = {k: ink(v) for k, v in HUE.items()}


def colours(mix):
    p, e, h = mix
    a = p * INK['phys'][0] + e * INK['econ'][0] + h * INK['phil'][0]
    b = p * INK['phys'][1] + e * INK['econ'][1] + h * INK['phil'][1]
    return oklab_to_hex(0.93, 0.5 * a, 0.5 * b), oklab_to_hex(0.50, a, b)


def token(n, mix, progress=False, cls='mark'):
    fill, ring = colours(mix)
    dash = ' in-progress' if progress else ''
    return (f'<svg class="{cls} token{dash}" viewBox="0 0 30 30" aria-hidden="true" style="--fill:{fill};--ring:{ring}">'
            f'<circle cx="15" cy="15" r="12.5"/><text x="15" y="15">{n}</text></svg>')


# ---------------------------------------------------------------- shared shell
FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Cpath d='M16 5 28.5 26.5h-25Z' fill='none' stroke='%23000' stroke-width='2.2' stroke-linejoin='round'/%3E"
           "%3Ccircle cx='16' cy='5' r='3' fill='%23c46761'/%3E%3Ccircle cx='3.5' cy='26.5' r='3' fill='%235188cd'/%3E%3Ccircle cx='28.5' cy='26.5' r='3' fill='%23549957'/%3E%3C/svg%3E")


def strip(s):
    return html.unescape(re.sub(r'<[^>]+>', '', s))


def shell(path, title, body, current, desc, depth=0, scripts=False, head_extra=''):
    root = '../' * depth
    nav = ''.join(f'<a href="{root}{href}"{" aria-current=\"page\"" if href == current else ""}>{label.replace("&", "&amp;")}</a>' for href, label in C.NAV)
    full = C.NAME if path == 'index.html' else f'{strip(title)} — {C.NAME}'
    name = (f'<h1 class="site-name">{C.NAME}</h1>' if path == 'index.html'
            else f'<a class="site-name" href="{root}index.html">{C.NAME}</a>')
    url = SITE_URL + ('' if path == 'index.html' else path)
    js = f'<script src="{root}assets/site.js" defer></script>' if scripts else ''
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>{html.escape(full)}</title>
<meta name="description" content="{html.escape(desc, quote=True)}">
<meta property="og:type" content="website">
<meta property="og:title" content="{html.escape(full, quote=True)}">
<meta property="og:description" content="{html.escape(desc, quote=True)}">
<meta property="og:url" content="{url}">
<link rel="canonical" href="{url}">
<link rel="icon" href="{FAVICON}">
<link rel="preload" href="{root}assets/fonts/lm10-regular.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{root}assets/site.css">{head_extra}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-head"><div class="wrap">
{name}
<nav aria-label="Main">{nav}</nav>
</div></header>
<main id="main" class="wrap">
{body}
</main>
<footer class="site-foot"><div class="wrap"><p>Last updated {C.UPDATED}</p></div></footer>
{js}
</body>
</html>
'''


def write(path, text):
    f = OUT / path
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, encoding='utf-8')


def has_page(w):
    return bool(w.get('slug')) and (PAPERS / (w['slug'] + '.json')).exists()


def listing_page(w):
    return 'research.html' if w['group'] == 'published' else 'working.html'


# ---------------------------------------------------------------- Figure 1
BLOG = [w for w in C.WORKS if w['group'] == 'blog']
V = {'phil': (220.0, 52.0), 'phys': (60.0, 329.1), 'econ': (380.0, 329.1)}
RING = {'phys': '#5188cd', 'econ': '#4f9453', 'phil': '#c46761'}


def place(mix):
    p, e, h = mix
    return (p * V['phys'][0] + e * V['econ'][0] + h * V['phil'][0], p * V['phys'][1] + e * V['econ'][1] + h * V['phil'][1])


def figure_one():
    tri = f"{V['phil'][0]},{V['phil'][1]} {V['econ'][0]},{V['econ'][1]} {V['phys'][0]},{V['phys'][1]}"
    rings = []
    for k in ('phys', 'econ', 'phil'):
        cx, cy = V[k]
        arcs = []
        for n in range(1, 16):
            r = 21.33 * n
            op = 0.10 + 0.80 * (1 - r / 330) ** 1.35
            arcs.append(f'<circle cx="{cx}" cy="{cy}" r="{r:.1f}" stroke-opacity="{op:.2f}"/>')
        rings.append(f'<g class="rings" stroke="{RING[k]}">{"".join(arcs)}</g>')

    def tok(w, x, y, label=None, wide=False):
        fill, ring = colours(w['mix'])
        linked = has_page(w)
        href = f"writings/{w['slug']}.html" if linked else f"{listing_page(w)}#w{w['n']}"
        state = 'In progress' if w.get('progress') else ''
        link = 'Read it' if linked else ('' if w.get('progress') else 'See the entry')
        cls = 'token in-progress' if w.get('progress') else 'token'
        lab = label or str(w['n'])
        shape = (f'<rect x="{x - 19:.1f}" y="{y - 11:.1f}" width="38" height="22" rx="11"/>' if wide
                 else f'<circle cx="{x:.1f}" cy="{y:.1f}" r="11"/>')
        title = w['title'] if not wide else 'Blog: essays in philosophy, film and music'
        desc = w['desc'] if not wide else f'{len(BLOG)} essays, 2021–2024.'
        if wide:
            href = 'working.html#blog'; link = 'See the essays'; state = ''
        return (f'<a class="{cls}" href="{href}" data-title="{html.escape(title, quote=True)}" data-desc="{html.escape(desc, quote=True)}" '
                f'data-state="{state}" data-link="{link}" style="--fill:{fill};--ring:{ring}">'
                f'<title>{lab}. {html.escape(strip(title))}</title>{shape}<text x="{x:.1f}" y="{y:.1f}">{lab}</text></a>')

    W = {w['n']: w for w in C.WORKS}
    toks = []
    toks.append(tok(W[2], V['phil'][0] - 21, V['phil'][1]))
    toks.append(tok(BLOG[0], V['phil'][0] + 20, V['phil'][1], label=f"{BLOG[0]['n']}–{BLOG[-1]['n']}", wide=True))
    toks.append(tok(W[1], V['econ'][0] - 13, V['econ'][1]))
    toks.append(tok(W[3], V['econ'][0] + 12, V['econ'][1]))
    for n in (4, 5, 6):
        x, y = place(W[n]['mix'])
        toks.append(tok(W[n], x, y))
    return f'''<figure id="figure-1">
<div class="fig-box">
<svg id="simplex" viewBox="0 0 440 372" role="group" aria-labelledby="figure-1-caption">
<defs><clipPath id="tri"><polygon points="{tri}"/></clipPath></defs>
<g clip-path="url(#tri)" aria-hidden="true">{"".join(rings)}</g>
<polygon class="frame" points="{tri}"/>
<text class="vertex" x="{V['phil'][0]}" y="24">Philosophy</text>
<text class="vertex" x="{V['phys'][0]}" y="361">Physics</text>
<text class="vertex" x="{V['econ'][0]}" y="361">Economics</text>
{"".join(toks)}
</svg>
<div class="fig-card" id="fig-card" hidden></div>
</div>
<figcaption id="figure-1-caption"><b>Figure 1.</b> My writing, placed among the three fields I trained in. Hover over or tap a number to see the paper. Dashed rings mark work in progress.</figcaption>
</figure>'''


# ---------------------------------------------------------------- pages
def page_about():
    bio = ''.join(f'<p>{p}</p>' for p in C.BIO + [C.MINNE])
    fig = figure_one() if C.SHOW_FIGURE else ''
    body = f'''<p class="lede meta">{C.AFFILIATION}</p>
<div class="bio">{bio}</div>
{fig}'''
    desc = 'Alex Yoon is a master’s student in financial engineering at Columbia University, working where physics, economics and philosophy meet.'
    write('index.html', shell('index.html', C.NAME, body, 'index.html', desc, scripts=C.SHOW_FIGURE))


def rows(items):
    return '<ul class="rows cv">' + ''.join(
        f'<li><span class="org">{org}</span><span class="role">{role}</span><span class="when">{when}</span></li>' for org, role, when in items) + '</ul>'


def page_resume():
    body = f'<h1>Résumé</h1>\n<h2>Positions</h2>\n{rows(C.POSITIONS)}\n<h2>Education</h2>\n{rows(C.EDUCATION)}'
    write('resume.html', shell('resume.html', 'Résumé', body, 'resume.html', 'Positions Alex Yoon has held, and his education.'))


PLAIN = '' if C.SHOW_FIGURE else ' plain'


def work_item(w):
    linked = has_page(w)
    t = f'<a href="writings/{w["slug"]}.html">{w["title"]}</a>' if linked else w['title']
    mark = token(w["n"], w["mix"], w.get("progress")) if C.SHOW_FIGURE else ''
    return (f'<li id="w{w["n"]}">{mark}<div>'
            f'<p class="t">{t}</p><p class="d">{w["desc"]}</p><p class="meta">{w["meta"]}</p></div></li>')


def page_published():
    items = ''.join(work_item(w) for w in C.WORKS if w['group'] == 'published')
    body = f'<h1>Research papers</h1>\n<ol class="works{PLAIN}">{items}</ol>'
    write('research.html', shell('research.html', 'Research papers', body, 'research.html', 'Research papers by Alex Yoon: two honors theses and a policy study.'))


def page_working():
    wp = ''.join(work_item(w) for w in C.WORKS if w['group'] == 'working')
    # the blog is split by topic, in the order set by BLOG_TOPICS; within a topic, entries keep their order in WORKS
    blog = ''
    for key, label in C.BLOG_TOPICS:
        items = ''.join(work_item(w) for w in C.WORKS if w['group'] == 'blog' and w['topic'] == key)
        if items:
            blog += f'<h3 class="topic" id="{key}">{label}</h3>\n<ol class="works{PLAIN}">{items}</ol>\n'
    body = (f'<h1>Working papers &amp; blog</h1>\n<h2>Working papers</h2>\n<ol class="works{PLAIN}">{wp}</ol>\n'
            f'<h2 id="blog">Blog</h2>\n<p class="meta intro">{C.BLOG_INTRO}</p>\n{blog}')
    write('working.html', shell('working.html', 'Working papers & blog', body, 'working.html', 'Work in progress and essays by Alex Yoon.'))


def page_honors():
    items = ''
    for year, name, where, note in C.HONORS:
        n = f'<p class="note">{note}</p>' if note else ''
        items += f'<li><span class="when">{year}</span><div><p><b>{name}</b>, {where}</p>{n}</div></li>'
    body = f'<h1>Honors and awards</h1>\n<ul class="rows honors">{items}</ul>'
    write('honors.html', shell('honors.html', 'Honors and awards', body, 'honors.html', 'Honors and awards received by Alex Yoon.'))


def page_contact():
    li = ''
    if C.EMAIL:
        li += f'<li><span class="when">Email</span><a href="mailto:{C.EMAIL}">{C.EMAIL}</a></li>'
    li += f'<li><span class="when">LinkedIn</span><a href="{C.LINKEDIN}">{C.LINKEDIN.replace("https://www.", "")}</a></li>'
    body = f'<h1>Contact</h1>\n<ul class="rows contact">{li}</ul>'
    write('contact.html', shell('contact.html', 'Contact', body, 'contact.html', 'How to reach Alex Yoon.'))


# ---------------------------------------------------------------- paper pages
def render_blocks(blocks):
    out = []; toc = []; in_list = None; hn = 0
    def close_list():
        nonlocal in_list
        if in_list: out.append(f'</{in_list}>'); in_list = None
    for b in blocks:
        t = b['type']
        if t == 'li':
            tag = 'ol' if b.get('ordered') else 'ul'
            if in_list != tag:
                close_list(); out.append(f'<{tag}>'); in_list = tag
            out.append(f'<li>{b["html"]}</li>'); continue
        close_list()
        if t == 'p':
            cls = f' class="{b["cls"]}"' if b.get('cls') else ''
            out.append(f'<p{cls}>{b["html"]}</p>')
        elif t == 'blockquote':
            out.append(f'<blockquote><p>{b["html"]}</p></blockquote>')
        elif t in ('h2', 'h3', 'h4'):
            hn += 1; hid = f's{hn}'
            num = f'<span class="num">{b["num"]}</span>' if b.get('num') else ''
            out.append(f'<{t} id="{hid}">{num}{b["html"]}</{t}>')
            if t == 'h2': toc.append((hid, (b.get('num', '') + ' ' + b['html']).strip()))
        elif t == 'dedication':
            out.append('<p class="dedication">' + re.sub(r'</?i>', '', b['html']) + '</p>')
        elif t == 'eq':
            no = f'<span class="eqno meta">({b["num"]})</span>' if b.get('num') else '<span></span>'
            out.append(f'<div class="eq"><div class="eqbox">{b["svg"]}</div>{no}</div>')
        elif t == 'figure':
            note = f'<span class="fnote">{b["note"]}</span>' if b.get('note') else ''
            media = f'<img src="{b["src"]}" alt="" width="{b["w"]}" height="{b["h"]}" style="width:{b["em"]}em" loading="lazy">'
            out.append(f'<figure class="float">{media}<figcaption>{b["caption"]}{note}</figcaption></figure>')
        elif t == 'table':
            note = f'<span class="fnote">{b["note"]}</span>' if b.get('note') else ''
            out.append(f'<figure class="float"><figcaption>{b["caption"]}{note}</figcaption><div class="scroll">{b["svg"]}</div></figure>')
        elif t == 'refs':
            out.append('<div class="refs">' + ''.join(f'<p>{r}</p>' for r in b['items']) + '</div>')
        elif t == 'raw':
            out.append(b['html'])
    close_list()
    return '\n'.join(out), toc


def page_paper(w):
    d = json.loads((PAPERS / (w['slug'] + '.json')).read_text())
    body, toc = render_blocks(d['blocks'])
    back = listing_page(w)
    back_label = 'Research papers' if w['group'] == 'published' else 'Working papers &amp; blog'
    parts = [f'<p class="crumb"><a href="../{back}">{back_label}</a></p>', '<article class="paper">', f'<h1>{w["title"]}</h1>']
    if w.get('subtitle'): parts.append(f'<p class="subtitle">{w["subtitle"]}</p>')
    parts.append(f'<p class="meta">{w.get("page_meta", w["meta"])}</p>')
    if d.get('byline'): parts.append(f'<p class="meta">{d["byline"]}</p>')
    if d.get('abstract'):
        parts.append(f'<div class="abstract"><span class="label">Abstract</span>{d["abstract"]}</div>')
    if d.get('keywords'):
        parts.append(f'<p class="kw"><span class="label">Keywords</span>{d["keywords"]}</p>')
    if len(toc) >= 3:
        parts.append('<nav class="toc" aria-label="Contents"><ol>' + ''.join(f'<li><a href="#{i}">{t}</a></li>' for i, t in toc) + '</ol></nav>')
    parts.append(f'<div class="body">{d.get("glyphdefs", "")}\n{body}\n</div>')
    if d.get('notes'):
        notes = ''.join(f'<li id="fn{n}"><a class="fnnum" href="#fnref{n}" aria-label="Back to the text at note {n}">{n}</a><span>{h}</span></li>' for n, h in d['notes'])
        parts.append(f'<section class="notes" aria-label="Notes"><h2>Notes</h2><ol>{notes}</ol></section>')
    parts.append('</article>')
    desc = strip(w['desc'])
    write(f'writings/{w["slug"]}.html', shell(f'writings/{w["slug"]}.html', strip(w['title']), '\n'.join(parts), back, desc, depth=1))


def main():
    if OUT.exists(): shutil.rmtree(OUT)
    (OUT / 'assets' / 'fonts').mkdir(parents=True)
    for f in (HERE / 'fonts').glob('*.woff2'):
        if f.name.startswith(('lm10-', 'lm17-')) or f.name in ('jost-400.woff2', 'jost-500.woff2'):
            shutil.copy(f, OUT / 'assets' / 'fonts' / f.name)
    shutil.copy(HERE / 'assets' / 'site.css', OUT / 'assets' / 'site.css')
    if C.SHOW_FIGURE: shutil.copy(HERE / 'assets' / 'site.js', OUT / 'assets' / 'site.js')
    if (HERE / 'media').exists():
        shutil.copytree(HERE / 'media', OUT / 'writings' / 'media')
    (OUT / '.nojekyll').write_text('')
    page_about(); page_resume(); page_published(); page_working(); page_honors(); page_contact()
    n = 0
    for w in C.WORKS:
        if has_page(w):
            page_paper(w); n += 1
    files = sorted(p.relative_to(OUT).as_posix() for p in OUT.rglob('*') if p.is_file())
    size = sum((OUT / f).stat().st_size for f in files)
    print(f'built {len(files)} files, {size / 1024:.0f} KB, {n} paper pages')


if __name__ == '__main__':
    main()
