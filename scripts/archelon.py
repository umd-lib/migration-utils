#!/usr/bin/env python3

import json
import logging
from argparse import ArgumentParser, Namespace
from csv import DictReader, writer
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Union
from xml.dom.minidom import parse, Element, Node, Text
from xml.etree import ElementTree
import os

import iso639
import requests
import edtf
import yaml

# Convert Fedora exported and filtered objects to Archelon input format.

logging.basicConfig(level=logging.INFO, format='%(message)s')


class Object:
    """ Class to store metadata and files for a single media object. """

    def __init__(self, args: Namespace, mapping: dict):

        self.args = args
        self.mapping = mapping

        # Fedora 2 Columns
        self.f2_pid = ""
        self.f2_type = ""
        self.f2_status = ""
        self.f2_collections = ""

        # Required Columns
        self.object_type = "<unknown>"
        self.identifier = []
        self.rights_statement = "http://rightsstatements.org/vocab/UND/1.0/"
        self.title = ""

        # Optional Columns
        self.handle = ""
        self.format = "<unknown>"
        self.archival_collection = ""
        self.date = ""
        self.temporal = []
        self.description = ""
        self.bibliographic_citation = ""
        self.alternate_title = ""
        self.creator = []
        self.creator_uri = []
        self.contributor = []
        self.contributor_uri = []
        self.publisher = []
        self.publisher_uri = []
        self.location = []
        self.extent = ""
        self.subject = []
        self.language = []
        self.rights_holder = ""
        self.collection_information = ""
        self.accession_number = ""
        self.files = []


    def get_tei_umdm(self, umdm_file: Path) -> None:
        """ Get dynamically generated TEI UMDM """

        try:
            logging.info(f"Getting TEI UMDM for {self.f2_pid}")

            response = requests.get(f'https://fedora.lib.umd.edu/fedora/get/{self.f2_pid}/umd-bdef:umdm/getUMDM/')
            if not response.ok:
                logging.warning(f'No UMDM found for {self.f2_pid}')
                return

            with open(str(umdm_file), 'w') as umdm:
                logging.info(f"Writing TEI UMDM to {umdm_file}")
                umdm.write(response.text)

        except Exception as e:
            logging.error(f"Error getting TEI UMD: {e}")


    def get_edtf(self, date: str) -> str:
        """ Get Extended Data/Time Format (EDTF) string """

        if self.args.fast_mode:
            return date

        date = date \
            .replace('no date', '') \
            .replace('unknown', '') \
            .replace('不明', '') \
            .replace('-?', '')

        # Process dates in an interval separately
        dates = date.split('/')
        for i in range(len(dates)):

            dates[i] = dates[i].strip()

            try:
                # Some natural language can be converted to EDTF
                if (edtf_date := edtf.text_to_edtf(dates[i])) is not None:
                    dates[i] = edtf_date

                # Parse to make sure it is properly EDTF formatted
                dates[i] = str(edtf.parse_edtf(dates[i]))

            except Exception:
                return 'Invalid EDTF:' + date

        return '/'.join(dates)


    def process_umdm(self, umdm_path: Path) -> None:
        """ Gather data from the UMDM xml. """

        doc = parse(str(umdm_path))

        desc_meta = doc.documentElement

        century_date_range = ""

        for e in desc_meta.childNodes:

            # agent
            if e.nodeName == 'agent':
                agent_type = e.getAttribute('type')
                agent_role = e.getAttribute('role')

                for child in e.childNodes:
                    text = XmlUtils.get_text(child.childNodes)

                    if child.nodeName == 'agent':
                        self.creator.append(text)

                    elif child.nodeName == 'unknown':
                        self.contributor.append(text)

                    elif (agent_type == 'creator' and
                          (
                            child.nodeName == 'corpName' and (agent_role is None or agent_role == 'author')
                            or child.nodeName == 'persName' and (agent_role is None or agent_role == 'author')
                            or child.nodeName == 'other'
                          )):
                        self.creator.append(text)

                    elif (agent_type == 'contributor' and
                          (
                            child.nodeName == 'corpName' and (agent_role is None or agent_role in ('illustrator', 'editor'))
                            or child.nodeName == 'persName' and (agent_role is None or agent_role in ('illustrator', 'editor'))
                            or child.nodeName == 'other'
                          )):
                        self.contributor.append(text)

                    elif (agent_type == 'provider'
                          and child.nodeName in ('corpName', 'persName', 'other')):
                        self.publisher.append(text)

            # covPlace
            elif e.nodeName == 'covPlace':
                for geogName in e.getElementsByTagName('geogName'):
                    type = geogName.getAttribute('type')
                    if type in ('continent', 'country', 'region', 'settlement', 'zone', 'bloc'):
                        text = XmlUtils.get_text(geogName.childNodes)
                        if text != 'not captured':
                            self.location.append(text)

            # covTime
            elif e.nodeName == 'covTime':

                # TODO: determine Archelon date range format

                for date in e.getElementsByTagName('date'):
                    self.date = self.get_edtf(XmlUtils.get_text(date.childNodes))

                for dateRange in e.getElementsByTagName('dateRange'):
                    date_from = dateRange.getAttribute('from')
                    date_to = dateRange.getAttribute('to')
                    self.date = self.get_edtf(date_from + "/" + date_to)

                for century in e.getElementsByTagName('century'):
                    text = XmlUtils.get_text(century.childNodes)
                    # Save for later, if no other date is found
                    century_date_range = text.replace("-", "/")

            # description
            elif e.nodeName == 'description':

                text = XmlUtils.get_text(e.childNodes)

                if self.description:
                    self.description += "; "
                self.description += text

            # identifier
            elif e.nodeName == 'identifier':

                text = XmlUtils.get_text(e.childNodes)

                self.identifier.append(text)

            # language
            elif e.nodeName == 'language':

                text = XmlUtils.get_text(e.childNodes)
                for value in text.split("; "):
                    if not self.args.fast_mode:
                        if (match := iso639.find(whatever=value)) is not None:
                            value = match['iso639_2_b']
                    self.language.append(value)

            # mediaType
            elif e.nodeName == 'mediaType':
                mediaType = e.getAttribute('type')

                if mediaType in self.mapping['object_type']:
                    self.object_type = self.mapping['object_type'][mediaType]
                else:
                    self.object_type = f'Not Mapped: {mediaType}'

                for form in e.getElementsByTagName('form'):
                    form = XmlUtils.get_text(form.childNodes)

                    if form in self.mapping['format']:
                        self.format = self.mapping['format'][form]
                    else:
                        self.format = f'Not Mapped: {form}'

            # physDesc
            elif e.nodeName == 'physDesc':

                for node in e.childNodes:
                    text = XmlUtils.get_text(node.childNodes)

                    if node.nodeName in ('color', 'format'):
                        if self.extent:
                            self.extent += '; '
                        self.extent += text

                    elif node.nodeName in ('extent', 'size'):
                        if self.extent:
                            self.extent += '; '
                        text += " " + node.getAttribute('units')
                        self.extent += text

                    elif node.nodeName == 'documents':
                        if node.getAttribute('type') == 'pbccd':
                            text = XmlUtils.get_text(node.childNodes)

                            if self.description:
                                self.description += "; "
                            self.description += f'{text} pbccd'

            # relationships
            elif e.nodeName == 'relationships':

                for node in e.childNodes:
                    if node.nodeName == 'relation':

                        relation = node.getAttribute('label')
                        rtype = node.getAttribute('type')

                        if relation == 'archivalcollection':

                            for relationChild in node.childNodes:
                                if relationChild.nodeName == 'bibRef':

                                    note_text = BibRefToTextConverter.as_text(relationChild)
                                    escaped_note_text = note_text.encode("unicode_escape").decode("utf-8")
                                    self.bibliographic_citation = escaped_note_text

                                    for bibRefChild in relationChild.childNodes:
                                        if bibRefChild.nodeName == 'title':
                                            if bibRefChild.getAttribute('type') == 'main':
                                                titleText = XmlUtils.get_text(bibRefChild.childNodes)
                                                ac = titleText

                                                if ac in self.mapping['archival_collection']:
                                                    self.archival_collection = self.mapping['archival_collection'][ac]
                                                else:
                                                    self.archival_collection = f'Not Mapped: {ac}'


                        elif relation in ('fair', 'component', 'category', 'series', 'subcode#'):
                            text = XmlUtils.get_text(node.childNodes)

                            if self.bibliographic_citation:
                                self.bibliographic_citation += ', '
                            self.bibliographic_citation += relation.capitalize() + " " + text

                        elif not relation and rtype == 'isPartOf':
                            text = XmlUtils.get_text(node.childNodes)

                            if self.bibliographic_citation:
                                self.bibliographic_citation += ', '
                            self.bibliographic_citation += text

                        for relationChild in node.childNodes:
                            if relationChild.nodeName == 'identifier':
                                text = XmlUtils.get_text(relationChild.childNodes)

                                if self.bibliographic_citation:
                                    self.bibliographic_citation += ', '
                                self.bibliographic_citation += text

            # rights
            elif e.nodeName == 'rights':

                if e.getAttribute('type') == 'copyrightowner':
                    self.rights_holder = XmlUtils.get_text(e.childNodes)

                else:
                    self.rights_statement = XmlUtils.get_text(e.childNodes)

            # subject
            elif e.nodeName == 'subject':
                text = XmlUtils.get_text(e.childNodes)
                if text:
                    self.subject.append(text)

                for node in e.childNodes:
                    text = XmlUtils.get_text(node.childNodes)

                    if node.nodeName in ('browse', 'corpName', 'other', 'persName'):
                        self.subject.append(text)

                    elif node.nodeName in ('geogName'):
                        self.location.append(text)

                    elif node.nodeName in ('date', 'decade'):
                        self.temporal.append(text)

            # title
            elif e.nodeName == 'title':

                if e.getAttribute('type') == 'main':
                    text = XmlUtils.get_text(e.childNodes)

                    if self.title:
                        self.title += " / "
                    self.title += text

                if e.getAttribute('type') == 'alternate':
                    text = XmlUtils.get_text(e.childNodes)

                    if self.alternate_title:
                        self.alternate_title += " / "
                    self.alternate_title += text

            # repository
            elif e.nodeName == 'repository':

                for node in e.childNodes:
                    if node.nodeName == 'corpName':

                        text = XmlUtils.get_text(node.childNodes)
                        if self.bibliographic_citation:
                            self.bibliographic_citation += ', '
                        self.bibliographic_citation += text

        # Use century for date, if necessary
        if not self.date and century_date_range:
            self.temporal.append(century_date_range)


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

    @staticmethod
    def descendentNodes(parent: Node, nodes: List) -> List:
        ''' Return all descendent nodes of parent. '''
        for child in parent.childNodes:
            nodes.append(child)
            XmlUtils.descendentNodes(child, nodes)

        return nodes


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
            item_text = XmlUtils.get_text(XmlUtils.descendentNodes(e, [])).strip()
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
            ["F2 PID", "F2 TYPE", "F2 STATUS", "F2 COLLECTIONS"] \
            + ["Object Type", "Identifier", "Rights Statement", "Title", "Handle/Link"] \
            + ["Format", "Archival Collection", "Date", "dcterms:temporal"] \
            + ["Description", "Bibliographic Citation", "Alternate Title"] \
            + ["Creator", "Creator URI", "Contributor", "Contributor URI", "Publisher", "Publisher URI"] \
            + ["Location", "Extent", "Subject", "Language", "Rights Holder", "Collection Information"] \
            + ["Accession Number", "FILES"]

    def convert(self, obj: Object) -> List[str]:
        '''
        Converts the given Object into a List of strings for output as CSV row.

        :param obj: the Object to output
        :return: a List of Strings with entries matching the "headers" layout
        '''
        row = [
            # F2 PID
            obj.f2_pid,

            # F2 TYPE
            obj.f2_type,

            # F2 STATUS
            obj.f2_status,

            # F2 COLLECTIONS
            self.multicolumn(obj.f2_collections),

            # Object Type
            obj.object_type,

            # Identifier
            self.multicolumn(obj.identifier),

            # Rights Statement
            obj.rights_statement,

            # Title
            obj.title,

            # Handle/Link
            obj.handle,

            # Format
            obj.format,

            # Archival Collection
            obj.archival_collection,

            # Date
            obj.date,

            # Temporal
            self.multicolumn(obj.temporal),

            # Description
            obj.description,

            # Bibliographic Citation
            obj.bibliographic_citation,

            # Alternate Title
            obj.alternate_title,

            # Creator
            self.multicolumn(obj.creator),

            # Creator URI
            self.multicolumn(obj.creator_uri),

            # Contributor
            self.multicolumn(obj.contributor),

            # Contributor URI
            self.multicolumn(obj.contributor_uri),

            # Publisher
            self.multicolumn(obj.publisher),

            # Publisher URI
            self.multicolumn(obj.publisher_uri),

            # Location
            self.multicolumn(obj.location),

            # Extent
            obj.extent,

            # Subject
            self.multicolumn(obj.subject),

            # Language
            self.multicolumn(obj.language),

            # Rights Holder
            obj.rights_holder,

            # Collection Information
            obj.collection_information,

            # Accession Number
            obj.accession_number,

            # FILES
            self.multicolumn(obj.files),
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

    parser.add_argument('-f', '--fast-mode',
                        default=False, action='store_true',
                        help='Fast mode: disable some slower computations')

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


def load_filter(filter_data_path: Path) -> Optional[dict]:
    """ Load in filter.json """
    filter_data = {}
    with filter_data_path.open(mode='r') as filter_data_file:
        logging.info(f'Reading filter data from {filter_data_path}')
        for line in filter_data_file:
            record = json.loads(line)
            filter_data[record['pid']] = record
    return filter_data


def load_mapping() -> Optional[dict]:
    """ Load in data/archelon-mapping.yml """

    # Assume cwd is the migration-utils directory)
    mapping_file = 'data/archelon-mapping.yml'

    logging.info(f'Reading mapping data from {mapping_file}')
    with open(mapping_file, 'r') as mapping_file:
        mapping = yaml.safe_load(mapping_file)

    return mapping


def main(args: Namespace) -> None:
    """ Main conversion loop. """

    objects = []
    obj = None

    target = Path(args.target_dir)

    # Load index information
    index_path = Path(args.index_path) if args.index_path else target / 'index.json'
    index = load_index(index_path)

    # Load filter.json data
    if not args.fast_mode:
        filter_data = load_filter(target / 'filter.json')

    # Load mapping document (assumes cwd is the migration-utils directory)
    mapping = load_mapping()

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
                obj = Object(args, mapping)

                obj.title = ""
                obj.identifier.append(umdm)

                if record['handle'].startswith("hdl:"):
                    obj.handle = 'https://hdl.handle.net/' + record['handle'][4:]
                    obj.identifier.append(record['handle'])

                obj.f2_pid = umdm

                if not args.fast_mode:
                    obj.f2_type = filter_data[umdm]['ds']['doInfo']['type']
                    obj.f2_status = filter_data[umdm]['ds']['doInfo']['status']

                    collections = set()
                    rels = filter_data[umdm]['ds']['rels-mets']['rels']
                    if 'isMemberOfCollection' in rels:
                        for collection in rels['isMemberOfCollection']:
                            collections.add(collection)
                    if len(collections) > 1 and "umd:3392" in collections:
                        # Remove Digital Collections, if there a more than one collection
                        collections.remove("umd:3392")
                    obj.f2_collections = list(collections)

                umdm_file = target / record['location'] / 'umdm.xml'

                if obj.f2_type == 'UMD_TEI' and not umdm_file.exists():
                    obj.get_tei_umdm(umdm_file)

                try:
                    obj.process_umdm(umdm_file)

                except Exception as e:
                    text = f'Error reading umdm.xml: {e}'
                    logging.error(text)
                    obj.title = text

                objects.append(obj)

            else:
                # add UMAM to the current UMDM
                if obj is None:
                    # UMAM occurred before a UMDM
                    raise Exception(f'File {export_path} is not formatted correctly')

                umdm_umam_path = Path(umdm.replace(":", "_"), umam.replace(":", "_"))

                # add any files provided by the restored files index
                if index is not None:

                    try:
                        filename = index[umdm][umam]
                        obj.files.append([f'{umdm_umam_path}/{filename}', umam])
                    except KeyError:
                        doc = ElementTree.parse(target / umdm_umam_path / 'umam.xml')
                        filename = doc.getroot().findtext('./technical/fileName') or doc.getroot().findtext('./identifier')
                        obj.files.append(['MISSING', filename or ''])
                        missing_files.append(f'{umdm}/{umam}')
                        logging.warning(f'File for {umdm}/{umam} not found in restored files index')

                # add any files provided by the Fedora 2 export
                try:
                    umam_files = os.listdir(target / umdm_umam_path)
                except FileNotFoundError:
                    # the umam directory may be missing, if umam files are suppressed from extract
                    continue

                for file in umam_files:
                    # ignore these files
                    if file in ('amInfo-properties.json', 'amInfo.xml', 'foxml.xml', 'properties.json',
                                'umam-properties.json', 'umam.xml') \
                            or file.endswith('-properties.json'):
                        continue

                    # add this file
                    obj.files.append(f'{umdm_umam_path}/{file}')

    # Write output csv
    if args.fast_mode:
        manifest_path = target / 'fast.csv'
    else:
        manifest_path = target / 'batch_manifest.csv'

    logging.info(f"Writing output {manifest_path}")
    logging.info(f"  {len(objects)} objects")
    logging.info(f'  {len(missing_files)} missing files')

    write_csv(manifest_path, objects)


if __name__ == '__main__':
    # Run the conversion
    main(process_args())
