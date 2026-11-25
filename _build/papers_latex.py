"""Convert the two LaTeX papers to block JSON (text + redrawn formulas and tables + figure images)."""
import sys, re, json
sys.path.insert(0, '/home/claude/site2')
import latexpdf

SRC = '/home/claude/writings_src/'; OUT = '/home/claude/site2/papers/'
strip = lambda s: re.sub(r'<[^>]+>', '', re.sub(r'<svg.*?</svg>', ' ', s, flags=re.S))

def green_trade():
    slug = 'green-trade'
    cfg = {'body': 10.9, 'left': 72, 'right': 540, 'par_indent': 17, 'page_size': {2: 10.0}, 'par_gap': {2: 40},
           'media_dir': f'/home/claude/site2/media/{slug}', 'media_url': f'media/{slug}/'}
    D = latexpdf.Doc(SRC + 'econ_thesis.pdf', cfg)
    front = D.run([1])['blocks']
    abstract = keywords = ''
    for b in front:
        h = b.get('html', '')
        if strip(h).lstrip().startswith('Abstract'):
            abstract = '<p>' + re.sub(r'^\s*<b>Abstract</b>\s*', '', h) + '</p>'
        elif strip(h).lstrip().startswith('Keywords'):
            keywords = re.sub(r'^\s*<b>Keywords:?</b>:?\s*', '', h)
    D.blocks = []; D.cur = None; D.open_par = None; D.after = 'start'
    res = D.run(range(2, len(D.doc)))
    res['abstract'] = abstract; res['keywords'] = keywords
    return slug, res, D

def pdi():
    slug = 'renewable-energy-tax-incentives'
    cfg = {'body': 10.0, 'left': 57, 'right': 540, 'columns': [(57, 289.5), (307.5, 540)], 'par_indent': 10, 'head_y': 60, 'foot_y': 785,
           'adopt_base': True, 'italic_math': True, 'italic_heads': True, 'pitch': 12.5,
           'fullwidth': [(1, 215, 396)], 'skip': [(1, 0, 0, 600, 214), (1, 0, 752, 298, 780)],
           'media_dir': f'/home/claude/site2/media/{slug}', 'media_url': f'media/{slug}/'}
    D = latexpdf.Doc(SRC + 'pdi.pdf', cfg)
    res = D.run(range(len(D.doc)))
    # abstract = everything before the first numbered heading
    k = next(i for i, b in enumerate(res['blocks']) if b['type'] == 'h2')
    front = res['blocks'][:k]; res['blocks'] = res['blocks'][k:]
    ab = ' '.join(b.get('html', '') for b in front if b['type'] == 'p')
    ab = re.sub(r'^\s*<b>Abstract</b>\s*', '', ab)
    ab = re.sub(r'^<i>(.*)</i>$', r'\1', ab.strip(), flags=re.S) if ab.count('<i>') == 1 else ab
    res['abstract'] = '<p>' + ab + '</p>'
    # byline from the title block
    import fitz
    from rows import page_chars, cluster_rows
    rows = [r for r in cluster_rows([c for c in page_chars(D.doc[0]) if 120 < c['y'] < 182 and c['size'] > 11], tol=1.5) if r['text'].strip()]
    by = ' '.join(re.sub(r'\s+', ' ', r['text']).strip() for r in rows)
    by = re.sub(r'Project Leader:\s*', 'Project leader: ', by); by = re.sub(r'\s*Researchers:\s*', '. Researchers: ', by)
    res['byline'] = html_escape(by) + '.'
    return slug, res, D

def html_escape(s):
    import html
    return html.escape(s, quote=False)

# spelling slips in the original PDFs, corrected on the web version at the author's request
TYPOS = {
    'green-trade': {'Viginia': 'Virginia', 'Viriginia': 'Virginia', 'aribtrary': 'arbitrary', 'electricty': 'electricity',
                    'entrie': 'entire', 'strenght': 'strength', 'utilites': 'utilities'},
    'renewable-energy-tax-incentives': {'imapct': 'impact'},
}

def fix_typos(slug, res):
    fixes = TYPOS.get(slug, {}); n = 0
    def fix(s):
        nonlocal n
        parts = re.split(r'(<svg.*?</svg>|<[^>]+>)', s, flags=re.S)
        for i in range(0, len(parts), 2):
            for a, b in fixes.items():
                parts[i], k = re.subn(r'\b%s\b' % a, b, parts[i]); n += k
        return ''.join(parts)
    for b in res['blocks']:
        for k in ('html', 'caption', 'note'):
            if b.get(k): b[k] = fix(b[k])
    res['notes'] = [(m, fix(h)) for m, h in res['notes']]
    if res.get('abstract'): res['abstract'] = fix(res['abstract'])
    return n

if __name__ == '__main__':
    which = sys.argv[1:] or ['green']
    for w in which:
        slug, res, D = green_trade() if w == 'green' else pdi()
        print('spelling fixes applied:', fix_typos(slug, res))
        json.dump(res, open(OUT + slug + '.json', 'w'), ensure_ascii=False)
        kinds = {}
        for b in res['blocks']: kinds[b['type']] = kinds.get(b['type'], 0) + 1
        refs = re.findall(r'href="#fn([^"]+)"', ' '.join(b.get('html', '') + b.get('caption', '') for b in res['blocks']) + res.get('abstract', ''))
        print(slug, kinds, '| notes', [n for n, _ in res['notes']], '| refs', refs, '| glyph shapes', len(D.store.ids), '| json KB', len(json.dumps(res)) // 1024)
        print('  abstract:', strip(res.get('abstract', ''))[:90], '…', strip(res.get('abstract', ''))[-60:])
        print('  keywords:', strip(res.get('keywords', ''))[:120])
        print('  log:', D.log[:20])
        print('  mended words:', sorted(set(l for l in D.log if l.startswith('dehyphen')))[:60])
