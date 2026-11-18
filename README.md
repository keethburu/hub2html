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

## Contributing

See the [regression test guide](tests/README.md) for setup and commands.
