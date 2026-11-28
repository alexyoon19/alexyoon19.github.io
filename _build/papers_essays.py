"""Convert the short course essays (Pages and Word files) to block JSON for the blog.

LibreOffice first turns each .pages file into .docx (soffice --headless --convert-to docx);
pandoc then gives clean HTML, which is cut into paragraphs and notes here.
The class header (name, instructor, course, date) and the essay's own title are dropped from the body:
the title is kept in content.py as the entry's 'subtitle'.

Typing slips can be corrected on the way through: pass a JSON file of the form
{slug: [[as typed, as published], ...]}. Each 'as typed' string must occur exactly once in the essay,
or the run stops, so a correction can never land in the wrong place.

Usage: python3 papers_essays.py <folder with the .docx files> <output folder> [corrections.json]
"""
import sys, re, json, subprocess, pathlib

# slug -> (file stem, number of header paragraphs, number of title paragraphs, closing note or None)
ESSAYS = {
    'peace-and-panic': ('CMST_1440_ESSAY_2', 4, 1, None),
    'pursuit-of-a-seagull': ('CMST_14400_-_Visual_Analysis', 4, 2, None),
    'cruda-amarilli': ('02_Yoon', 4, 1, None),
}


def convert(docx):
    out = subprocess.run(['pandoc', '-f', 'docx', '-t', 'html5', '--wrap=none', str(docx)],
                         capture_output=True, text=True, check=True).stdout
    notes = []
    m = re.search(r'<(?:section|aside)[^>]*class="footnotes[^"]*"[^>]*>(.*)</(?:section|aside)>', out, flags=re.S)
    if m:
        for i, li in enumerate(re.findall(r'<li id="fn\d+"[^>]*>(.*?)</li>', m.group(1), flags=re.S), 1):
            t = re.sub(r'<a href="#fnref\d+"[^>]*>.*?</a>', '', li, flags=re.S)
            t = re.sub(r'</?p>', '', t).strip().replace('<em>', '<i>').replace('</em>', '</i>')
            t = re.sub(r'<a href="(https?://[^"]+)">[^<]*</a>',
                       lambda k: '<a href="%s">%s</a>' % (k.group(1), k.group(1).replace('https://www.', '').replace('https://', '')), t)
            notes.append((str(i), t))
        out = out[:m.start()]
    out = re.sub(r'<a href="#fn(\d+)" class="footnote-ref" id="fnref\d+"[^>]*><sup>\d+</sup></a>',
                 r'<sup class="fnref"><a href="#fn\1" id="fnref\1">\1</a></sup>', out)
    paras = re.findall(r'<p>(.*?)</p>', out, flags=re.S)
    paras = [re.sub(r'\s+', ' ', p).replace('<em>', '<i>').replace('</em>', '</i>').strip() for p in paras]
    return [p for p in paras if p], notes


def main(src, dst, fixes=None):
    src, dst = pathlib.Path(src), pathlib.Path(dst)
    FIXES = json.loads(pathlib.Path(fixes).read_text(encoding='utf-8')) if fixes else {}
    for slug, (stem, n_head, n_title, closing) in ESSAYS.items():
        paras, notes = convert(src / (stem + '.docx'))
        head, title, body = paras[:n_head], paras[n_head:n_head + n_title], paras[n_head + n_title:]
        for typed, published in FIXES.get(slug, []):
            hits = sum(p.count(typed) for p in body)
            if hits != 1:
                sys.exit(f'{slug}: expected one occurrence of {typed!r}, found {hits}')
            body = [p.replace(typed, published) for p in body]
        blocks = [{'type': 'p', 'html': p, 'cls': ''} for p in body]
        if closing:
            blocks.append({'type': 'p', 'cls': 'meta ednote', 'html': closing})
        d = {'blocks': blocks, 'notes': notes, 'title_from_file': title}
        (dst / (slug + '.json')).write_text(json.dumps(d, ensure_ascii=False, indent=0), encoding='utf-8')
        words = len(' '.join(re.sub(r'<[^>]+>', '', p) for p in body).split())
        print(f'{slug:22s} {words:5d} words, {len(body):2d} paragraphs, {len(notes)} notes, {len(FIXES.get(slug, []))} fixes')
        print('    header:', ' | '.join(re.sub(r'<[^>]+>', '', h) for h in head))
        print('    title: ', ' '.join(re.sub(r'<[^>]+>', '', t) for t in title))


if __name__ == '__main__':
    main(*sys.argv[1:4])
