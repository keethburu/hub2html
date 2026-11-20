# Hub2HTML

Hub2HTML converts Hub 1.1 and later XML documents to XHTML. It is the
rendering step in transpect HTML and EPUB workflows, turning Hub headings,
lists, tables, figures, and references into XHTML that downstream steps can
use.

This repository is a fork of the original [transpect/hub2html](https://github.com/transpect/hub2html) project.

## Using Hub2HTML

Configure your transpect XProc 1.0 environment with the
[Hub2HTML XML catalog](xmlcatalog/catalog.xml) and the XML catalogs for its
dependencies. In your pipeline, import [`xpl/hub2html.xpl`](xpl/hub2html.xpl)
and invoke `hub2htm:convert` (`http://transpect.io/hub2htm`).

- Pass the Hub document on the `source` port.
- Pass transpect cascade paths on the `paths` port to select a stylesheet.
  Bind the port with `<p:input port="paths"><p:empty/></p:input>` to use the
  default stylesheet.
- Supply any additional stylesheet parameters on the `other-params` parameter
  port.

Read the converted XHTML from the `result` port.

### Author names

Hub2HTML separates visible structured author name parts with spaces, including
first, middle, and final `othername` components, while preserving authored
whitespace and line breaks. This applies to authors directly under `info`,
`biblioentry`, or `biblioset`, authors in an `authorgroup` directly under those
containers, and authors in their `revhistory/revision` metadata. Names in
running prose, cooked bibliographies (`bibliomixed` or `bibliomset`, including
nested metadata), and standalone revision histories in chapter content or
endnotes retain their existing spacing.

Spacing accounts for `display: none` in emitted inline styles, as well as simple
named Hub classes when `use-css-rules` is `yes` (the default). Inline `display`
overrides are respected. A hidden, padded middle name therefore leaves the visible
name as `Ada Lovelace`. External stylesheets and arbitrary CSS selectors are
not resolved when determining name boundaries.

The spacing contract concerns browser-visible output under those supported
visibility rules. Authored spaces, nonbreaking spaces, narrow nonbreaking
spaces, tabs and breaks retain their own behavior under the consuming
stylesheet's `white-space` setting. Serialized XHTML may contain hidden text
and whitespace that a browser collapses; extracting all text nodes is not a
substitute for rendering. Existing serialized-text regression checks remain
in place, and this follow-up changes no production XHTML. See the
[spacing design note](tests/author-name-spacing.md) for the consumer audit,
browser checks and the reasons for retaining the current implementation.

## Contributing

See the [regression test guide](tests/README.md) for setup and commands.
