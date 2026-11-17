# hub2html

Hub2HTML converts Hub 1.1 and later XML documents to XHTML. It maps document
structure and content such as headings, lists, tables, figures, and references
for HTML and EPUB workflows.

## Using Hub2HTML

Import [`xpl/hub2html.xpl`](xpl/hub2html.xpl) in a transpect XProc pipeline and
invoke the `hub2htm:convert` step with the Hub document on its `source` port.
Connect an empty sequence to the `paths` port to use the default stylesheet.
The `target` option defaults to `EPUB2`, and `sections="yes"` enables HTML
section elements for the DocBook hierarchy.

## Development

This fork gives structural headings precedence when both the structural and
metadata title rules match. The focused regression also checks that empty
titles are suppressed and section headings retain their depth.

To run the regression, install [`tests/requirements.txt`](tests/requirements.txt)
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
