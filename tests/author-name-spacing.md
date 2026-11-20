# Author-name spacing contract

Name handling follows the original transpect implementation at
[5417ccf](https://github.com/transpect/hub2html/commit/5417ccf4a859386866cd6db2a4fdc0a9ccff9b66):
process the `personname` children directly and add an ordinary space after
`firstname`, `givenname`, `surname` and `honorific` when a following sibling
element exists. `othername` was added to this upstream rule in
[0b2b1ff](https://github.com/transpect/hub2html/commit/0b2b1ff7e199562f0995b9764d21d58d2cec64d2).
This fork keeps its metadata-only `othername` scope and its span wrapper for
language, styling and inline markup. No other upstream rendering changes are
imported.

Name spacing does not predict CSS visibility or deduplicate separators. Authored
whitespace, NBSP/narrow NBSP, tabs, breaks and punctuation remain in the
output, alongside upstream's structural spaces. Thus `John` followed by
`, Jr.` yields `John , Jr.`; an authored NBSP can be followed by an additional
ordinary space. Under normal browser whitespace collapsing, empty or hidden
middle components leave a single visible gap. Under `pre`, two structural
spaces can remain, and hidden leading/trailing parts can leave edge spaces.
These are intentional consequences of the upstream rule, rather than inputs
to another visibility calculation.

The browser alone interprets inline styles, named Hub rules, overrides,
external stylesheets and whitespace modes. The browser fixtures check the
resulting layout contract; they do not require a CSS cascade inside XSLT.
The former CSS-dependent spacing expectations have been replaced. There is
no promise of identical visible spacing under every stylesheet or EPUB reader.

The repository's existing tests extract serialized author text with
`itertext()` and inspect individual text/tail nodes. Their spacing expectations
now reflect the upstream rule. The public XProc result port returns XML; its
in-repository passes do not extract author names as strings. External text
consumers are not inventoried here and can observe the changed spaces.
Browser `innerText` and serialized text are separate contracts: hidden text
remains serialized, and normal spaces can collapse when rendered.

Metadata `othername` scope remains direct/grouped authors under `info`,
`biblioentry` or `biblioset`, plus their revision authors. Prose, cooked
bibliographies (including nested metadata), standalone content/endnote
revision histories, titles, languages, abstracts and headings retain their
compatibility controls. Nonvisual index/note markers are rendered by their
existing templates; they do not trigger special name-boundary analysis.
