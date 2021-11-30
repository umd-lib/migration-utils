#!/usr/bin/env python3

'''Unit tests for Python scripts'''
import unittest

from xml.dom.minidom import parseString
from avalon import bibref_to_note_text, collapse_whitespace_nodes


class TestBibRefToNoteText(unittest.TestCase):
    '''Test cases for the 'bibref_to_note_text' method in avalon.py'''

    @staticmethod
    def to_element(xml: str):
        '''Converts the given string into minidom Element'''
        doc = parseString(str(xml))
        collapse_whitespace_nodes(doc)
        doc_element = doc.documentElement
        return doc_element

    def test_bibref_with_no_children(self):
        xml = '<bibRef />'
        bibref = self.to_element(xml)
        self.assertEqual('', bibref_to_note_text(bibref))

        xml = '<bibRef></bibRef>'
        bibref = self.to_element(xml)
        self.assertEqual('', bibref_to_note_text(bibref))

    def test_bibref_with_only_title(self):
        xml = '<bibRef>\n        <title type="main">Madrigal Singers</title>\n      </bibRef>'
        bibref = self.to_element(xml)
        self.assertEqual('Madrigal Singers', bibref_to_note_text(bibref))

    def test_bibref_with_title_and_accession(self):
        xml = '<bibRef><title type="main">University of Maryland\xa0Football\xa0Heritage\xa0Film\xa0Collection</title>\n<bibScope type="accession">2011-166</bibScope></bibRef>'
        bibref = self.to_element(xml)
        self.assertEqual('University of Maryland\xa0Football\xa0Heritage\xa0Film\xa0Collection, Accession 2011-166', bibref_to_note_text(bibref))

    def test_bibref_with_title_and_box_and_accession(self):
        xml = '<bibRef>\n        <title type="main">WMUC Archives</title>\n        <bibScope type="box">1</bibScope>\n        <bibScope type="accession">2011-084</bibScope>\n      </bibRef>'
        bibref = self.to_element(xml)
        self.assertEqual('WMUC Archives, Box 1, Accession 2011-084', bibref_to_note_text(bibref))

    def test_bibref_with_empty_title_and_empty_box_and_accession(self):
        xml = '<bibRef>\n                <title type="main"/>\n                <bibScope type="box"/>\n                <bibScope type="accession">2011-084</bibScope>\n              </bibRef>'
        bibref = self.to_element(xml)
        self.assertEqual('Accession 2011-084', bibref_to_note_text(bibref))

    def test_bibref_with_title_and_series_and_box_and_folder_and_item(self):
        xml = '<bibRef>\n        <title type="main">Jackson R. Bryer Interviews Collection</title>\n        <bibScope type="series">1</bibScope>\n        <bibScope type="box">1</bibScope>\n        <bibScope type="folder">1</bibScope>\n        <bibScope type="item">5.0</bibScope>\n      </bibRef>'
        bibref = self.to_element(xml)
        self.assertEqual('Jackson R. Bryer Interviews Collection, Series 1, Box 1, Folder 1, Item 5.0', bibref_to_note_text(bibref))

    def test_bibref_with_no_title_and_accession(self):
        xml = '<bibRef>\n                \n                \n                <bibScope type="accession">2011-084</bibScope>\n              </bibRef>'
        bibref = self.to_element(xml)
        self.assertEqual('Accession 2011-084', bibref_to_note_text(bibref))

    def test_bibref_with_empty_title(self):
        xml = '<bibRef><title type="main"/></bibRef>'
        bibref = self.to_element(xml)
        self.assertEqual('', bibref_to_note_text(bibref))

    def test_bib_with_title_and_series_and_accession_and_subseries_and_item(self):
        xml = '<bibRef><title type="main">United Brotherhood of Carpenters and Joiners America (UBC) archives</title>\n<bibScope type="series">16</bibScope>\n<bibScope type="accession">1995-94</bibScope>\n<bibScope type="subseries">2</bibScope>\n<bibScope type="item">Audio #32</bibScope></bibRef>'
        bibref = self.to_element(xml)
        self.assertEqual('United Brotherhood of Carpenters and Joiners America (UBC) archives, Series 16, Accession 1995-94, Subseries 2, Item Audio #32', bibref_to_note_text(bibref))

    def test_bibref_with_title_and_accession_displays_title_first(self):
        xml = '<bibRef><bibScope type="accession">2011-166</bibScope>\n<title type="main">Test Title</title></bibRef>'
        bibref = self.to_element(xml)
        self.assertEqual('Test Title, Accession 2011-166', bibref_to_note_text(bibref))


if __name__ == '__main__':
    unittest.main()
