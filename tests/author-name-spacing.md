# Author-name spacing: contract and simplification decision

The observable goal in [issue #8](https://github.com/keethburu/hub2html/issues/8)
is browser-visible spacing. A visible structured metadata name should retain
its authored separators and receive a space at an otherwise unseparated name
boundary. Empty or supported hidden components must not join adjacent visible
words. A comma-led lineage such as `, Jr.` stays attached to its preceding
name. Other punctuation keeps the existing behavior: a surname followed by
`, Ada` still yields `Lovelace , Ada`.

The scope and transformation assertions from
[the preceding change](https://github.com/keethburu/hub2html/pull/7) are retained:
metadata authors directly or in an `authorgroup` under `info`, `biblioentry`
or `biblioset`, and revision authors in those metadata containers. Running
prose, `bibliomixed`/`bibliomset` (including nested metadata), and standalone
content/endnote revision histories retain their existing behavior. Inline
markup, language attributes, graphics, title/subtitle, abstract and heading
compatibility checks remain transformation-level assertions.

## Serialized-text consumers

The repository's transformation tests consume exact author text through
ElementTree `itertext()`, sometimes removing known hidden nodes first. They
also check individual text/tail nodes, inline markup and attributes. These
are concrete existing serialized-text consumers, and remain unchanged.

The public XProc step `xpl/hub2html.xpl` returns an XML result after its CSS,
list, table, reference and namespace passes. Its in-repository passes do not
extract author text as a string. The README describes downstream HTML/EPUB
workflows, but this checkout contains no downstream application text extractor
or consumer inventory. External consumers relying on exact text nodes cannot
be ruled out. No production stylesheet or serialized output changes in this
follow-up, so those consumers keep the existing output.

Browser text and serialized text are distinct contracts: hidden text is still
present in XHTML; ordinary whitespace can collapse in a browser; NBSP and
narrow NBSP do not collapse with an adjacent ordinary space. The existing
serialization assertions protect compatibility, while the browser assertions
test the intended visible symptom directly.

## Bounded counterfactuals

Two small alternatives were compared with the current converter using the
same 47 initial browser fixtures. Both retained the metadata scope predicate
and the existing component templates. Expected strings came from authored
separators and the existing spacing contract, independently of each candidate.

| Alternative | Trigger and conditions | Browser-visible result | Failing cases |
| --- | --- | --- | --- |
| Remove CSS visibility filtering from rendered boundary detection | A middle `othername` or its descendant contains ` M. ` and is hidden by inline CSS or a named Hub rule | `AdaLovelace`: the hidden padding suppressed both separators | 12/47, also including hidden SVG edges after NBSP |
| Emit a space after each structural name component with a following element, except immediately before comma-led lineage | A padded middle component is hidden under `white-space: pre`, `pre-wrap` or `break-spaces` | `Ada  Lovelace`: both generated spaces remain | 20/47 across whitespace, NBSP, tabs, lineage and hidden SVG cases |

The structural alternative succeeds for hidden padded names under normal
whitespace collapsing. This is the useful positive control. It nevertheless
adds an ordinary space after an authored NBSP/narrow NBSP even under `normal`,
and produces `John , Jr.` when an empty or hidden component intervenes before
the lineage. Authored tabs acquire a second separator under `pre`. Conversely,
the CSS-blind alternative preserves authored separators but cannot distinguish
the padded text that the browser will hide. These are visible changes, not
merely differences in text-node arrangement.

More source-side exceptions could fix individual examples, but deciding
whether a styled descendant contributes the name boundary returns to the
visibility problem. CSS margins or generated content would also change text
selection/copying and require handling those same conditional boundaries.
Neither tested simplification preserves the supported contract. In accordance
with the issue's fallback, the existing implementation is retained, without
adding CSS parsing or widening its claimed support.

## Browser coverage and limits

`browser_spacing.json` contains the repeatable cases. The transformation suite
exports complete converted XHTML through `--browser-output`; the Chrome runner
asserts rendered `innerText` and visible SVG rectangles. No Python imitation
of CSS hiding or whitespace collapsing supplies the browser oracle. CI runs
both the full transformation suite and these browser assertions.

The cases cover first/middle/final components, empty and hidden parts,
hidden descendants, named rules, disabled rules, inline overrides, ordered
SVG declarations and `!important`, NBSP/narrow NBSP, tabs, `<br>`, punctuation,
inline formatting and language. Whitespace environments include `normal`,
`nowrap`, `pre`, `pre-wrap`, `pre-line` and `break-spaces`. Authored padding is
preserved, so it intentionally remains multiple spaces in preserving modes.
Leading/trailing hidden components are also checked under `normal` and `pre`.

Intervening index terms become empty anchors/comments. The note fixtures
produce empty reference links because they have no authored identifier; their
note text remains in the endnotes. Comments and these nonvisual references
must not displace an NBSP or add a name separator. Notes with authored visible
identifiers have their own reference rendering and are not asserted to be
invisible.

The retained boundary analysis supports the emitted inline `display`
declarations, simple named Hub classes with `use-css-rules=yes`, and the
existing SVG/image handling. It is still not a general CSS cascade: external
stylesheets, arbitrary selectors, inherited/custom-property effects,
`visibility`, generated content and every possible layout override are not
resolved. The browser suite checks Chromium XHTML rendering at its test
viewport; it does not claim exhaustive browser, line-wrapping or EPUB-reader
coverage. No new support for these cases is implied by retaining the code.
