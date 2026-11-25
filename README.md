# alexyoon19.github.io

Personal site of Alex Yoon, served by GitHub Pages from the `main` branch.

- The pages at the top level (`index.html`, `resume.html`, `research.html`, `working.html`, `honors.html`, `contact.html`, `writings/`) are generated files.
- `_build/` holds what generates them: `content.py` is all the text on the site, `papers/` holds each paper's text, and `build_site.py` writes the pages into `_build/out/`. To change the site, edit `content.py`, run `python3 _build/build_site.py`, then copy `_build/out/` over the top level.
- Paper figures live in `writings/media/`. Formulas and tables in the two technical papers are redrawn from the original PDFs' own glyph outlines by `latexpdf.py`.
- Type is Latin Modern (GUST Font License) and Jost (SIL Open Font License).
