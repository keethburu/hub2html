"""Execute the structural-title contract through hub2html's main template."""

import argparse
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from xml.sax.saxutils import quoteattr

from saxonche import PySaxonApiError, PySaxonProcessor


DBK = "http://docbook.org/ns/docbook"
HTML = "http://www.w3.org/1999/xhtml"
XML = "http://www.w3.org/XML/1998/namespace"
STRUCTURES = (
    "toc", "acknowledgements", "preface", "chapter", "colophon",
    "appendix", "part", "partintro", "book",
)


def hub(content):
    return (
        f'<hub xmlns="{DBK}" xml:lang="en">'
        '<info><title>Document metadata</title></info>'
        f'{content}<para>Retained body.</para></hub>'
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

    def convert(self, content, executable=None):
        executable = executable if executable is not None else self.fixed
        executable.set_global_context_item(xdm_item=self.processor.parse_xml(xml_text=hub(content)))
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

    def test_pristine_baseline_negative_control(self):
        if self.baseline is None:
            self.skipTest('pass --baseline-root to reproduce the pristine ambiguity')
        with self.assertRaisesRegex(PySaxonApiError, 'XTDE0540'):
            self.convert('<chapter><info><title>Chapter heading</title></info></chapter>', self.baseline)
        # Establish that the baseline compiles and converts unrelated cases.
        output = self.convert('', self.baseline)
        self.assertEqual(output.find(f'{{{HTML}}}head/{{{HTML}}}title').text, 'Document metadata')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--xslt-util', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--baseline-root', type=Path)
    OPTIONS = parser.parse_args()
    unittest.main(argv=[__file__], verbosity=2)
