"""Check XHTML output through hub2html's main template."""

import argparse
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import NotRequired, TypedDict
from xml.sax.saxutils import quoteattr

from saxonche import PySaxonApiError, PySaxonProcessor, PyXsltExecutable

DBK = "http://docbook.org/ns/docbook"
HTML = "http://www.w3.org/1999/xhtml"
CSS = "http://www.w3.org/1996/css"
XML = "http://www.w3.org/XML/1998/namespace"
STRUCTURES = (
    "toc", "acknowledgements", "preface", "chapter", "colophon",
    "appendix", "part", "partintro", "book",
)


class BrowserFixture(TypedDict):
    name: str
    parts: str
    expected: str
    white_space: NotRequired[str]
    use_css_rules: NotRequired[str]
    visible_svg: NotRequired[int]


def hub(content: str, *, language: str | None = "en") -> str:
    language_attribute = "" if language is None else f" xml:lang={quoteattr(language)}"
    return (
        f'<hub xmlns="{DBK}"{language_attribute}>'
        "<info><title>Document metadata</title></info>"
        f"{content}<para>Retained body.</para></hub>"
    )


class TitlePriority(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        catalog = Path(cls.temp.name) / "catalog.xml"
        deps = OPTIONS.xslt_util.resolve().as_uri() + "/"
        catalog.write_text(
            '<catalog xmlns="urn:oasis:names:tc:entity:xmlns:xml:catalog">'
            '<rewriteURI uriStartString="http://transpect.io/xslt-util/" '
            f'rewritePrefix={quoteattr(deps)}/>'
            '<rewriteURI uriStartString="http://www.functx.com/" '
            f'rewritePrefix={quoteattr(deps + "functx/")}/></catalog>',
            encoding="utf-8",
        )
        cls.processor = PySaxonProcessor(license=False)
        cls.addClassCleanup(cls.processor.__exit__, None, None, None)
        cls.processor.set_catalog_files([str(catalog)])
        cls.fixed = cls.compile(OPTIONS.source_root)
        cls.baseline = cls.compile(OPTIONS.baseline_root) if OPTIONS.baseline_root else None

    @classmethod
    def compile(cls, root):
        # Fail on an ambiguous rule instead of accepting Saxon's recovery choice.
        # This changes no match patterns, priorities, or conversion templates.
        return cls.processor.new_xslt30_processor().compile_stylesheet(
            stylesheet_text=(
                '<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="3.0">'
                f'<xsl:import href={quoteattr((root / "xsl/hub2html.xsl").resolve().as_uri())}/>'
                '<xsl:mode name="hub2htm-default" on-multiple-match="fail"/>'
                '</xsl:stylesheet>'
            )
        )

    def convert(
        self,
        content: str,
        executable: PyXsltExecutable | None = None,
        *,
        language: str | None = "en",
    ) -> ET.Element:
        executable = executable if executable is not None else self.fixed
        executable.set_global_context_item(
            xdm_item=self.processor.parse_xml(xml_text=hub(content, language=language))
        )
        return ET.fromstring(executable.call_template_returning_string("main"))

    def test_structural_titles(self):
        # The source contract is h1 for every listed structure, both direct and
        # info/title forms, retaining role, language, inline content and text.
        for structure in STRUCTURES:
            for in_info in (False, True):
                with self.subTest(structure=structure, in_info=in_info):
                    title = (
                        '<title role="Heading" xml:lang="de">Kapitel '
                        '<emphasis xml:lang="de">Überschrift</emphasis></title>'
                    )
                    if in_info:
                        title = f'<info>{title}</info>'
                    output = self.convert(f'<{structure}>{title}</{structure}>')
                    headings = output.findall(f'.//{{{HTML}}}h1')
                    self.assertEqual(len(headings), 1)
                    heading = headings[0]
                    self.assertEqual(''.join(heading.itertext()), 'Kapitel Überschrift')
                    self.assertEqual(heading.get('class'), 'Heading')
                    self.assertEqual(heading.get(f'{{{XML}}}lang'), 'de')
                    self.assertTrue(heading.get('id', '').startswith('hd-'))
                    self.assertEqual(heading.get('title'), 'Kapitel  Überschrift')
                    emphasis = heading.find(f'{{{HTML}}}em')
                    self.assertIsNotNone(emphasis)
                    self.assertEqual(emphasis.get(f'{{{XML}}}lang'), 'de')
                    self.assertEqual(emphasis.text, 'Überschrift')

    def test_empty_titles_still_suppressed(self):
        for structure in STRUCTURES:
            for in_info in (False, True):
                with self.subTest(structure=structure, in_info=in_info):
                    title = '<title> </title>'
                    if in_info:
                        title = f'<info>{title}</info>'
                    output = self.convert(f'<{structure}>{title}</{structure}>')
                    self.assertEqual(output.findall(f'.//{{{HTML}}}h1'), [])
                    self.assertIn('Retained body.', ''.join(output.itertext()))

    def test_metadata_title_still_metadata(self):
        output = self.convert('')
        # Document metadata stays in the head rather than becoming a heading.
        self.assertEqual(output.find(f'{{{HTML}}}head/{{{HTML}}}title').text, 'Document metadata')
        self.assertEqual(output.findall(f'.//{{{HTML}}}h1'), [])
        self.assertIn('Retained body.', ''.join(output.itertext()))

    def test_section_depth_unchanged(self):
        output = self.convert(
            '<section><title>First</title><section><info><title>Second</title></info>'
            '</section></section>'
        )
        self.assertEqual(output.find(f'.//{{{HTML}}}h1').text, 'First')
        self.assertEqual(output.find(f'.//{{{HTML}}}h2').text, 'Second')

    def test_html_root_uses_source_language(self) -> None:
        for language in ("fr-CA", "ja", None):
            with self.subTest(language=language):
                output = self.convert("", language=language)
                self.assertEqual(output.get("lang"), language)
                self.assertNotIn(f"{{{XML}}}lang", output.attrib)

    def test_part_chapter_section_depth_unchanged(self) -> None:
        output = self.convert(
            "<part><title>Part</title><chapter><info><title>Chapter</title></info>"
            "<section><title>First</title><section><info><title>Second</title></info>"
            "</section></section></chapter></part>"
        )
        body = output.find(f"{{{HTML}}}body")
        assert body is not None
        heading_tags = {f"{{{HTML}}}h{level}" for level in range(1, 7)}
        headings = [
            (element.tag.removeprefix(f"{{{HTML}}}"), element.text)
            for element in body.iter()
            if element.tag in heading_tags
        ]
        self.assertEqual(
            headings,
            [("h1", "Part"), ("h1", "Chapter"), ("h1", "First"), ("h2", "Second")],
        )

    def test_unstyled_abstract_keeps_text(self) -> None:
        output = self.convert(
            "<chapter><info><abstract><para>Retained abstract text.</para>"
            "</abstract></info></chapter>"
        )
        paragraphs = output.findall(f"{{{HTML}}}body//{{{HTML}}}p")
        self.assertIn(
            "Retained abstract text.", [paragraph.text for paragraph in paragraphs]
        )

    def test_subtitle_class_normalization(self) -> None:
        output = self.convert(
            '<chapter><info><subtitle role="Sub.Title:Marked">A subtitle</subtitle></info></chapter>'
        )
        subtitle = output.find(f"{{{HTML}}}body//{{{HTML}}}p")
        assert subtitle is not None
        self.assertEqual(subtitle.text, "A subtitle")
        self.assertEqual(subtitle.get("class"), "Sub_Title_Marked")

    def test_author_othername_spacing(self) -> None:
        output = self.convert(
            "<chapter><info><authorgroup>"
            "<author><personname><othername>Ada</othername><surname>Lovelace</surname></personname></author>"
            "<author><personname><firstname>Ada</firstname><othername>M.</othername>"
            "<surname>Lovelace</surname></personname></author>"
            "<author><personname><firstname>Ada</firstname><surname>Lovelace</surname>"
            "<othername>Byron</othername></personname></author>"
            "</authorgroup></info></chapter>"
        )
        authors = output.findall(f'.//{{{HTML}}}p[@class="author"]')
        self.assertEqual(
            ["".join(author.itertext()) for author in authors],
            ["Ada Lovelace", "Ada M. Lovelace", "Ada Lovelace Byron"],
        )
        self.assertEqual(output.findall(f".//{{{DBK}}}othername"), [])

    def test_author_name_empty_and_styled_edge_parts(self) -> None:
        executable = self.fixed.clone()
        executable.set_property("!indent", "no")
        cases = (
            (
                "<othername/><firstname>Ada</firstname><surname>Lovelace</surname>",
                "Ada Lovelace",
            ),
            (
                "<firstname>Ada</firstname><othername/><surname>Lovelace</surname>",
                "Ada Lovelace",
            ),
            (
                "<firstname>Ada</firstname><surname>Lovelace</surname><othername/>",
                "Ada Lovelace",
            ),
            (
                '<othername css:display="none"> M. </othername><surname>Lovelace</surname>',
                "Lovelace",
            ),
            (
                '<firstname>Ada</firstname><othername css:display="none"> M. </othername>',
                "Ada",
            ),
            (
                "<honorific>Dr.</honorific><givenname>Ada</givenname><othername>M.</othername><surname>Lovelace</surname>",
                "Dr. Ada M. Lovelace",
            ),
        )
        for source, expected in cases:
            with self.subTest(source=source):
                output = self.convert(
                    f'<chapter xmlns:css="{CSS}"><info><author><personname>{source}'
                    "</personname></author></info></chapter>",
                    executable,
                )
                author = output.find(f'.//{{{HTML}}}p[@class="author"]')
                assert author is not None
                for hidden in author.findall('.//*[@style="display: none"]'):
                    hidden.text = None
                    del hidden[:]
                self.assertEqual("".join(author.itertext()), expected)

    def test_revision_author_uses_metadata_spacing(self) -> None:
        output = self.convert(
            "<chapter><info><revhistory><revision><date>2026-01-01</date>"
            "<author><personname><firstname>Ada</firstname><othername>M.</othername>"
            "<surname>Lovelace</surname></personname></author>"
            "</revision></revhistory></info></chapter>"
        )
        author = output.find(f'.//{{{DBK}}}revision/{{{HTML}}}p[@class="author"]')
        assert author is not None
        self.assertEqual("".join(author.itertext()), "Ada M. Lovelace")

    def test_author_name_preserves_explicit_separators(self) -> None:
        executable = self.fixed.clone()
        executable.set_property("!indent", "no")
        comment = (
            '<phrase role="hub:foreign">'
            '<tr:comment xmlns:tr="http://transpect.io">{}</tr:comment></phrase>'
        )
        cases = [
            (
                "<othername>M.&#xA0;</othername><surname>Lovelace</surname>",
                "M.\u00a0Lovelace",
            ),
            (
                "<othername>M.</othername><surname>&#xA0;Lovelace</surname>",
                "M.\u00a0Lovelace",
            ),
            (
                '<firstname><emphasis role="Name">Ada</emphasis>&#xA0;</firstname>'
                "<surname>Lovelace</surname>",
                "Ada\u00a0Lovelace",
            ),
            (
                "<firstname>Ada</firstname>"
                '<surname>&#xA0;<emphasis role="Name">Lovelace</emphasis></surname>',
                "Ada\u00a0Lovelace",
            ),
            ("<othername>M.</othername> <surname>Lovelace</surname>", "M. Lovelace"),
            (
                "<firstname>Ada&#x202F;</firstname><othername>M.</othername>",
                "Ada\u202fM.",
            ),
            ("<othername>John</othername><lineage>, Jr.</lineage>", "John, Jr."),
            (
                "<surname>Lovelace</surname><firstname>, Ada</firstname>",
                "Lovelace , Ada",
            ),
            (
                "<firstname>Ada&#xA0;</firstname><othername/>"
                "<surname>Lovelace</surname>",
                "Ada\u00a0Lovelace",
            ),
            (
                "<firstname>Ada</firstname><othername/><surname>Lovelace</surname>",
                "Ada Lovelace",
            ),
            (
                "<othername>John</othername><surname/><lineage>, Jr.</lineage>",
                "John, Jr.",
            ),
            (
                f"<firstname>Ada{comment.format('note ')}</firstname>"
                "<surname>Lovelace</surname>",
                "Ada Lovelace",
            ),
            (
                "<firstname>Ada</firstname>"
                f"<surname>{comment.format(' note')}Lovelace</surname>",
                "Ada Lovelace",
            ),
        ]
        for marker in (
            "<indexterm><primary>Lovelace</primary></indexterm>",
            "<footnote><para>Former pen name.</para></footnote>",
            comment.format("note"),
        ):
            cases.extend(
                (
                    (
                        f"<othername>M.&#xA0;{marker}</othername>"
                        "<surname>Lovelace</surname>",
                        "M.\u00a0Lovelace",
                    ),
                    (
                        "<othername>M.</othername>"
                        f"<surname>{marker}&#xA0;Lovelace</surname>",
                        "M.\u00a0Lovelace",
                    ),
                    (
                        f"<othername>John</othername><lineage>{marker}, Jr.</lineage>",
                        "John, Jr.",
                    ),
                )
            )
        for source, expected in cases:
            with self.subTest(source=source):
                output = self.convert(
                    f"<chapter><info><author><personname>{source}"
                    "</personname></author></info></chapter>",
                    executable,
                )
                authors = output.findall(f'.//{{{HTML}}}p[@class="author"]')
                self.assertEqual(
                    ["".join(author.itertext()) for author in authors], [expected]
                )

    def test_author_name_spacing_ignores_hidden_content(self) -> None:
        executable = self.fixed.clone()
        executable.set_property("!indent", "no")
        hidden_phrase = '<phrase css:display="none"> note </phrase>'
        cases = (
            ('<othername css:display="none"> M. </othername>', 1, "Ada Lovelace"),
            ('<othername css:display="inline"> M. </othername>', 0, "Ada M. Lovelace"),
            (f"<othername>{hidden_phrase}</othername>", 1, "Ada Lovelace"),
            (
                '<othername><emphasis css:display="none"> M. </emphasis></othername>',
                1,
                "Ada Lovelace",
            ),
            (
                '<othername><emphasis css:display="inline"> M. </emphasis></othername>',
                0,
                "Ada M. Lovelace",
            ),
            ('<lineage css:display="none"> , Jr. </lineage>', 1, "Ada Lovelace"),
            (
                '<othername><phrase css:display="none"> </phrase></othername>',
                0,
                "Ada Lovelace",
            ),
        )
        for middle, hidden_count, expected in cases:
            with self.subTest(middle=middle):
                output = self.convert(
                    f'<chapter xmlns:css="{CSS}"><info><author><personname>'
                    f"<firstname>Ada</firstname>{middle}<surname>Lovelace</surname>"
                    "</personname></author></info></chapter>",
                    executable,
                )
                author = output.find(f'.//{{{HTML}}}p[@class="author"]')
                assert author is not None
                hidden_elements = author.findall('.//*[@style="display: none"]')
                self.assertEqual(len(hidden_elements), hidden_count)
                for hidden in hidden_elements:
                    hidden.text = None
                    del hidden[:]
                self.assertEqual("".join(author.itertext()), expected)

    def test_author_name_spacing_around_inline_glyphs(self) -> None:
        executable = self.fixed.clone()
        executable.set_property("!indent", "no")
        svg = "http://www.w3.org/2000/svg"
        glyph = (
            "<inlinemediaobject><imageobject><imagedata>"
            f'<svg xmlns="{svg}" viewBox="0 0 3 4"><path d="M0 0h3v4H0z"/></svg>'
            "</imagedata></imageobject></inlinemediaobject>"
        )
        output = self.convert(
            "<chapter><info><author><personname><honorific>Dr.</honorific>"
            f"<firstname>{glyph}</firstname><surname>Lovelace</surname>"
            f"<othername>{glyph}</othername><lineage>, Jr.</lineage>"
            "</personname></author></info></chapter>",
            executable,
        )
        author = output.find(f'.//{{{HTML}}}p[@class="author"]')
        assert author is not None
        self.assertEqual(author.text, "Dr. ")
        self.assertEqual(
            [element.tail for element in author.findall(f"{{{svg}}}svg")],
            [" Lovelace ", None],
        )
        self.assertEqual(author.findtext(f"{{{DBK}}}lineage"), ", Jr.")

    def test_author_name_spacing_ignores_hidden_svg(self) -> None:
        executable = self.fixed.clone()
        executable.set_property("!indent", "no")
        svg = "http://www.w3.org/2000/svg"
        glyph = (
            "<inlinemediaobject><imageobject><imagedata>"
            f'<svg xmlns="{svg}" display="none"><path d="M0 0h3v4H0z"/></svg>'
            "</imagedata></imageobject></inlinemediaobject>"
        )
        output = self.convert(
            "<chapter><info><author><personname>"
            f"<firstname>Ada&#xA0;{glyph}</firstname><surname>Lovelace</surname>"
            f"<lineage>{glyph}, Jr.</lineage></personname></author></info></chapter>",
            executable,
        )
        author = output.find(f'.//{{{HTML}}}p[@class="author"]')
        assert author is not None
        self.assertEqual(len(author.findall(f'.//{{{svg}}}svg[@display="none"]')), 2)
        self.assertEqual("".join(author.itertext()), "Ada\u00a0Lovelace, Jr.")

    def test_author_name_spacing_uses_inline_image_reference(self) -> None:
        executable = self.fixed.clone()
        executable.set_property("!indent", "no")
        for overwrite, prefix in (("no", ""), ("yes", "./")):
            executable.set_parameter(
                "overwrite-image-paths", self.processor.make_string_value(overwrite)
            )
            for fileref, expected in (
                ("", "M.\u00a0Lovelace, Jr."),
                ("glyph.png", "M.\u00a0 Lovelace , Jr."),
            ):
                with self.subTest(overwrite=overwrite, fileref=fileref):
                    media = (
                        "<inlinemediaobject><imageobject>"
                        f'<imagedata fileref="{fileref}"/>'
                        "</imageobject></inlinemediaobject>"
                    )
                    output = self.convert(
                        "<chapter><info><author><personname>"
                        f"<othername>M.&#xA0;{media}</othername>"
                        f"<surname>Lovelace</surname><lineage>{media}, Jr.</lineage>"
                        "</personname></author></info></chapter>",
                        executable,
                    )
                    author = output.find(f'.//{{{HTML}}}p[@class="author"]')
                    assert author is not None
                    images = author.findall(f".//{{{HTML}}}img")
                    self.assertEqual(
                        [image.get("src") for image in images], [prefix + fileref] * 2
                    )
                    self.assertEqual("".join(author.itertext()), expected)

    def test_author_name_preserves_tabs_and_breaks(self) -> None:
        executable = self.fixed.clone()
        executable.set_property("!indent", "no")
        for marker, tag, text in (("<tab/>", "span", "\t"), ("<br/>", "br", None)):
            for left, right in ((marker, ""), ("", marker)):
                with self.subTest(marker=marker, before_boundary=bool(left)):
                    output = self.convert(
                        "<chapter><info><author><personname>"
                        f"<othername>M.{left}</othername>"
                        f"<surname>{right}Lovelace</surname>"
                        "</personname></author></info></chapter>",
                        executable,
                    )
                    author = output.find(f'.//{{{HTML}}}p[@class="author"]')
                    assert author is not None
                    separator = author.find(f"{{{HTML}}}{tag}")
                    assert separator is not None
                    self.assertEqual(
                        (author.text, separator.text, separator.tail),
                        ("M.", text, "Lovelace"),
                    )

    def test_prose_names_keep_existing_spacing(self) -> None:
        output = self.convert(
            "<para><personname><othername>d\u2019</othername>"
            "<surname>Artagnan</surname></personname></para>"
            "<para><personname><firstname>Ada&#xA0;</firstname>"
            "<surname>Lovelace</surname></personname></para>"
            "<para><author><personname><othername>d\u2019</othername>"
            "<surname>Artagnan</surname></personname></author></para>"
            "<para><author><personname><firstname>Ada&#xA0;</firstname>"
            "<surname>Lovelace</surname></personname></author></para>"
        )
        paragraphs = output.findall(f"{{{HTML}}}body/{{{HTML}}}p")
        expected = ["d\u2019Artagnan", "Ada\u00a0 Lovelace"]
        self.assertEqual(
            ["".join(paragraph.itertext()) for paragraph in paragraphs[:2]], expected
        )
        inline = output.findall(
            f'{{{HTML}}}body/{{{HTML}}}p/{{{HTML}}}p[@class="author"]'
        )
        self.assertEqual(["".join(author.itertext()) for author in inline], expected)

    def test_author_othername_keeps_inline_formatting(self) -> None:
        output = self.convert(
            "<chapter><info><author><personname><firstname>Ada</firstname>"
            f'<othername xmlns:css="{CSS}" xml:lang="ja" role="Name:Alternate" '
            'css:color="red" css:font-style="italic">花子</othername>'
            "<surname>Yamada</surname></personname></author></info></chapter>"
        )
        author = output.find(f'.//{{{HTML}}}p[@class="author"]')
        self.assertEqual("".join(author.itertext()), "Ada 花子 Yamada")
        alternate = author.find(f"{{{HTML}}}span")
        self.assertIsNotNone(alternate)
        self.assertEqual(alternate.get(f"{{{XML}}}lang"), "ja")
        self.assertEqual(alternate.get("class"), "Name_Alternate")
        self.assertEqual(alternate.get("style"), "color: red")
        self.assertEqual(alternate.findtext(f"{{{HTML}}}i"), "花子")
        self.assertEqual(alternate.tail, " Yamada")

    def test_bibliomixed_othername_preserves_punctuation(self) -> None:
        output = self.convert(
            "<bibliography><bibliomixed><othername>Byron</othername>, "
            "<citetitle>Memoirs</citetitle></bibliomixed></bibliography>"
        )
        entry = output.find(f'.//{{{HTML}}}div[@class="bibliography"]/{{{HTML}}}p')
        self.assertEqual("".join(entry.itertext()), "Byron, Memoirs")

    def test_endnote_bibliography_keeps_author_spacing(self) -> None:
        output = self.convert(
            "<para>Reference<footnote><bibliolist><biblioentry>"
            "<author><personname><firstname>Ada</firstname><surname>Lovelace</surname>"
            "</personname></author></biblioentry></bibliolist></footnote></para>"
        )
        author = output.find(
            f'.//{{{HTML}}}dd[@class="endnote-text"]//{{{HTML}}}p[@class="author"]'
        )
        assert author is not None
        self.assertEqual("".join(author.itertext()), "Ada Lovelace")

    def test_cooked_bibliography_preserves_nested_name_punctuation(self) -> None:
        executable = self.fixed.clone()
        executable.set_property("!indent", "no")
        author = (
            "<biblioset><author><personname><othername>d\u2019</othername>"
            "<surname>Artagnan</surname></personname></author></biblioset>"
        )
        cases = (
            (f"<bibliomixed>{author}, Memoirs</bibliomixed>", f"{{{HTML}}}p"),
            (
                f"<biblioentry><bibliomset>{author}, Memoirs</bibliomset>"
                "</biblioentry>",
                f"{{{DBK}}}biblioentry/{{{DBK}}}bibliomset",
            ),
        )
        for source, path in cases:
            with self.subTest(source=source):
                output = self.convert(
                    f"<bibliography>{source}</bibliography>", executable
                )
                entry = output.find(f'.//{{{HTML}}}div[@class="bibliography"]/{path}')
                assert entry is not None
                self.assertEqual(
                    "".join(entry.itertext()).strip(), "d\u2019Artagnan, Memoirs"
                )

    def test_author_name_spacing_with_named_display_rule(self) -> None:
        # Hub emits named rules as simple class selectors. Hidden padding cannot
        # supply the only separator between the remaining visible name parts.
        executable = self.fixed.clone()
        executable.set_property("!indent", "no")
        for enabled in ("yes", "no"):
            executable.set_parameter(
                "use-css-rules", self.processor.make_string_value(enabled)
            )
            for source, hidden_text, visible_text in (
                (
                    '<othername role="hidden-name"> M. </othername>',
                    "Ada Lovelace",
                    "Ada M. Lovelace",
                ),
                (
                    '<othername><emphasis role="hidden-name"> M. </emphasis></othername>',
                    "Ada Lovelace",
                    "Ada M. Lovelace",
                ),
                (
                    '<othername role="hidden-name" css:display="inline"> M. </othername>',
                    "Ada M. Lovelace",
                    "Ada M. Lovelace",
                ),
            ):
                with self.subTest(enabled=enabled, source=source):
                    output = self.convert(
                        f'<info xmlns:css="{CSS}"><css:rules>'
                        '<css:rule name="hidden-name" css:display="none"/>'
                        "</css:rules></info>"
                        f'<chapter xmlns:css="{CSS}"><info><author><personname>'
                        f"<firstname>Ada</firstname>{source}<surname>Lovelace</surname>"
                        "</personname></author></info></chapter>",
                        executable,
                    )
                    styles = output.findall(f"{{{HTML}}}head/{{{HTML}}}style")
                    self.assertEqual(len(styles), 2 if enabled == "yes" else 1)
                    if enabled == "yes":
                        self.assertIn(".hidden-name{", styles[0].text)
                        self.assertIn("display:none", styles[0].text)
                    author = output.find(f'.//{{{HTML}}}p[@class="author"]')
                    assert author is not None
                    for element in author.findall('.//*[@class="hidden-name"]'):
                        if (
                            enabled == "yes"
                            and element.get("style") != "display: inline"
                        ):
                            element.text = None
                            del element[:]
                    self.assertEqual(
                        "".join(author.itertext()),
                        hidden_text if enabled == "yes" else visible_text,
                    )

    def test_author_name_spacing_respects_svg_display_override(self) -> None:
        executable = self.fixed.clone()
        executable.set_property("!indent", "no")
        for style, visible in (
            ("display:inline", True),
            ("display:none; display:inline", True),
            ("display:inline; display:none", False),
            ("display:none !important; display:inline", False),
        ):
            with self.subTest(style=style):
                glyph = (
                    "<inlinemediaobject><imageobject><imagedata>"
                    '<svg xmlns="http://www.w3.org/2000/svg" display="none" '
                    f'style="{style}"><path d="M0 0h3v4H0z"/></svg>'
                    "</imagedata></imageobject></inlinemediaobject>"
                )
                output = self.convert(
                    "<chapter><info><author><personname>"
                    f"<firstname>Ada&#xA0;{glyph}</firstname><surname>Lovelace</surname>"
                    "</personname></author></info></chapter>",
                    executable,
                )
                author = output.find(f'.//{{{HTML}}}p[@class="author"]')
                assert author is not None
                self.assertEqual(
                    "".join(author.itertext()),
                    "Ada\u00a0 Lovelace" if visible else "Ada\u00a0Lovelace",
                )

    def test_pristine_baseline_negative_control(self):
        if self.baseline is None:
            self.skipTest('pass --baseline-root to reproduce the pristine ambiguity')
        with self.assertRaisesRegex(PySaxonApiError, 'XTDE0540'):
            self.convert('<chapter><info><title>Chapter heading</title></info></chapter>', self.baseline)
        # Establish that the baseline compiles and converts unrelated cases.
        output = self.convert('', self.baseline)
        self.assertEqual(output.find(f'{{{HTML}}}head/{{{HTML}}}title').text, 'Document metadata')

    def test_browser_spacing_fixtures(self) -> None:
        """Generate real converter output; browser_spacing.mjs checks its layout."""
        # This is a checked-in test table, not a public input interface.
        fixtures: list[BrowserFixture] = json.loads(
            Path(__file__).with_name("browser_spacing.json").read_text(encoding="utf-8")
        )
        manifest: list[dict[str, object]] = []
        for fixture in fixtures:
            with self.subTest(name=fixture["name"]):
                executable = self.fixed.clone()
                executable.set_property("!indent", "no")
                executable.set_parameter(
                    "use-css-rules",
                    self.processor.make_string_value(
                        fixture.get("use_css_rules", "yes")
                    ),
                )
                output = self.convert(
                    f'<info xmlns:css="{CSS}"><css:rules>'
                    '<css:rule name="hidden-name" css:display="none"/>'
                    "</css:rules></info>"
                    f'<chapter xmlns:css="{CSS}"><info><author><personname>'
                    f"{fixture['parts']}</personname></author></info></chapter>",
                    executable,
                )
                authors = output.findall(f'.//{{{HTML}}}p[@class="author"]')
                self.assertEqual(len(authors), 1)
                # Apply the whitespace environment after conversion, as an EPUB
                # reader or consuming stylesheet would. Do not normalize text.
                authors[0].set(
                    "style", f"white-space: {fixture.get('white_space', 'normal')}"
                )
                if OPTIONS.browser_output:
                    OPTIONS.browser_output.mkdir(parents=True, exist_ok=True)
                    path = OPTIONS.browser_output / f"{fixture['name']}.xhtml"
                    ET.ElementTree(output).write(
                        path, encoding="utf-8", xml_declaration=True
                    )
                    manifest.append({**fixture, "url": path.resolve().as_uri()})
        if OPTIONS.browser_output:
            (OPTIONS.browser_output / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xslt-util", type=Path, required=True)
    parser.add_argument(
        "--source-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--baseline-root", type=Path)
    parser.add_argument(
        "--browser-output", type=Path, help="export fixtures for browser_spacing.mjs"
    )
    OPTIONS = parser.parse_args()
    unittest.main(argv=[__file__], verbosity=2)
