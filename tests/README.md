# Hub2HTML regression tests

## Local setup

Check out `transpect/xslt-util` at the revision pinned in the
[CI workflow](../.github/workflows/title-priority.yml#L22-L27). Use a Python
environment to install the pinned SaxonC-HE dependency and run the suite.
Run these commands from the repository root.

```sh
python -m pip install -r tests/requirements.txt
python tests/title_priority.py --xslt-util /path/to/xslt-util
```

The suite runs the converter's `main` template and resolves stylesheet
dependencies through a local XML catalog.

## What the suite covers

When both structural and metadata title rules match, structural titles take
precedence. The root language test checks that the converter copies the source
root's `xml:lang` value to `lang` on the XHTML `<html>` element. If the source
root has no `xml:lang`, the XHTML root has no `lang` attribute.

The [author-name spacing contract](../README.md#author-names) is covered by
cases for first, middle, and final `othername` components, authored whitespace,
lineage punctuation, empty parts, inline formatting and language, graphics,
hidden content, and metadata revision authors. Compatibility cases cover prose
names and cooked bibliography punctuation.

The hidden-name cases check the inline declarations and simple named Hub
classes emitted by the converter, including disabled Hub rules and inline
`display` overrides. SVG display overrides are covered independently.

The `othername` addition derives from the corresponding change in
[the upstream commit](https://github.com/transpect/hub2html/commit/0b2b1ff7e199562f0995b9764d21d58d2cec64d2).
The fork retains its existing title, language, abstract, heading-depth, and
subtitle behavior.

## CI negative control

To reproduce the ambiguous title match (`XTDE0540`), export the pristine
upstream revision used by the
[CI negative control](../.github/workflows/title-priority.yml#L32-L38) and
add `--baseline-root /path/to/export` to the test command.

## Reproduce the full-upstream regressions

Use the pinned xslt-util checkout from [local setup](#local-setup).
From the maintained fork, run its tests against a temporary
checkout of the pinned full upstream revision.

```sh
upstream=$(mktemp -d)
git -C "$upstream" init -q
git -C "$upstream" fetch --depth=1 https://github.com/transpect/hub2html.git 5417ccf4a859386866cd6db2a4fdc0a9ccff9b66
git -C "$upstream" checkout --detach FETCH_HEAD
uv run --no-project --python 3.13.18 --with-requirements tests/requirements.txt \
  python tests/title_priority.py --xslt-util /path/to/xslt-util --source-root "$upstream"
```

On that pinned source, the root language test passes and the compatibility
checks show four differences.

- `test_part_chapter_section_depth_unchanged` gets `h1 h1 h4 h5` instead of
  `h1 h1 h1 h2` for a part, chapter, and two sections inside a Hub.
- `test_unstyled_abstract_keeps_text` fails because the abstract becomes an
  empty `div` and loses its paragraph.
- `test_structural_titles` fails because headings and inline emphasis use
  plain `lang` in place of `xml:lang`.
- `test_subtitle_class_normalization` gets `Sub.Title_Marked` instead of
  `Sub_Title_Marked`.
