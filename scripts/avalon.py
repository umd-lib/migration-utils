#!/usr/bin/env python3

import json
import logging
from argparse import ArgumentParser, Namespace
from csv import DictReader, writer
from pathlib import Path
from typing import Optional, Iterable, Union
from xml.dom.minidom import parse, Element, Text

# Convert Fedora exported objects to Avalon input format.
#
# Input - json info file with flat list of all objects
#
# Output - json info file which is filtered for matching UMDM objects and
#          their hasPart UMAM objects listed under the 'hasPart' key in the
#          UMDM object
from xml.etree import ElementTree

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

        self.handle = ''

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
                        text = get_text(node.childNodes)
                        if agent_type == 'contributor':
                            self.contributor.append(text)
                        elif agent_type == 'creator':
                            self.creator.append(text)
                        elif agent_type == 'provider':
                            self.publisher.append(text)

            # covPlace
            elif e.nodeName == 'covPlace':
                for geogName in e.getElementsByTagName('geogName'):
                    text = get_text(geogName.childNodes)
                    if text != 'not captured':
                        self.geographic_subject.append(text)

            # covTime
            elif e.nodeName == 'covTime':

                for date in e.getElementsByTagName('date'):
                    self.date_issued = get_text(date.childNodes)

                for dateRange in e.getElementsByTagName('dateRange'):
                    date_from = dateRange.getAttribute('from')
                    date_to = dateRange.getAttribute('to')
                    self.date_issued = date_from + "/" + date_to

                for century in e.getElementsByTagName('century'):
                    text = get_text(century.childNodes)

                    # Save the century as date range, in case we need it for the
                    # date_issued
                    century_date_range = text.replace("-", "/")

            # description
            elif e.nodeName == 'description':

                description_type = e.getAttribute('type')
                text = get_text(e.childNodes)

                if description_type == 'summary':
                    if self.abstract:
                        self.abstract += "; "
                    self.abstract += text

                elif description_type == 'credits':
                    self.note.append(('creation/production credits', text))

            # language
            elif e.nodeName == 'language':

                text = get_text(e.childNodes)
                for value in text.split("; "):
                    if value in languageMap:
                        value = languageMap[value]
                    self.language.append(value)

            # subject
            elif e.nodeName == 'subject':

                subject_type = e.getAttribute('type')
                text = get_text(e.childNodes)

                if subject_type == 'genre':
                    self.genre.append(text)

                else:
                    self.topical_subject.append(text)

            # culture
            elif e.nodeName == 'culture':
                text = get_text(e.childNodes)
                if text != 'not captured':
                    self.topical_subject.append(text + ' Culture')

            # identifier
            elif e.nodeName == 'identifier':

                identifier_type = e.getAttribute('type')
                text = get_text(e.childNodes)

                if identifier_type == 'oclc':
                    self.other_identifier.append(('oclc', text))

                else:
                    self.other_identifier.append(('local', text))

            # physDesc
            elif e.nodeName == 'physDesc':

                for node in e.childNodes:
                    text = get_text(node.childNodes)

                    if node.nodeName in ('color', 'format'):
                        if self.physical_description:
                            self.physical_description += '; '
                        self.physical_description += text

                    if node.nodeName in ('extent', 'size'):
                        if self.physical_description:
                            self.physical_description += '; '
                        text += " " + node.getAttribute('units')
                        self.physical_description += text

            # rights
            elif e.nodeName == 'rights':
                if self.terms_of_use:
                    self.terms_of_use += '; '
                self.terms_of_use += get_text(e.childNodes)

        # Use century for date_issued, if necessary
        if not self.date_issued and century_date_range:
            self.date_issued = century_date_range


def process_args() -> Namespace:
    """ Process command line arguments. """

    # Setup command line arguments
    parser = ArgumentParser()

    parser.add_argument("-a", "--target-dir", required=True,
                        type=str,
                        help="Target directory with exported Fedora objects")

    parser.add_argument("-t", "--title", required=True,
                        type=str,
                        help="Title of the batch load")

    parser.add_argument("-e", "--email", required=True,
                        type=str,
                        help="Email of the batch loader")

    parser.add_argument('-x', '--index-path',
                        type=str,
                        help='JSON file mapping UMDM/UMAM PIDs to file paths')

    # Process command line arguments
    args = parser.parse_args()

    return args


def write_csv(title: str, email: str, manifest_path: Path, objects: Iterable) -> None:
    """ Write objects out to the CSV manifest file. """

    # Get column counts
    max_other_identifier = 1
    max_creator = 1
    max_contributor = 1
    max_publisher = 1
    max_genre = 1
    max_related_item = 1
    max_geographic_subject = 1
    max_topical_subject = 1
    max_temporal_subject = 1
    max_note = 1
    max_file = 1
    max_language = 1

    for obj in objects:
        max_other_identifier = max(len(obj.other_identifier), max_other_identifier)
        max_creator = max(len(obj.creator), max_creator)
        max_contributor = max(len(obj.contributor), max_contributor)
        max_publisher = max(len(obj.publisher), max_publisher)
        max_genre = max(len(obj.genre), max_genre)
        max_related_item = max(len(obj.related_item), max_related_item)
        max_geographic_subject = max(len(obj.geographic_subject), max_geographic_subject)
        max_topical_subject = max(len(obj.topical_subject), max_topical_subject)
        max_temporal_subject = max(len(obj.temporal_subject), max_temporal_subject)
        max_note = max(len(obj.note), max_note)
        max_file = max(len(obj.file), max_file)
        max_language = max(len(obj.language), max_language)

    # Build the headers
    headers = \
        ["Bibliographic ID Label", "Bibliographic ID"] \
        + ["Other Identifier Type", "Other Identifier"] * max_other_identifier \
        + ["Handle"] \
        + ["Title"] \
        + ["Creator"] * max_creator \
        + ["Contributor"] * max_contributor \
        + ["Genre"] * max_genre \
        + ["Publisher"] * max_publisher \
        + ["Date Created", "Date Issued", "Abstract"] \
        + ["Language"] * max_language \
        + ["Physical Description"] \
        + ["Related Item Label", "Related Item URL"] * max_related_item \
        + ["Topical Subject"] * max_topical_subject \
        + ["Geographic Subject"] * max_geographic_subject \
        + ["Temporal Subject"] * max_temporal_subject \
        + ["Terms of Use", "Table of Contents"] \
        + ["Note Type", "Note"] * max_note \
        + ["Publish", "Hidden"] \
        + ["File", "Label"] * max_file

    # Write the output CSV file
    with manifest_path.open(mode='w', newline='') as manifest_file:
        manifest_csv = writer(manifest_file)

        # Write the special first row with batch information
        manifest_csv.writerow([title, email] + [""] * (len(headers) - 2))

        # Write the header row
        manifest_csv.writerow(headers)

        # Write each object row
        for obj in objects:
            row = [
                # "Bibliographic ID Label", "Bibliographic ID"
                obj.bib_id_label,
                obj.bib_id,

                # "Other Identifier Type", Other Identifier"
                *multicolumn(obj.other_identifier, 2, max_other_identifier),

                # "Handle"
                obj.handle,

                # "Title"
                obj.title,

                # "Creator"
                *multicolumn(obj.creator, 1, max_creator),

                # "Contributor"
                *multicolumn(obj.contributor, 1, max_contributor),

                # "Genre"
                *multicolumn(obj.genre, 1, max_genre),

                # "Publisher"
                *multicolumn(obj.publisher, 1, max_publisher),

                # "Date Created", "Date Issued", "Abstract"
                obj.date_created,
                obj.date_issued,
                obj.abstract,

                # "Language"
                *multicolumn(obj.language, 1, max_language),

                # "Physical Description"
                obj.physical_description,

                # "Related Item Label", "Related Item URL"
                *multicolumn(obj.related_item, 2, max_related_item),

                # "Topical Subject"
                *multicolumn(obj.topical_subject, 1, max_topical_subject),

                # "Geographic Subject"
                *multicolumn(obj.geographic_subject, 1, max_geographic_subject),

                # "Temporal Subject"
                *multicolumn(obj.temporal_subject, 1, max_temporal_subject),

                # "Terms of Use", "Table of Contents"
                obj.terms_of_use,
                obj.table_of_contents,

                # "Note Type", "Note"
                *multicolumn(obj.note, 2, max_note),

                # "Publish", "Hidden"
                obj.publish,
                obj.hidden,

                # "File", "Label"
                *multicolumn(obj.file, 2, max_file)
            ]

            # Write the row
            manifest_csv.writerow(row)


def get_text(nodelist: Iterable[Union[Element, Text]]) -> str:
    """Extract text from an XML node list."""
    return ''.join(node.data.strip().replace('\n', '') for node in nodelist if node.nodeType == node.TEXT_NODE)


def multicolumn(values: list, size: int, max_count: int) -> list:
    """
    Format multiple values, taking into account multi-column values.

    :param values: list of values
    :param size: number of columns for each value
    :param max_count: total number of values to allocate space for
    :return: list of columns
    """

    columns = []
    for i in range(0, max_count):
        if i < len(values):
            if size == 1:
                columns.append(values[i])
            else:
                columns.extend(values[i])
        else:
            columns.extend([''] * size)

    return columns


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
                obj.handle = record['handle']
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

    write_csv(args.title, args.email, manifest_path, objects)


if __name__ == '__main__':
    # Run the conversion
    main(process_args())
