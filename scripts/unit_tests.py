#!/usr/bin/env python3

'''Unit tests for Python scripts'''
import unittest

from xml.dom.minidom import parseString
from avalon import BibRefToTextConverter, XmlUtils


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
