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

## Contributing

See the [regression test guide](tests/README.md) for setup and commands.
