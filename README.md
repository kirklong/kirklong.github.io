# kirklong.github.io

The template used to make this site is available [here](https://themeforest.net/item/cards-personal-vcard-resumecv-portfolio/13066785) -- please do not just copy it from this repo! It's important to support creators, and it only costs $17 :)

That being said, after purchasing it if you are interested in some tweaks I made feel free to gander at the code here. To get the custom domain (kirklong.space) I used Google domains, paying them $20/yr for the privilege of a more personalized site name, but it just forwards to the original github.io site, so all the hosting is still done for free with Github pages.

## Writing blog posts in Markdown

Install the converter dependencies in a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r scripts/requirements.txt
```

Convert a UTF-8 draft into a complete reading page:

```bash
python3 scripts/markdown_to_html.py draft.md -o new-post.html
# Try the included example:
python3 scripts/markdown_to_html.py examples/blog-draft.md -o example-post.html
```

Without `-o`, the output uses the input path with an `.html` extension. Existing
outputs require `--force` to replace them. The browser title comes from the first
H1, or the draft's filename if there is no H1. The H1 appears once in the article.

The converter uses [markdown-it-py](https://markdown-it-py.readthedocs.io/en/latest/using.html)
and [mdit-py-plugins](https://mdit-py-plugins.readthedocs.io/en/latest/) for headings,
lists, links, blockquotes, fenced code, tables, strikethrough, and footnotes. Raw
HTML is preserved for custom embeds and captions; use drafts you trust.

Use ordinary image syntax for photos and the same syntax for video shortcuts:

```markdown
![Description](img/photo.jpg)
![Description](vid/clip.mp4)
![Description](https://youtu.be/JBzDRFJi6KQ)
```

Local videos get playback controls. YouTube short, watch, shorts, and embed URLs
become responsive players. Raw YouTube iframe embeds are responsive too. Media
paths are relative to the **output HTML**, and media are not copied or uploaded.
Site stylesheet, favicon, and home links are calculated relative to the output
directory. Keep the generated page inside this site when publishing it.

Use `$...$` or `\(...\)` for inline equations, and `$$...$$` or `\[...\]` for
display equations, including multiline expressions. Escape literal dollar signs
as `\$`. Code spans and code blocks remain literal. Equations are rendered by
[MathJax](https://docs.mathjax.org/en/latest/web/start.html) in the browser;
MathJax, Google Fonts, and hosted videos require network access.

All reading pages share `css/blog.css`: a wide light article over the scenic
background, normal document scrolling, and one fixed home link. Preview cards
remain manual edits in `index.html`; the converter does not change the blog list.

Preview locally and run converter checks:

```bash
python3 -m http.server 8000
# In another terminal, with the virtual environment active:
python3 -m unittest discover -s tests -v
```
