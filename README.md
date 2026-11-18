# hub2html

Hub2HTML converts Hub 1.1 and later XML documents to XHTML. It maps document
structure and content such as headings, lists, tables, figures, and references
for HTML and EPUB workflows.

This repository is a fork of [transpect/hub2html](https://github.com/transpect/hub2html),
the original Hub2HTML project.

## Using Hub2HTML

Import [`xpl/hub2html.xpl`](xpl/hub2html.xpl) in a transpect XProc pipeline and
invoke the `hub2htm:convert` step with the Hub document on its `source` port.
Connect an empty sequence to the `paths` port to use the default stylesheet.

The converter copies the source root's `xml:lang` value to the `lang` attribute
on the XHTML `<html>` element. It omits `lang` when the source root has no
`xml:lang`.

## Development

This fork gives structural titles precedence when both the structural and
metadata title rules match.

To run the regression suite, install [`tests/requirements.txt`](tests/requirements.txt)
in a Python environment and provide a checkout of `transpect/xslt-util` at
`5d78dff50bf197e7973c5dcf92b921e08c4ae6cc`:

```sh
python tests/title_priority.py --xslt-util /path/to/xslt-util
```

The suite runs the real `main` template with the pinned SaxonC-HE dependency
and resolves stylesheet dependencies through a local catalog. See the
[full-upstream regression reproduction](tests/README.md) for compatibility
checks against the pinned upstream revision.

CI also exports pristine upstream `ee25fb16ce4819ef6ab880889e9761d8e5768ef3`
and passes it via `--baseline-root /path/to/export` to reproduce `XTDE0540` as
a negative control.
