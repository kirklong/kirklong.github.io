#!/usr/bin/env python3
"""Convert a trusted Markdown draft into a standalone blog reading page."""

import argparse
from html import escape
from html.parser import HTMLParser
import os
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit

from markdown_it import MarkdownIt
from mdit_py_plugins.dollarmath import dollarmath_plugin
from mdit_py_plugins.footnote import footnote_plugin


def math_html(content, display=False):
    # Only backslash delimiters reach MathJax: escaped dollar prices stay literal.
    tag, kind, opening, closing = (
        ('div', 'display', r'\[', r'\]') if display
        else ('span', 'inline', r'\(', r'\)')
    )
    return f'<{tag} class="math-{kind}">{opening}{escape(content)}{closing}</{tag}>'


def bracket_math(state, silent):
    """Consume TeX before Markdown's escape/emphasis rules (never inside code)."""
    opening = state.src[state.pos:state.pos + 2]
    if opening not in (r'\(', r'\['):
        return False
    closing = r'\)' if opening == r'\(' else r'\]'
    end = state.src.find(closing, state.pos + 2)
    if end < 0:
        return False
    if not silent:
        token = state.push('bracket_math', '', 0)
        token.content = state.src[state.pos + 2:end]
        token.meta['display'] = opening == r'\['
    state.pos = end + 2
    return True


def bracket_math_block(state, start_line, end_line, silent):
    start = state.bMarks[start_line] + state.tShift[start_line]
    if state.sCount[start_line] - state.blkIndent >= 4 or not state.src.startswith(r'\[', start):
        return False
    end = state.src.find(r'\]', start + 2)
    if end < 0 or end >= state.eMarks[end_line - 1]:
        return False
    last_line = start_line
    while state.eMarks[last_line] < end + 2:
        last_line += 1
    if state.src[end + 2:state.eMarks[last_line]].strip():
        return False
    if silent:
        return True
    token = state.push('bracket_math', '', 0)
    token.content = state.src[start + 2:end]
    token.meta['display'] = True
    token.block = True
    token.map = [start_line, last_line + 1]
    state.line = last_line + 1
    return True


def youtube_id(url):
    parsed = urlsplit(url)
    if parsed.scheme not in ('http', 'https'):
        return None
    host = (parsed.hostname or '').lower()
    if host in ('youtu.be', 'www.youtu.be'):
        candidate = parsed.path.strip('/')
    elif host in ('youtube.com', 'www.youtube.com', 'm.youtube.com',
                  'youtube-nocookie.com', 'www.youtube-nocookie.com'):
        candidate = (parse_qs(parsed.query).get('v', [''])[0]
                     if parsed.path == '/watch'
                     else parsed.path.split('/')[-1]
                     if parsed.path.startswith(('/embed/', '/shorts/')) else '')
    else:
        return None
    return candidate if re.fullmatch(r'[\w-]{11}', candidate, flags=re.ASCII) else None


def parser():
    md = MarkdownIt('commonmark', {'html': True}).enable(['table', 'strikethrough'])
    md.use(footnote_plugin)
    md.use(dollarmath_plugin, allow_labels=False, allow_space=False,
           double_inline=True,
           renderer=lambda content, options: escape(content))

    def render_math(self, tokens, idx, options, env):
        token = tokens[idx]
        display = token.meta.get('display', False) or token.type in ('math_block', 'math_inline_double')
        # Inline display math uses a span to preserve valid paragraph markup.
        result = math_html(token.content, display)
        return result if token.block else result.replace('<div ', '<span ').replace('</div>', '</span>')

    md.inline.ruler.before('escape', 'bracket_math', bracket_math)
    md.block.ruler.before('fence', 'bracket_math', bracket_math_block,
                          {'alt': ['paragraph', 'reference', 'blockquote', 'list']})
    for name in ('bracket_math', 'math_inline', 'math_inline_double', 'math_block'):
        md.add_render_rule(name, render_math)

    image_renderer = md.renderer.rules['image']

    def render_media(self, tokens, idx, options, env):
        token = tokens[idx]
        src = token.attrGet('src') or ''
        description = self.renderInlineAsText(token.children or [], options, env)
        video_id = youtube_id(src)
        if video_id:
            return (f'<iframe src="https://www.youtube.com/embed/{video_id}" '
                    f'title="{escape(description or "YouTube video", quote=True)}" '
                    'loading="lazy" allow="accelerometer; autoplay; clipboard-write; '
                    'encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>')
        if Path(urlsplit(src).path).suffix.lower() in ('.mp4', '.webm', '.ogg', '.ogv', '.mov', '.m4v'):
            return (f'<video controls playsinline preload="metadata" src="{escape(src, quote=True)}" '
                    f'aria-label="{escape(description, quote=True)}">'
                    f'<a href="{escape(src, quote=True)}">{escape(description or "Download video")}</a></video>')
        return image_renderer(tokens, idx, options, env)

    md.add_render_rule('image', render_media)
    return md


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            self.parts.append(dict(attrs).get('alt', ''))


def document(content, title, assets='.'):
    """Assets point back to the site root; media stay relative to the output."""
    base = escape(assets.rstrip('/'), quote=True)
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<link rel="icon" href="{base}/img/favicon.ico">
<link href="https://fonts.googleapis.com/css?family=Montserrat:400,700" rel="stylesheet">
<link href="{base}/css/blog.css" rel="stylesheet">
<script>
window.MathJax = {{
  tex: {{inlineMath: [['\\\\(', '\\\\)']], displayMath: [['\\\\[', '\\\\]']]}},
  options: {{skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code']}}
}};
</script>
<script defer src="https://cdn.jsdelivr.net/npm/mathjax@4/tex-svg.js"></script>
</head>
<body class="blog-page">
<a class="blog-home" href="{base}/index.html">&larr; Back to home</a>
<main>
<article class="blog-article" id="blogPost">
{content}
</article>
</main>
</body>
</html>
'''


def convert(source, fallback_title, assets='.'):
    md = parser()
    env = {}
    tokens = md.parse(source, env)
    title = fallback_title
    for idx, token in enumerate(tokens):
        if token.type == 'heading_open' and token.tag == 'h1':
            text = PlainText()
            text.feed(md.renderer.renderInline(tokens[idx + 1].children or [], md.options, env))
            title = ''.join(text.parts)
            break
    return document(md.renderer.render(tokens, md.options, env), title, assets)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('input', type=Path, help='UTF-8 Markdown draft')
    cli.add_argument('-o', '--output', type=Path, help='default: input path with .html extension')
    cli.add_argument('--force', action='store_true', help='allow replacing an existing output')
    args = cli.parse_args()
    output = args.output or args.input.with_suffix('.html')
    if args.input.resolve() == output.resolve():
        cli.error('input and output must be different files')
    try:
        source = args.input.read_text(encoding='utf-8')
        root = Path(__file__).resolve().parent.parent
        assets = Path(os.path.relpath(root, output.resolve().parent)).as_posix()
        result = convert(source, args.input.stem, assets)
        # Exclusive creation avoids accidental overwrites, including concurrent runs.
        with output.open('w' if args.force else 'x', encoding='utf-8') as handle:
            handle.write(result)
    except FileExistsError:
        cli.error(f'output already exists: {output}; use --force to overwrite')
    except (OSError, UnicodeError) as error:
        cli.error(str(error))
    print(f'Wrote {output}')


if __name__ == '__main__':
    main()
