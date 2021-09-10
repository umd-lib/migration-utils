#!/usr/bin/env python3

import json
import logging
import re
from argparse import ArgumentParser, FileType
from collections import defaultdict
from csv import DictReader


logging.basicConfig(level=logging.INFO, format='%(message)s')

parser = ArgumentParser(
    description=(
        'Read an inventory CSV file, and build an index dictionary JSON file '
        "mapping the UMDM PID to a dictionary mapping that object's UMAM PIDs "
        'to the relative path to the corresponding binary.'
    )
)

parser.add_argument("-i", "--infile", required=True,
                    type=FileType(mode='r', encoding='UTF-8'),
                    help="CSV inventory file")

parser.add_argument("-o", "--outfile", required=True,
                    type=FileType(mode='a', encoding='UTF-8'),
                    help="JSON output file")

args = parser.parse_args()

INVENTORY_FIELDS = [
    'PATH', 'DIRECTORY', 'FILENAME', 'EXTENSION', 'BYTES', 'MTIME', 'MODDATE', 'MD5', 'SHA1', 'SHA256'
]
PIDS_PATTERN = re.compile(r'umd_(\d+)/umd_(\d+)')

index = defaultdict(dict)

reader = DictReader(args.infile)

for line in reader:
    match = PIDS_PATTERN.search(line['DIRECTORY'])
    if match:
        umdm_pid, umam_pid = (f'umd:{pid}' for pid in match.groups())
        index[umdm_pid].update({umam_pid: line['FILENAME']})
        logging.info(f'Added {umam_pid} to {umdm_pid}')

logging.info(f'Writing index to {args.outfile.name}')
args.outfile.write(json.dumps(index) + '\n')
