#!/usr/bin/env python3

import sys
from csv import DictReader, writer
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Union
import html
import logging
from argparse import ArgumentParser, Namespace

import yaml

# Convert MD Map Collection records exported from Hippo CMS to Archelon
# input format.
#
# 1. mkdir maryland-maps
#
# 2. In the Hippo console, export path=/content/gallery/public/maryland-maps
# to maryland-maps/{maryland-maps-gallery.yaml, maryland-maps}
#
# 3. In the Hippo console, export path=/content/documents/digital/maryland-maps
# to maryland-maps/maryland-maps.yaml
#
# 4. Create maryland-maps/batch_manifest.csv
# python3 scripts/maryland-maps.py --target-dir=maryland-maps

logging.basicConfig(level=logging.INFO, format='%(message)s')


def traverse_metadata(e, manifest_csv):
    """ Traverse the metadata JSON document. """
    if isinstance(e, dict):

        is_map = (
            "jcr:primaryType" in e
            and e["jcr:primaryType"] == "mdmap:map"
            and "hippostd:state" in e
            and e["hippostd:state"] == "published"
            and "hippo:availability" in e
            and "live" in e["hippo:availability"]
        )

        if is_map:
            handle_map(e, manifest_csv)
        else:
            for v in e.values():
                traverse_metadata(v, manifest_csv)


def handle_text(e, key):
    """ Handle a text field. """
    value = ""
    if key in e:
        value = e[key]
    return value


def handle_html(e, key):
    """ Handle an HTML field. """
    value = ""
    if key in e:
        value = e[key]["hippostd:content"] \
                .replace('\n', '') \
                .replace('\t', '')
    return value


def handle_url(e, key):
    """ Handle a URL field. """
    url = ""
    if key in e:
        url = e[key]["public:url"]
    return url


def handle_list(e, key):
    """ Handle an array field. """
    if key in e:
        return e[key]
    else:
        return []


def handle_map(e, manifest_csv):
    """ Handle a single map. """

    global rowcount, writer

    row = []
    headers = []

    headers.append("Title")
    row.append(html.unescape(handle_text(e, "mdmap:title")))

    headers.append("CallNumber")
    row.append(handle_text(e, "mdmap:call_number"))

    headers.append("Digitized")
    row.append(handle_text(e, "mdmap:digitized"))

    headers.append("Cartographer")
    row.append(handle_text(e, "mdmap:cartographer"))

    headers.append("StartYear")
    row.append(handle_text(e, "mdmap:start_year"))

    headers.append("EndYear")
    row.append(handle_text(e, "mdmap:end_year"))

    headers.append("MapType")
    row.append(handle_text(e, "mdmap:map_type"))

    headers.append("Notes")
    row.append(handle_text(e, "mdmap:notes"))

    headers.append("NumSheets")
    row.append(handle_text(e, "mdmap:num_sheets"))

    headers.append("Publisher")
    row.append(handle_text(e, "mdmap:publisher"))

    headers.append("Region")
    row.append(handle_text(e, "mdmap:region"))

    headers.append("Railroad")
    row.append(handle_text(e, "mdmap:railroad"))

    headers.append("Waterway")
    row.append(handle_text(e, "mdmap:waterway"))

    headers.append("Cities")
    row.append('; '.join(handle_list(e, "mdmap:cities")))

    headers.append("Counties")
    row.append('; '.join(handle_list(e, "mdmap:counties")))

    headers.append("Regions")
    row.append('; '.join(handle_list(e, "mdmap:regionis")))

    headers.append("States")
    row.append('; '.join(handle_list(e, "mdmap:states")))

    headers.append("FedoraLink")
    url = handle_url(e, "/mdmap:fedora")

    row.append(url)

    if rowcount == 0:
        manifest_csv.writerow(headers)

    manifest_csv.writerow(row)
    rowcount += 1


def process_args() -> Namespace:
    """ Process command line arguments. """

    # Setup command line arguments
    parser = ArgumentParser()

    parser.add_argument("-a", "--target-dir", required=True,
                        type=str,
                        help="Target maryland-maps directory (input and output files)")

    # Process command line arguments
    args = parser.parse_args()

    return args


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

    # Target Directory
    target = Path(args.target_dir)

    # Load mapping document (assumes cwd is the migration-utils directory)
    mapping = load_mapping()

    # Read in exported metadata records (YAML)
    export_path = target / 'maryland-maps.yaml'
    logging.info(f"Reading exported records from {export_path}")

    with export_path.open(mode='r') as export_file:
        doc = yaml.safe_load(export_file)

    # Write batch_manifest.csv
    manifest_path = target / 'batch_manifest.csv'
    logging.info(f"Writing output {manifest_path}")

    with manifest_path.open(mode='w') as manifest_file:
        manifest_csv = writer(manifest_file)
        traverse_metadata(doc, manifest_csv)

    logging.info(f"  {rowcount} records")


rowcount = 0


if __name__ == '__main__':
    # Run the conversion
    main(process_args())

