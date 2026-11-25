"""Convert the prose papers (word-processor PDFs and the two Pages files) to block JSON."""
import sys, re, json, subprocess, html
sys.path.insert(0, '/home/claude/site2')
import prose

SRC = '/home/claude/writings_src/'
OUT = '/home/claude/site2/papers/'

def from_pdf(name, cfg):
    res = prose.convert(SRC + name, cfg)
    ids = set(res['order'])
    blocks = []
    for b in res['blocks']:
        h = prose.runs_html(b['runs'], ids)
        if not h: continue
        if b['type'] == 'h':
            h = re.sub(r'^<i>(.*)</i>$', r'\1', h) if h.count('<i>') == 1 else h
            blocks.append({'type': 'h2', 'html': h})
        elif b['type'] == 'p':
            cls = 'cont' if b.get('cont') else ('center' if b.get('center') else '')
            blocks.append({'type': 'p', 'html': h, 'cls': cls})
        else:
            blocks.append({'type': b['type'], 'html': h})
    notes = [(n, prose.runs_html(res['notes'][n], None)) for n in res['order']]
    return {'blocks': blocks, 'notes': notes}

def from_pages(stem):
    """LibreOffice already turned the .pages file into .docx; pandoc gives clean HTML."""
    out = subprocess.run(['pandoc', '-f', 'docx', '-t', 'html5', '--wrap=none', SRC + 'lo_out/' + stem + '.docx'], capture_output=True, text=True).stdout
    notes = []
    m = re.search(r'<(?:section|aside)[^>]*class="footnotes[^"]*"[^>]*>(.*)</(?:section|aside)>', out, flags=re.S)
    if m:
        for i, li in enumerate(re.findall(r'<li id="fn\d+"[^>]*>(.*?)</li>', m.group(1), flags=re.S), 1):
            t = re.sub(r'<a href="#fnref\d+"[^>]*>.*?</a>', '', li, flags=re.S)
            t = re.sub(r'</?p>', '', t).strip().replace('<em>', '<i>').replace('</em>', '</i>')
            t = re.sub(r'<a href="(https?://[^"]+)">[^<]*</a>', lambda m: '<a href="%s">%s</a>' % (m.group(1), m.group(1).replace('https://www.', '').replace('https://', '')), t)
            notes.append((str(i), t))
        out = out[:m.start()]
    out = re.sub(r'<a href="#fn(\d+)" class="footnote-ref" id="fnref\d+"[^>]*><sup>\d+</sup></a>', r'<sup class="fnref"><a href="#fn\1" id="fnref\1">\1</a></sup>', out)
    paras = re.findall(r'<p>(.*?)</p>', out, flags=re.S)
    paras = [re.sub(r'\s+', ' ', p).replace('<em>', '<i>').replace('</em>', '</i>').strip() for p in paras]
    paras = [p for p in paras if p]
    # a paragraph cut in two by a page break: the first half has no closing punctuation, the second starts lower-case
    merged = []
    for p in paras:
        txt_prev = re.sub(r'<[^>]+>', '', merged[-1]) if merged else ''
        txt = re.sub(r'<[^>]+>', '', p)
        if merged and not re.search(r'[.?!:"”)\]…]\s*(\d+)?$', txt_prev) and txt[:1].islower():
            merged[-1] = merged[-1] + ' ' + p
        else:
            merged.append(p)
    return merged, notes

docs = {}
docs['existential-kant'] = from_pdf('kant.pdf', {'start_after': r'^The Existential Kant'})
docs['everlasting-masquerade'] = from_pdf('nietzsche.pdf', {'start_after': r'^An Everlasting Masquerade'})
docs['philosophical-schism'] = from_pdf('heidegger_hegel.pdf', {'start_after': r'^Full Authentic Existence'})
docs['beyond-scientific-validity'] = from_pdf('phil_thesis.pdf', {'start_after': r'^Advised by', 'front_pages': {2: 'dedication'}})
docs['power-in-film'] = from_pdf('kant_film.pdf', {'start_after': r'^How Kant.s Theory of Fine Art', 'stop_at': r'^Appendix 1:'})
docs['power-in-film']['blocks'].append({'type': 'p', 'cls': 'meta ednote', 'html': 'The essay’s three appendices are film stills from <i>Interstellar</i>, <i>Life of Pi</i> and <i>Dune</i>. They are left out of this web version.'})

for slug, stem, ntitle in [('balthazar', 'bresson2', 2)]:
    paras, notes = from_pages(stem)
    title = ' '.join(re.sub(r'<[^>]+>', '', p) for p in paras[:ntitle])
    docs[slug] = {'blocks': [{'type': 'p', 'html': p, 'cls': ''} for p in paras[ntitle:]], 'notes': notes, 'title_from_file': paras[:ntitle]}

for slug, d in docs.items():
    json.dump(d, open(OUT + slug + '.json', 'w'), ensure_ascii=False, indent=0)
    txt = ' '.join(re.sub(r'<[^>]+>', '', b['html']) for b in d['blocks'])
    kinds = {}
    for b in d['blocks']: kinds[b['type']] = kinds.get(b['type'], 0) + 1
    refs = re.findall(r'href="#fn(\d+)"', ' '.join(b['html'] for b in d['blocks']))
    print(f"{slug:28s} words {len(txt.split()):6d} blocks {kinds} notes {len(d['notes'])} refs {len(refs)} refs==notes {refs == [n for n, _ in d['notes']]}")
    if d.get('title_from_file'): print('   title:', d['title_from_file'])
