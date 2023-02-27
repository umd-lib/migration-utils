#!/usr/bin/env python3

from csv import DictReader, reader, writer
import json
import re

from pathlib import Path
import requests

# Lookup names in VIAF and record the matching URIs.
# Process is restartable; it will read from the output CSV
# file first to determine which names it has already processed.

def normalize(s):
    ''' Normalize to a searchable form. '''
    s = re.sub(r'\s+', '', s)
    s = re.sub(r'[\[\]・･,;.\-?]',' ', s)
    s = re.sub(r'\(.*?\)','',s)
    return s

manifest_file_name = "export/batch_manifest.csv"
csv_file_name = "export/lookup-viaf.csv"

viaf_base_url = "https://viaf.org/viaf"
viaf_search_params = {
    'sortKeys': 'holdingscount',
    'recordSchema': 'BriefVIAF',
    'maximumRecords': '3',
    'startRecord': '1',
    'httpAccept': 'application/json',
}

already_searched = set()

# Read the CSV as input
with open(csv_file_name, "r") as in_file:
    csv_reader = reader(in_file)
    for row in csv_reader:
        # Record this creator as already searched
        already_searched.add(row[0])

# Open the CSV as output for write with append
with open(csv_file_name, "a") as out_file:
    csv_writer = writer(out_file)

    # Read each row in the manifest file
    with open(manifest_file_name, "r") as manifest_file:
        creator_reader = DictReader(manifest_file)
        for row in creator_reader:
            creators = row['Creator']
            for creator in creators.split('|'):

                # Check if we've already searched this creator
                if creator not in already_searched:

                    # Normalize the creator for the VIAF search
                    creator_norm = normalize(creator)
                    if creator_norm:

                        out_row = [creator]

                        # Search in VIAF
                        print(f'VIAF lookup: {creator}')

                        viaf_search_params['query'] = f'local.personalNames all "{creator_norm}"'

                        response = requests.get(f'{viaf_base_url}/search', params=viaf_search_params)
                        if response.ok:

                            result = json.loads(response.text)['searchRetrieveResponse']
                            out_row.append(result['numberOfRecords'])

                            if 'records' in result:
                                for record in result['records']:
                                    id = record['record']['recordData']['viafID']['#text']
                                    out_row.append(f'{viaf_base_url}/{id}')

                        csv_writer.writerow(out_row)

                        # Clear the buffer by flushing, to ensure we don't lose any entries
                        out_file.flush()

                        already_searched.add(creator)

