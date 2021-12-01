#!/usr/bin/env python3

'''Unit tests for Python scripts'''
import unittest

from pathlib import Path
from xml.dom.minidom import parseString
from avalon import BibRefToTextConverter, CsvColumnCounts, Object, ObjectToCsvConverter, XmlUtils


class TestObject(unittest.TestCase):
    def test_creation_from_umdm(self):
        umdm_file = 'src/test/resources/scripts/avalon/umd_55387_umdm.xml'
        self.obj = Object()
        self.obj.title = 'Test Object 1'
        self.obj.other_identifier.append(("local", 'umd:55387'))
        self.obj.handle = 'hdl:1903.1/5368'
        self.obj.process_umdm(Path(umdm_file))

        self.assertEqual(['North America', 'United States of America', 'Maryland', 'College Park'],
                         self.obj.geographic_subject)


class TestObjectToCsvConverter(unittest.TestCase):
    def setUp(self):
        umdm_file = 'src/test/resources/scripts/avalon/umd_55387_umdm.xml'
        self.obj = Object()
        self.obj.title = 'Test Object 1'
        self.obj.other_identifier.append(("local", 'umd:55387'))
        self.obj.handle = 'hdl:1903.1/5368'
        self.obj.process_umdm(Path(umdm_file))

        self.column_counts = CsvColumnCounts([self.obj])
        self.converter = ObjectToCsvConverter(self.column_counts)

    def test_headers(self):
        expected_headers = \
            ['Bibliographic ID Label', 'Bibliographic ID'] \
            + ['Other Identifier Type', 'Other Identifier'] * self.column_counts.max_other_identifier \
            + ['Handle'] \
            + ['Title'] \
            + ['Creator'] * self.column_counts.max_creator \
            + ['Contributor'] * self.column_counts.max_contributor \
            + ['Genre'] * self.column_counts.max_genre \
            + ['Publisher'] * self.column_counts.max_publisher \
            + ['Date Created', 'Date Issued', 'Abstract'] \
            + ['Language'] * self.column_counts.max_language \
            + ['Physical Description'] \
            + ['Related Item Label', 'Related Item URL'] * self.column_counts.max_related_item \
            + ['Topical Subject'] * self.column_counts.max_topical_subject \
            + ['Geographic Subject'] * self.column_counts.max_geographic_subject \
            + ['Temporal Subject'] * self.column_counts.max_temporal_subject \
            + ['Terms of Use', 'Table of Contents'] \
            + ['Note Type', 'Note'] * self.column_counts.max_note \
            + ['Publish', 'Hidden'] \
            + ['File', 'Label'] * self.column_counts.max_file

        self.assertEqual(expected_headers, self.converter.headers)

    def test_convert(self):
        row = self.converter.convert(self.obj)
        title_index = self.converter.headers.index('Title')
        handle_index = self.converter.headers.index('Handle')
        geographic_subject_index = self.converter.headers.index('Geographic Subject')

        self.assertEqual('Test Object 1', row[title_index])
        self.assertIn('hdl:1903.1/5368', row[handle_index])
        self.assertIn('North America', row[geographic_subject_index])


class TestCsvColumnCounts(unittest.TestCase):
    def test_counts_from_single_object(self):
        umdm_file = 'src/test/resources/scripts/avalon/umd_55387_umdm.xml'
        obj = Object()
        obj.process_umdm(Path(umdm_file))
        csv_column_counts = CsvColumnCounts([obj])

        self.assertEqual(1, csv_column_counts.max_other_identifier)
        self.assertEqual(4, csv_column_counts.max_creator)
        self.assertEqual(1, csv_column_counts.max_contributor)
        self.assertEqual(1, csv_column_counts.max_publisher)
        self.assertEqual(1, csv_column_counts.max_genre)
        self.assertEqual(1, csv_column_counts.max_related_item)
        self.assertEqual(4, csv_column_counts.max_geographic_subject)
        self.assertEqual(10, csv_column_counts.max_topical_subject)
        self.assertEqual(1, csv_column_counts.max_temporal_subject)
        self.assertEqual(1, csv_column_counts.max_note)
        self.assertEqual(1, csv_column_counts.max_file)
        self.assertEqual(1, csv_column_counts.max_language)


class TestBibRefToTextConverter(unittest.TestCase):
    '''Test cases for the 'bib_ref_to_note_text' method in avalon.py'''

    @staticmethod
    def to_element(xml: str):
        '''Converts the given string into minidom Element'''
        doc = parseString(str(xml))
        XmlUtils.collapse_whitespace_nodes(doc)
        doc_element = doc.documentElement
        return doc_element

    def test_bib_ref_with_no_children(self):
        xml = '<bibRef />'
        bib_ref = self.to_element(xml)
        self.assertEqual('', BibRefToTextConverter.as_text(bib_ref))

        xml = '<bibRef></bibRef>'
        bib_ref = self.to_element(xml)
        self.assertEqual('', BibRefToTextConverter.as_text(bib_ref))

    def test_bib_ref_with_only_title(self):
        xml = '<bibRef>\n        <title type="main">Madrigal Singers</title>\n      </bibRef>'
        bib_ref = self.to_element(xml)
        self.assertEqual('Madrigal Singers', BibRefToTextConverter.as_text(bib_ref))

    def test_bib_ref_with_title_and_accession(self):
        xml = '<bibRef><title type="main">University of Maryland\xa0Football\xa0Heritage\xa0Film\xa0Collection</title>\n<bibScope type="accession">2011-166</bibScope></bibRef>'
        bib_ref = self.to_element(xml)
        self.assertEqual('University of Maryland\xa0Football\xa0Heritage\xa0Film\xa0Collection, Accession 2011-166', BibRefToTextConverter.as_text(bib_ref))

    def test_bib_ref_with_title_and_box_and_accession(self):
        xml = '<bibRef>\n        <title type="main">WMUC Archives</title>\n        <bibScope type="box">1</bibScope>\n        <bibScope type="accession">2011-084</bibScope>\n      </bibRef>'
        bib_ref = self.to_element(xml)
        self.assertEqual('WMUC Archives, Accession 2011-084, Box 1', BibRefToTextConverter.as_text(bib_ref))

    def test_bib_ref_with_empty_title_and_empty_box_and_accession(self):
        xml = '<bibRef>\n                <title type="main"/>\n                <bibScope type="box"/>\n                <bibScope type="accession">2011-084</bibScope>\n              </bibRef>'
        bib_ref = self.to_element(xml)
        self.assertEqual('Accession 2011-084', BibRefToTextConverter.as_text(bib_ref))

    def test_bib_ref_with_title_and_series_and_box_and_folder_and_item(self):
        xml = '<bibRef>\n        <title type="main">Jackson R. Bryer Interviews Collection</title>\n        <bibScope type="series">1</bibScope>\n        <bibScope type="box">1</bibScope>\n        <bibScope type="folder">1</bibScope>\n        <bibScope type="item">5.0</bibScope>\n      </bibRef>'
        bib_ref = self.to_element(xml)
        self.assertEqual('Jackson R. Bryer Interviews Collection, Series 1, Box 1, Folder 1, Item 5.0', BibRefToTextConverter.as_text(bib_ref))

    def test_bib_ref_with_no_title_and_accession(self):
        xml = '<bibRef>\n                \n                \n                <bibScope type="accession">2011-084</bibScope>\n              </bibRef>'
        bib_ref = self.to_element(xml)
        self.assertEqual('Accession 2011-084', BibRefToTextConverter.as_text(bib_ref))

    def test_bib_ref_with_empty_title(self):
        xml = '<bibRef><title type="main"/></bibRef>'
        bib_ref = self.to_element(xml)
        self.assertEqual('', BibRefToTextConverter.as_text(bib_ref))

    def test_bib_with_title_and_series_and_accession_and_subseries_and_item(self):
        xml = '<bibRef><title type="main">United Brotherhood of Carpenters and Joiners America (UBC) archives</title>\n<bibScope type="series">16</bibScope>\n<bibScope type="accession">1995-94</bibScope>\n<bibScope type="subseries">2</bibScope>\n<bibScope type="item">Audio #32</bibScope></bibRef>'
        bib_ref = self.to_element(xml)
        self.assertEqual('United Brotherhood of Carpenters and Joiners America (UBC) archives, Accession 1995-94, Series 16, Subseries 2, Item Audio #32', BibRefToTextConverter.as_text(bib_ref))

    def test_bib_ref_with_title_and_accession_displays_title_first(self):
        xml = '<bibRef><bibScope type="accession">2011-166</bibScope>\n<title type="main">Test Title</title></bibRef>'
        bib_ref = self.to_element(xml)
        self.assertEqual('Test Title, Accession 2011-166', BibRefToTextConverter.as_text(bib_ref))

    def test_bib_ref_with_unexpected_bibscope_puts_bibscope_at_end(self):
        xml = '<bibRef><title type="main">Test Title</title>\n<bibScope type="accession">2011-166</bibScope><bibScope type="unknownScope">abc123</bibScope>\n</bibRef>'
        bib_ref = self.to_element(xml)
        self.assertEqual('Test Title, Accession 2011-166, Unknownscope abc123', BibRefToTextConverter.as_text(bib_ref))

    def test_bib_ref_with_unexpected_xml_puts_xml_at_end(self):
        xml = '<bibRef><title type="main">Test Title</title>\n<subtitle>Test Subtitle</subtitle>\n<bibScope type="accession">2011-166</bibScope><bibScope type="unknownScope">abc123</bibScope>\n</bibRef>'
        bib_ref = self.to_element(xml)
        self.assertEqual('Test Title, Accession 2011-166, Subtitle Test Subtitle, Unknownscope abc123', BibRefToTextConverter.as_text(bib_ref))

    def test_bib_ref_with_multiple_titles_displays_multiple_titles(self):
        xml = '<bibRef><title type="main">Test Title 1</title>\n<title type="main">Test Title 2</title>\n<bibScope type="accession">2011-166</bibScope>\n</bibRef>'
        bib_ref = self.to_element(xml)
        self.assertEqual('Test Title 1, Test Title 2, Accession 2011-166', BibRefToTextConverter.as_text(bib_ref))

    def test_bib_ref_with_multiple_bibscopes_displays_multiple_entries(self):
        xml = '<bibRef><title type="main">Test Title</title>\n<bibScope type="accession">2011-166</bibScope><bibScope type="accession">ABC-123</bibScope></bibRef>'
        bib_ref = self.to_element(xml)
        self.assertEqual('Test Title, Accession 2011-166, Accession ABC-123', BibRefToTextConverter.as_text(bib_ref))


if __name__ == '__main__':
    unittest.main()
