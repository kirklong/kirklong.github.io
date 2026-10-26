"""Run with: python3 -m unittest discover -s tests -v"""

from html.parser import HTMLParser
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from markdown_to_html import convert

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'markdown_to_html.py'


class Elements(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.tags = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class ConverterTests(unittest.TestCase):
    def test_title_formatting_and_unicode(self):
        page = convert('# 北京 *stars* & sky\n\n## Subtitle\n\n~~old~~\n\n'
                       '> Quote\n\n- One\n- Two\n\n1. First\n\n'
                       '| A | B |\n| --- | --- |\n| α | β |\n\n'
                       'Note[^1]\n\n[^1]: A footnote.\n', 'fallback')
        self.assertIn('<title>北京 stars &amp; sky</title>', page)
        self.assertEqual(page.count('<h1>'), 1)
        for marker in ('<s>old</s>', '<blockquote>', '<ul>', '<ol>', '<table>', 'class="footnotes', 'A footnote.'):
            self.assertIn(marker, page)
        self.assertIn('<title>filename</title>', convert('No heading', 'filename'))

    def test_math_is_protected_and_code_is_literal(self):
        source = r'''Inline $a_b * c < d$ and \(x_1 * y_2\).

$$
\begin{aligned}
a_1 &= b_2 \\
c &= d
\end{aligned}
$$

\[
x_1 + x_2

= y_3
\]

Escaped \$5 and \$10. Code `$x_y$` and `\(z\)`.

```text
$$not_math$$
\[not_math\]
```

    $indented_code$
'''
        page = convert(source, 'Math')
        self.assertIn(r'\(a_b * c &lt; d\)', page)
        self.assertIn(r'\(x_1 * y_2\)', page)
        self.assertIn('a_1 &amp;= b_2', page)
        self.assertIn('x_1 + x_2\n\n= y_3', page)
        self.assertIn('Escaped $5 and $10.', page)
        self.assertIn('<code>$x_y$</code>', page)
        self.assertIn('<code>\\(z\\)</code>', page)
        self.assertIn('$$not_math$$\n\\[not_math\\]', page)
        self.assertIn('<pre><code>$indented_code$', page)
        self.assertNotIn('<em>', page)

    def test_media_and_raw_html(self):
        page = convert('![Photo](img/photo.jpg)\n\n'
                       '![A & B](vid/clip.MP4?download=1)\n\n'
                       '![Player](https://youtu.be/JBzDRFJi6KQ)\n\n'
                       '![Watch](https://www.youtube.com/watch?v=JBzDRFJi6KQ)\n\n'
                       '<figure><figcaption>My caption</figcaption></figure>', 'Media')
        tags = Elements(page).tags
        self.assertIn(('img', {'src': 'img/photo.jpg', 'alt': 'Photo'}), tags)
        video = next(attrs for tag, attrs in tags if tag == 'video')
        self.assertIn('controls', video)
        self.assertEqual(video['src'], 'vid/clip.MP4?download=1')
        self.assertEqual(video['aria-label'], 'A & B')
        frames = [attrs for tag, attrs in tags if tag == 'iframe']
        self.assertEqual(len(frames), 2)
        self.assertTrue(all(a['src'] == 'https://www.youtube.com/embed/JBzDRFJi6KQ' for a in frames))
        self.assertIn('<figure><figcaption>My caption</figcaption></figure>', page)

    def test_cli_errors_preserve_files_and_default_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            draft = Path(tmp) / 'draft.md'
            output = draft.with_suffix('.html')
            draft.write_text('# My draft\n\n你好', encoding='utf-8')

            def run(*args):
                return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                                      capture_output=True, text=True)

            self.assertEqual(run(draft).returncode, 0)
            original = output.read_bytes()
            self.assertIn(b'<title>My draft</title>', original)
            rejected = run(draft)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn('--force', rejected.stderr)
            self.assertEqual(output.read_bytes(), original)
            self.assertNotEqual(run(Path(tmp) / 'missing.md', '-o', output, '--force').returncode, 0)
            self.assertEqual(output.read_bytes(), original)
            self.assertNotEqual(run(draft, '-o', draft, '--force').returncode, 0)
            self.assertEqual(draft.read_text(encoding='utf-8'), '# My draft\n\n你好')
            draft.write_text('# Replaced', encoding='utf-8')
            self.assertEqual(run(draft, '--force').returncode, 0)
            self.assertIn('<title>Replaced</title>', output.read_text())


if __name__ == '__main__':
    unittest.main()
