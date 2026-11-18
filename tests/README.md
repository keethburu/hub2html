# Hub2HTML regression tests

## Local setup

Install the pinned SaxonC-HE dependency in a Python environment and check out
`transpect/xslt-util` at `5d78dff50bf197e7973c5dcf92b921e08c4ae6cc`.
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

## CI negative control

The [CI workflow](../.github/workflows/title-priority.yml) exports pristine
upstream revision `ee25fb16ce4819ef6ab880889e9761d8e5768ef3` and adds
`--baseline-root /path/to/export` to the test command to reproduce `XTDE0540`
as a negative control.

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
