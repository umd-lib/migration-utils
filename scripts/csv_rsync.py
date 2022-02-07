#!/usr/bin/env python3

# Performs an "rsync" using a CSV file for th esource and destination file
# locations.
#
# The CSV file must consist of:
#   A header row (with two entries). The actual entries are ignored.
#   Comma-separated rows where the first entry is the relative location of the
#   source file, and the second entry is the relative location of the
#   destination file.

import csv
import os
import subprocess

from argparse import ArgumentParser, Namespace
from pathlib import PurePath


def process_args() -> Namespace:
    """ Process command line arguments. """

    # Setup command line arguments
    parser = ArgumentParser()

    parser.add_argument("-s", "--source-dir-prefix", required=True,
                        type=str,
                        help="Absolute directory prefix for source files")

    parser.add_argument("-d", "--dest-dir-prefix", required=True,
                        type=str,
                        help="Absolute directory prefix for source files")

    parser.add_argument("-i", "--input-file", required=True,
                        type=str,
                        help="The CSV file containing the relative source and destionation paths")

    # Process command line arguments
    args = parser.parse_args()

    return args


def main(args: Namespace) -> None:
    """Performs the rsync"""
    csv_file = args.input_file
    source_dir_prefix = args.source_dir_prefix
    dest_dir_prefix = args.dest_dir_prefix

    with open(csv_file, mode='r', encoding='UTF-8') as infile:
        reader = csv.reader(infile)
        next(reader)  # skip header row

        for row in reader:
            source_relative = row[0]
            dest_relative = row[1]

            absolute_source_path_with_filename = PurePath(source_dir_prefix, source_relative)
            absolute_dest_path_with_filename = PurePath(dest_dir_prefix, dest_relative)

            absolute_dest_path = os.path.dirname(absolute_dest_path_with_filename)
            if not os.path.isdir(absolute_dest_path):
                os.makedirs(absolute_dest_path)

            print("----")
            print(f"Syncing '{absolute_source_path_with_filename}' to '{absolute_dest_path_with_filename}'")
            subprocess.call(["rsync", '-avr', absolute_source_path_with_filename, absolute_dest_path_with_filename])


if __name__ == '__main__':
    main(process_args())
