# hub2html
Converts Hub XML to XHTML

Structural titles (including `info/title` inside a chapter, book, or other
structural element) take precedence over the general metadata-title rule.
Empty titles remain suppressed; section headings retain their depth.

To run the focused conversion regression, install `tests/requirements.txt`
in a Python environment and provide a checkout of `transpect/xslt-util` at
`5d78dff50bf197e7973c5dcf92b921e08c4ae6cc`:

```sh
python tests/title_priority.py --xslt-util /path/to/xslt-util
```

The test runs the real `main` template with pinned SaxonC-HE 12.9 and local
catalog resolution for the stylesheet dependencies. It rejects ambiguous title
matches, checks structural headings and their inline language/style context,
and checks empty titles, metadata, and section depth. CI additionally exports
pristine upstream `ee25fb16ce4819ef6ab880889e9761d8e5768ef3` and passes it via
`--baseline-root /path/to/export` to reproduce `XTDE0540` as a negative control.
