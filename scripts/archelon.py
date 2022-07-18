#!/usr/bin/env python3

import json
import logging
from argparse import ArgumentParser, Namespace
from csv import DictReader, writer
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Union
from xml.dom.minidom import parse, Element, Node, Text
from xml.etree import ElementTree

# Convert Fedora exported and filtered objects to Archelon input format.

logging.basicConfig(level=logging.INFO, format='%(message)s')

languageMap = {
    "ar": "Arabic",
    "da": "Danish",
    "de": "German",
    "dut": "Dutch",
    "el": "Greek",
    "en-GB": "English",
    "en-US": "English",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "fre": "French",
    "ger": "German",
    "he": "Hebrew",
    "it": "Italian",
    "ja": "Japanese",
    "jpn": "Japanese",
    "ko": "Korean",
    "la": "Latin",
    "lat": "Latin",
    "pl": "Polish",
    "pt": "Portuguese",
    "spa": "Spanish",
    "zh": "Chinese",
}


class Object:
    """ Class to store metadata and files for a single media object. """

    def __init__(self):
        self.bib_id_label = ""
        self.bib_id = ""
        self.other_identifier = []  # (type, value)
        self.title = ""
        self.creator = []
        self.contributor = []
        self.genre = []
        self.publisher = []
        self.date_created = ""
        self.date_issued = ""
        self.abstract = ""
        self.language = []
        self.physical_description = ""
        self.related_item = []  # (label, url)
        self.geographic_subject = []
        self.topical_subject = []
        self.temporal_subject = []
        self.terms_of_use = ""
        self.table_of_contents = ""
        self.note = []  # (type, value)
        self.publish = "No"
        self.hidden = "No"

        # Offset, Skip Transcoding, Absolute Location, and Date Ingested are
        # not currently supported
        self.file = []  # (file, label)

    def process_umdm(self, umdm_path: Path) -> None:
        """ Gather data from the UMDM xml. """

        doc = parse(str(umdm_path))

        desc_meta = doc.documentElement

        century_date_range = ""

        for e in desc_meta.childNodes:

            # agent
            if e.nodeName == 'agent':
                agent_type = e.getAttribute('type')
                for node in e.childNodes:
                    if node.nodeName in ('persName', 'corpName'):
                        text = XmlUtils.get_text(node.childNodes)
                        if agent_type == 'contributor':
                            self.contributor.append(text)
                        elif agent_type == 'creator':
                            self.creator.append(text)
                        elif agent_type == 'provider':
                            self.publisher.append(text)

            # covPlace
            elif e.nodeName == 'covPlace':
                for geogName in e.getElementsByTagName('geogName'):
                    text = XmlUtils.get_text(geogName.childNodes)
                    if text != 'not captured':
                        self.geographic_subject.append(text)

            # covTime
            elif e.nodeName == 'covTime':

                for date in e.getElementsByTagName('date'):
                    self.date_issued = XmlUtils.get_text(date.childNodes)

                for dateRange in e.getElementsByTagName('dateRange'):
                    date_from = dateRange.getAttribute('from')
                    date_to = dateRange.getAttribute('to')
                    self.date_issued = date_from + "/" + date_to

                for century in e.getElementsByTagName('century'):
                    text = XmlUtils.get_text(century.childNodes)

                    # Save the century as date range, in case we need it for the
                    # date_issued
                    century_date_range = text.replace("-", "/")

            # description
            elif e.nodeName == 'description':

                description_type = e.getAttribute('type')
                text = XmlUtils.get_text(e.childNodes)

                if description_type == 'summary':
                    if self.abstract:
                        self.abstract += "; "
                    self.abstract += text

                elif description_type == 'credits':
                    self.note.append(('creation/production credits', text))

            # language
            elif e.nodeName == 'language':

                text = XmlUtils.get_text(e.childNodes)
                for value in text.split("; "):
                    if value in languageMap:
                        value = languageMap[value]
                    self.language.append(value)

            # subject
            elif e.nodeName == 'subject':

                subject_type = e.getAttribute('type')
                text = XmlUtils.get_text(e.childNodes)

                if subject_type == 'genre':
                    self.genre.append(text)

                else:
                    self.topical_subject.append(text)

            # culture
            elif e.nodeName == 'culture':
                text = XmlUtils.get_text(e.childNodes)
                if text != 'not captured':
                    self.topical_subject.append(text + ' Culture')

            # identifier
            elif e.nodeName == 'identifier':

                identifier_type = e.getAttribute('type')
                text = XmlUtils.get_text(e.childNodes)

                if identifier_type == 'oclc':
                    self.other_identifier.append(('oclc', text))

                else:
                    self.other_identifier.append(('local', text))

            # physDesc
            elif e.nodeName == 'physDesc':

                for node in e.childNodes:
                    text = XmlUtils.get_text(node.childNodes)

                    if node.nodeName in ('color', 'format'):
                        if self.physical_description:
                            self.physical_description += '; '
                        self.physical_description += text

                    if node.nodeName in ('extent', 'size'):
                        if self.physical_description:
                            self.physical_description += '; '
                        text += " " + node.getAttribute('units')
                        self.physical_description += text

            # relationships
            elif e.nodeName == 'relationships':

                for node in e.childNodes:
                    if node.nodeName == 'relation':
                        relation = node.getAttribute('label')
                        if relation == 'archivalcollection':
                            for relationChild in node.childNodes:
                                if relationChild.nodeName == 'bibRef':
                                    note_text = BibRefToTextConverter.as_text(relationChild)
                                    escaped_note_text = note_text.encode("unicode_escape").decode("utf-8")
                                    self.note.append(('general', escaped_note_text))

            # rights
            elif e.nodeName == 'rights':
                if self.terms_of_use:
                    self.terms_of_use += '; '
                self.terms_of_use += XmlUtils.get_text(e.childNodes)

        # Use century for date_issued, if necessary
        if not self.date_issued and century_date_range:
            self.date_issued = century_date_range


class XmlUtils:
    '''Utilties for handling minidom XML elements'''
    @staticmethod
    def collapse_whitespace_nodes(element: Element) -> None:
        '''
        Collapses extraneous whitespace child elements in given element,
        and normalizes. This method preserves the XML tag information.
        Largely taken from "remove_whitespace" method in
        https://realpython.com/python-xml-parser/

        :param element: the Element to modify (element is modified in place)
        '''
        if element.nodeType == Node.TEXT_NODE:
            if element.nodeValue.strip() == "":
                element.nodeValue = ""
        for child in element.childNodes:
            XmlUtils.collapse_whitespace_nodes(child)
        element.normalize()

    @staticmethod
    def get_text(nodelist: Iterable[Union[Element, Text]]) -> str:
        '''
        Extract text from an XML node list

        :param nodelist: an Iterable of Elements to extract the text from
        '''
        return ''.join(node.data.strip().replace('\n', '') for node in nodelist if node.nodeType == node.TEXT_NODE)


class BibRefToTextConverter:
    '''
    Converts <bibRef> XML element into a text string.
    '''

    # Order to output bibScope types
    BIBSCOPE_TYPE_OUTPUT_ORDER = [
        'accession', 'series', 'subseries', 'box', 'folder', 'item'
    ]

    @staticmethod
    def as_text(bib_ref: Element) -> str:
        '''
        Converts <bibRef> nodes into multi-line text describing the bibRef

        :param bib_ref: the Element to convert
        :return: a text string containing the information in the bibRef element
        '''
        XmlUtils.collapse_whitespace_nodes(bib_ref)

        bib_ref_dict = BibRefToTextConverter.bib_ref_to_dict(bib_ref)
        text_elements = BibRefToTextConverter.bib_ref_dict_to_text(bib_ref_dict)

        result_text = ', '.join(text_elements)
        return result_text

    @staticmethod
    def bib_ref_to_dict(bib_ref: Element) -> Dict[str, List[str]]:
        '''
        Converts a bibRef into a Dict with keys based on tag name or
        bibScope type.

        The key for each entry is either:
          * the tag name (such as "title"),
          * for "<bibScope>" tags only, the "type" attribute

        The value stored in the map is a list (as there could possibly be
        multiple instance of a tag or bibScope type) -- there will be one entry
        in the list for each instance.

        :param bib_ref: the Element to convert
        :return: A Dict of keys and values representing the information in the
                bibRef
        '''
        bib_ref_items: Dict[str, List[str]] = {}
        for e in bib_ref.childNodes:
            item_text = XmlUtils.get_text(e.childNodes).strip()
            if item_text == '':
                continue

            node_name = e.nodeName
            key = node_name
            if (node_name == 'bibScope'):
                key = e.getAttribute('type')

            entries = bib_ref_items.get(key, [])
            entries.append(item_text)
            bib_ref_items[key] = entries

        return bib_ref_items

    @staticmethod
    def bib_ref_dict_to_text(bib_ref_dict: Dict[str, List[str]]) -> List[str]:
        '''
        Converted the bibRef dict into a text string, ensuring that the
        text from the <title> tag (if present) appears first, followed by
        the bibScope types in the order defined by BIBSCOPE_TYPE_OUTPUT_ORDER
        (skipping any missing types).

        Any other tags or bibScope types are placed at the end, in an undefined
        order.

        :param bib_ref_dict: Dict from 'bib_ref_to_dict' method to convert
        :return: a List of Strings representing the bibRef information
        '''
        text_elements = []

        bib_ref_dict_keys = list(bib_ref_dict)

        # Title is always first - no caption is added
        if 'title' in bib_ref_dict:
            title_entries = bib_ref_dict['title']
            for title in title_entries:
                text_elements.append(title)

            bib_ref_dict_keys.remove('title')

        # Bibscopes in provided order
        for bibscope_type in BibRefToTextConverter.BIBSCOPE_TYPE_OUTPUT_ORDER:
            if bibscope_type in bib_ref_dict:
                caption = bibscope_type.capitalize()
                for entry in bib_ref_dict[bibscope_type]:
                    text_elements.append(f"{caption} {entry}")

                bib_ref_dict_keys.remove(bibscope_type)

        # Anything left in the bib_ref_dict_keys goes at the end
        for key in bib_ref_dict_keys:
            value = bib_ref_dict[key]
            caption = key.capitalize()
            for entry in value:
                text_elements.append(f"{caption} {entry}")

        return text_elements


class ObjectToCsvConverter:
    '''Converts an Object into format suitable for CSV'''
    def __init__(self):
        '''
        Constructs an ObjectToCsvConverter.
        '''

        self.headers = \
            ["Bibliographic ID Label", "Bibliographic ID"] \
            + ["Other Identifier Type", "Other Identifier"] \
            + ["Title"] \
            + ["Creator"] \
            + ["Contributor"] \
            + ["Genre"] \
            + ["Publisher"] \
            + ["Date Created", "Date Issued", "Abstract"] \
            + ["Language"] \
            + ["Physical Description"] \
            + ["Related Item Label", "Related Item URL"] \
            + ["Topical Subject"] \
            + ["Geographic Subject"] \
            + ["Temporal Subject"] \
            + ["Terms of Use", "Table of Contents"] \
            + ["Note Type", "Note"] \
            + ["Publish", "Hidden"] \
            + ["File", "Label"]

    def convert(self, obj: Object) -> List[str]:
        '''
        Converts the given Object into a List of strings for output as CSV row.

        :param obj: the Object to output
        :return: a List of Strings with entries matching the "headers" layout
        '''
        row = [
            # "Bibliographic ID Label", "Bibliographic ID"
            obj.bib_id_label,
            obj.bib_id,

            # "Other Identifier Type", Other Identifier"
            self.multicolumn(list(item[0] for item in obj.other_identifier)),
            self.multicolumn(list(item[1] for item in obj.other_identifier)),

            # "Title"
            obj.title,

            # "Creator"
            self.multicolumn(obj.creator),

            # "Contributor"
            self.multicolumn(obj.contributor),

            # "Genre"
            self.multicolumn(obj.genre),

            # "Publisher"
            self.multicolumn(obj.publisher),

            # "Date Created", "Date Issued", "Abstract"
            obj.date_created,
            obj.date_issued,
            obj.abstract,

            # "Language"
            self.multicolumn(obj.language),

            # "Physical Description"
            obj.physical_description,

            # "Related Item Label", "Related Item URL"
            self.multicolumn(list(item[0] for item in obj.related_item)),
            self.multicolumn(list(item[1] for item in obj.related_item)),

            # "Topical Subject"
            self.multicolumn(obj.topical_subject),

            # "Geographic Subject"
            self.multicolumn(obj.geographic_subject),

            # "Temporal Subject"
            self.multicolumn(obj.temporal_subject),

            # "Terms of Use", "Table of Contents"
            obj.terms_of_use,
            obj.table_of_contents,

            # "Note Type", "Note"
            self.multicolumn(list(item[0] for item in obj.note)),
            self.multicolumn(list(item[1] for item in obj.note)),

            # "Publish", "Hidden"
            obj.publish,
            obj.hidden,

            # "File", "Label"
            self.multicolumn([item[0] for item in obj.file]),
            self.multicolumn([item[1] for item in obj.file]),
        ]

        return row


    @staticmethod
    def multicolumn(values: list) -> str:
        """
        Format multiple values.

        :param values: list of values
        :return: values joined into one column
        """
        return "|".join(values)


def process_args() -> Namespace:
    """ Process command line arguments. """

    # Setup command line arguments
    parser = ArgumentParser()

    parser.add_argument("-a", "--target-dir", required=True,
                        type=str,
                        help="Target directory with exported Fedora objects")

    parser.add_argument('-x', '--index-path',
                        type=str,
                        help='JSON file mapping UMDM/UMAM PIDs to file paths')

    # Process command line arguments
    args = parser.parse_args()

    return args


def write_csv(manifest_path: Path, objects: List[Object]) -> None:
    """ Write objects out to the CSV manifest file. """

    converter = ObjectToCsvConverter()

    # Build the headers
    headers = converter.headers

    # Write the output CSV file
    with manifest_path.open(mode='w', newline='') as manifest_file:
        manifest_csv = writer(manifest_file)

        # Write the header row
        manifest_csv.writerow(headers)

        # Write each object row
        for obj in objects:
            row = converter.convert(obj)
            # Write the row
            manifest_csv.writerow(row)


def load_index(index_path: Path) -> Optional[dict]:
    if not index_path.is_file():
        logging.warning(f'No index file found at {index_path}; will skip linking objects to their files')
        return None
    else:
        index = {}
        with index_path.open(mode='r') as index_file:
            logging.info(f'Reading index from {index_path}')
            for line in index_file:
                index.update(json.loads(line))
        return index


def main(args: Namespace) -> None:
    """ Main conversion loop. """

    objects = []
    obj = None

    target = Path(args.target_dir)

    index_path = Path(args.index_path) if args.index_path else target / 'index.json'
    index = load_index(index_path)

    # Read in objects
    export_path = target / 'export.csv'
    logging.info(f"Reading input objects from {export_path}")
    missing_files = []

    with export_path.open(mode='r') as export_file:
        export_csv = DictReader(export_file)

        for record in export_csv:
            umam = record['umam']
            umdm = record['umdm']
            if not umam:
                # Process UMDM, start new object
                obj = Object()

                obj.title = record['title']
                obj.other_identifier.append(("local", umdm))
                obj.other_identifier.append(('handle', record['handle']))

                obj.process_umdm(target / record['location'] / 'umdm.xml')

                objects.append(obj)
            else:
                # add UMAM to the current UMDM
                if obj is None:
                    # UMAM occurred before a UMDM
                    raise Exception(f'File {export_path} is not formatted correctly')
                if index is None:
                    logging.debug(f'No restored files index configured; skipping file linking for {umdm}/{umam}')
                    continue

                umdm_umam_path = Path(umdm.replace(":", "_"), umam.replace(":", "_"))
                try:
                    filename = index[umdm][umam]
                    obj.file.append([f'{umdm_umam_path}/{filename}', umam])
                except KeyError:
                    doc = ElementTree.parse(target / umdm_umam_path / 'umam.xml')
                    filename = doc.getroot().findtext('./technical/fileName') or doc.getroot().findtext('./identifier')
                    obj.file.append(['MISSING', filename or ''])
                    missing_files.append(f'{umdm}/{umam}')
                    logging.warning(f'File for {umdm}/{umam} not found in restored files index')

    # Write output csv
    manifest_path = target / 'batch_manifest.csv'
    logging.info(f"Writing output {manifest_path}")
    logging.info(f"  {len(objects)} objects")
    logging.info(f'  {len(missing_files)} missing files')

    write_csv(manifest_path, objects)


if __name__ == '__main__':
    # Run the conversion
    main(process_args())
