#!/usr/bin/env python3

import csv
from argparse import ArgumentParser, FileType
from pathlib import Path
from xml.dom.minidom import parse

# Convert Fedora exported objects to Avalon input format.
#
# Input - json info file with flat list of all objects
#
# Output - json info file which is filtered for matching UMDM objects and
#          their hasPart UMAM objects listed under the 'hasPart' key in the
#          UMDM object

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
        self.other_identifier = [] # (type, value)
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
        self.related_item = [] # (label, url)
        self.geographic_subject = []
        self.topical_subject = []
        self.temporal_subject = []
        self.terms_of_use = ""
        self.table_of_contents = ""
        self.note = [] # (type, value)
        self.publish = "No"
        self.hidden = "No"

        # Offset, Skip Transcoding, Absolute Location, and Date Ingested are
        # not currently supported
        self.file = [] # (file, label)


def process_args():
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

    # Process command line arguments
    args = parser.parse_args()

    return args


def write_csv(args, manifest, objects):
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

    for object in objects:

        max_other_identifier = max(len(object.other_identifier), max_other_identifier)
        max_creator = max(len(object.creator), max_creator)
        max_contributor = max(len(object.contributor), max_contributor)
        max_publisher = max(len(object.publisher), max_publisher)
        max_genre = max(len(object.genre), max_genre)
        max_related_item = max(len(object.related_item), max_related_item)
        max_geographic_subject = max(len(object.geographic_subject), max_geographic_subject)
        max_topical_subject = max(len(object.topical_subject), max_topical_subject)
        max_temporal_subject = max(len(object.temporal_subject), max_temporal_subject)
        max_note = max(len(object.note), max_note)
        max_file = max(len(object.file), max_file)
        max_language = max(len(object.language), max_language)

    # Build the headers
    headers = \
        ["Bibliographic ID Label", "Bibliographic ID"] \
        + ["Other Identifier Type", "Other Identifier"] * max_other_identifier\
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
    with open(manifest, 'w', newline='') as manifest_file:
        manifest_csv = csv.writer(manifest_file)

        row = None

        def add_multi(values, size, max_count):
            """ Write multi-valued columns. """

            # values - list of values
            # size - size of a value:
            #    1 if a string, means one column
            #   >1 if sequence of strings, means multiple columns
            # max_count - total number of values to write

            nonlocal row

            for i in range(0, max_count):
                if i < len(values):
                    if size == 1:
                        row.append(values[i])
                    else:
                        row.extend(values[i])
                else:
                    row.extend([""] * size)

        # Write the special first row with batch information
        manifest_csv.writerow([args.title, args.email] + [""] * (len(headers) - 2))

        # Write the header row
        manifest_csv.writerow(headers)

        # Write each object row
        for object in objects:
            row = []

            # "Bibliographic ID Label", "Bibliographic ID"
            row.append(object.bib_id_label)
            row.append(object.bib_id)

            # "Other Identifier Type", Other Identifier" * max_other_identifier\
            add_multi(object.other_identifier, 2, max_other_identifier)

            # "Title"
            row.append(object.title)

            # "Creator"
            add_multi(object.creator, 1, max_creator)

            # "Contributor"
            add_multi(object.contributor, 1, max_contributor)

            # "Genre" * max_genre \
            add_multi(object.genre, 1, max_genre)

            # "Publisher"
            add_multi(object.publisher, 1, max_publisher)

            # "Date Created", "Date Issued", "Abstract"
            row.append(object.date_created)
            row.append(object.date_issued)
            row.append(object.abstract)

            # "Language"
            add_multi(object.language, 1, max_language)

            # "Physical Description"
            row.append(object.physical_description)

            # "Related Item Label", "Related Item URL"
            add_multi(object.related_item, 2, max_related_item)

            # "Topical Subject"
            add_multi(object.topical_subject, 1, max_topical_subject)

            # "Geographic Subject"
            add_multi(object.geographic_subject, 1, max_geographic_subject)

            # "Temporal Subject"
            add_multi(object.temporal_subject, 1, max_temporal_subject)

            # "Terms of Use", "Table of Contents"
            row.append(object.terms_of_use)
            row.append(object.table_of_contents)

            # "Note Type", "Note"
            add_multi(object.note, 2, max_note)

            # "Publish", "Hidden"
            row.append(object.publish)
            row.append(object.hidden)

            # "File", "Label"
            add_multi(object.file, 2, max_file)

            # Write the row
            manifest_csv.writerow(row)


def get_text(nodelist):
    """ Extract text from an XML node list. """
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data.strip().replace("\n", ""))
    return ''.join(rc)


def process_umdm(location, object):
    """ Gather data from the UMDM xml. """

    doc = parse(str(location / 'umdm.xml'))

    descMeta = doc.documentElement

    centuryDateRange = ""

    for e in descMeta.childNodes:

        # agent
        if e.nodeName == 'agent':
            type = e.getAttribute('type')
            for node in e.childNodes:
                if node.nodeName in ('persName', 'corpName'):
                    text = get_text(node.childNodes)
                    if type == 'contributor':
                        object.contributor.append(text)
                    elif type == 'creator':
                        object.creator.append(text)
                    elif type == 'provider':
                        object.publisher.append(text)

        # covPlace
        elif e.nodeName == 'covPlace':
            for geogName in e.getElementsByTagName('geogName'):
                text = get_text(geogName.childNodes)
                if text != 'not captured':
                    object.geographic_subject.append(text)

        # covTime
        elif e.nodeName == 'covTime':

            for date in e.getElementsByTagName('date'):
                object.date_issued = get_text(date.childNodes)

            for dateRange in e.getElementsByTagName('dateRange'):
                date_from = dateRange.getAttribute('from')
                date_to = dateRange.getAttribute('to')
                object.date_issued = date_from + "/" + date_to

            for century in e.getElementsByTagName('century'):
                text = get_text(century.childNodes)

                # Save the century as date range, in case we need it for the
                # date_issued
                centuryDateRange = text.replace("-", "/")

        # description
        elif e.nodeName == 'description':

            type = e.getAttribute('type')
            text = get_text(e.childNodes)

            if type == 'summary':
                if object.abstract:
                    object.abstract += "; "
                object.abstract += text

            elif type == 'credits':
                object.note.append(('creation/production credits', text))

        # language
        elif e.nodeName == 'language':

            text = get_text(e.childNodes)
            for value in text.split("; "):
                if value in languageMap:
                    value = languageMap[value]
                object.language.append(value)

        # subject
        elif e.nodeName == 'subject':

            type = e.getAttribute('type')
            text = get_text(e.childNodes)

            if type == 'genre':
                object.genre.append(text)

            else:
                object.topical_subject.append(text)

        # culture
        elif e.nodeName == 'culture':
            text = get_text(e.childNodes)
            if text != 'not captured':
                object.topical_subject.append(text + ' Culture')

        # identifier
        elif e.nodeName == 'identifier':

            type = e.getAttribute('type')
            text = get_text(e.childNodes)

            if type == 'oclc':
                object.other_identifier.append(('oclc', text))

            else:
                object.other_identifier.append(('local', text))

        # physDesc
        elif e.nodeName == 'physDesc':

            for node in e.childNodes:
                text = get_text(node.childNodes)

                if node.nodeName in ('color', 'format'):
                    if object.physical_description:
                        object.physical_description += '; '
                    object.physical_description += text

                if node.nodeName in ('extent', 'size'):
                    if object.physical_description:
                        object.physical_description += '; '
                    text += " " + node.getAttribute('units')
                    object.physical_description += text

        # rights
        elif e.nodeName == 'rights':
            if object.terms_of_use:
                object.terms_of_use += '; '
            object.terms_of_use += get_text(e.childNodes)


    # Use century for date_issued, if necessary
    if not object.date_issued and centuryDateRange:
        object.date_issued = centuryDateRange


def main(args):
    """ Main conversion loop. """

    objects = []
    object = None

    target = Path(args.target_dir)

    # Read in objects
    export = target / 'export.csv'
    print(f"Reading input objects from {export}")

    with open(export, "r") as export_file:
        export_csv = csv.reader(export_file)

        for umdm, umam, location, title in export_csv:

            if not umam:
                # Process UMDM, start new object
                object = Object()
                objects.append(object)

                object.title = title

                object.other_identifier.append(("local", umdm))

                process_umdm(target / location, object)

                # object.file.append(("UMDM", location))
                object.file.append(("export/test.mp4", "Test MP4 Video"))
            else:
                # TODO: Process UMAM
                # object.file.append(("UMAM", umam))
                None

    # Write output csv
    manifest = target / 'batch_manifest.csv'
    print(f"Writing output {manifest}")
    print(f"  {len(objects)} objects")

    write_csv(args, manifest, objects)


if __name__ == '__main__':

    # Process command line arguments
    args = process_args()

    # Run the conversion
    main(args)
