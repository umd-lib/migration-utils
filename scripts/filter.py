#!/usr/bin/env python3

import json
import logging
import random
from argparse import ArgumentParser, FileType
from tempfile import TemporaryFile
from xml.etree import ElementTree

import requests

# Filter Fedora objects in json info format
#
# Input - json info file with flat list of all objects
#
# Output - json info file which is filtered for matching UMDM objects and
#          their hasPart UMAM objects listed under the 'hasPart' key in the
#          UMDM object

logging.basicConfig(level=logging.INFO, format='%(message)s')


class DelimitedList:
    def __init__(self, delimiter=','):
        self.delimiter = delimiter

    def __call__(self, arg):
        return arg.split(self.delimiter)


def process_args():
    """ Process command line arguments. """

    # Setup command line arguments
    parser = ArgumentParser()

    parser.add_argument("-i", "--infile", required=True,
                        type=FileType(mode='r', encoding='UTF-8'),
                        help="JSON input file")

    parser.add_argument("-o", "--outfile", required=True,
                        type=FileType(mode='w', encoding='UTF-8'),
                        help="JSON output file")

    parser.add_argument("-c", "--collection",
                        type=DelimitedList(),
                        default=[],
                        help="Comma-separated list of collection pids")

    parser.add_argument("-s", "--status",
                        type=DelimitedList(),
                        default=['Complete', 'Private'],
                        help=(
                            "Comma-separated list of doInfo.status "
                            "(default: Complete,Private)"
                        ))

    parser.add_argument("-t", "--type",
                        type=DelimitedList(),
                        default=[],
                        help="Comma-separated list of doInfo.type")

    parser.add_argument("-r", "--random",
                        type=int,
                        default=0,
                        help=(
                            "Pseudo-randomly select records at a rate of 1 out of RANDOM"
                            "(default: every record)"
                        ))

    # Process command line arguments
    return parser.parse_args()


def is_umdm(obj):
    return hasitem_chain(obj, 'ds', 'doInfo')


def is_umam(obj):
    return hasitem_chain(obj, 'ds', 'amInfo')


def setup_filters(args):
    """
    Create a list of filter functions to run.

    :param args: Command-line arguments to this script
    :return: List of functions
    """
    filters = []

    if args.collection:
        logging.info(f"Filter Collections: {args.collection}")

        def filter_collections(obj):
            rels = getitem_chain(obj, 'ds', 'rels-mets', 'rels', default={})
            return 'isMemberOfCollection' in rels \
                   and any(collection in rels['isMemberOfCollection'] for collection in args.collection)

        filters.append(filter_collections)

    if args.status:
        logging.info(f"Filter Status: {args.status}")

        def filter_status(obj):
            do_info = getitem_chain(obj, 'ds', 'doInfo', default={})
            return 'status' in do_info and do_info['status'] in args.status

        filters.append(filter_status)

    if args.type:
        logging.info(f"Filter Type: {args.type}")

        def filter_type(obj):
            do_info = getitem_chain(obj, 'ds', 'doInfo', default={})
            return 'type' in do_info and do_info['type'] in args.type

        filters.append(filter_type)

    if args.random:
        logging.info(f"Filter Random: 1 out of {args.random}")

        random.seed(0)

        def filter_random(obj):
            return random.randrange(args.random) == 0

        filters.append(filter_random)


    return filters


def getitem_chain(obj, *keys, default=None):
    """
    Inspired by the "dig" method in Ruby hashes.::

        x = {'foo': {'bar': {'baz': 1719}}}

        getitem_chain(x, 'foo', 'bar', 'baz', default=2304)
            # => 1719

        getitem_chain(x, 'a', 'b', 'c', default=2304)
            # => 2304

        getitem_chain(x, 'a', 'b', 'c')
            # => None

    :param obj:
    :param keys:
    :param default:
    :return:
    """
    for key in keys:
        if key not in obj:
            return default
        obj = obj[key]
    return obj


def hasitem_chain(obj, *keys):
    """
    Inspired by the "dig" method in Ruby hashes.::

        x = {'foo': {'bar': {'baz': 1719}}}

        hasitem_chain(x, 'foo', 'bar', 'baz')  # => True

        hasitem_chain(x, 'a', 'b', 'c')        # => False

    :param obj:
    :param keys:
    :return:
    """
    for key in keys:
        if key not in obj:
            return False
        obj = obj[key]
    return True


def get_handle(pid):
    logging.debug(f'Looking up handle for {pid}')
    response = requests.get('https://fedora.lib.umd.edu/handle/', params={'action': 'lookup', 'pid': pid})
    if not response.ok:
        logging.warning(f'No handle found for {pid}')
        return ''

    root = ElementTree.fromstring(response.text)
    handle_element = root.find('.//handle')
    if handle_element is None:
        logging.warning(f'No handle found for {pid}')
        return ''

    return handle_element.text


def main(args):
    """
    Main input/output filter.

    Makes two passes through the input file:

    1. Collect all UMDM objects which match the filters
    2. Collect all UMAM for the matching UMDM

    Then writes to the output file.
    """

    # matching UMDM objects
    umdm = []
    # mapping from UMAM pid => UMDM
    umdm_for_umam_pid = {}
    parts_count = 0

    with TemporaryFile(mode='w+') as umam_list:
        # Collect all UMDM matching the filters
        filters = setup_filters(args)
        logging.info("Finding UMDM")
        for line in args.infile:
            obj = json.loads(line)

            # copy any UMAM objects to the temp file
            if is_umam(obj):
                umam_list.write(line)

            if is_umdm(obj) and all(check(obj) for check in filters):
                # Map the UMAM pids to their parent UMDM
                umam_pids = getitem_chain(obj, 'ds', 'rels-mets', 'rels', 'hasPart', default=[])
                umdm_for_umam_pid.update({pid: obj for pid in umam_pids})

                # Add the title
                obj['title'] = getitem_chain(obj, 'ds', 'umdm', 'umdm_title', default='<unknown>')

                # Add the handle
                obj['handle'] = get_handle(obj['pid'])

                # Save the UMDM object
                umdm.append(obj)

        logging.info(f"  found {len(umdm)}")

        # Collect all UMAM for the matching UMDM
        logging.info("Finding UMAM")

        # rewind the temp file listing of UMAM objects
        umam_list.seek(0)
        for line in umam_list:
            obj = json.loads(line)
            pid = obj['pid']

            if pid in umdm_for_umam_pid:
                umdm_object = umdm_for_umam_pid[pid]

                if 'hasPart' not in umdm_object:
                    umdm_object['hasPart'] = []

                # Add the UMAM to its parent UMDM
                umdm_object['hasPart'].append(obj)

                parts_count += 1

    logging.info(f"  found {parts_count}")

    # Write out the results
    logging.info("Writing output JSON")
    for obj in umdm:
        args.outfile.write(json.dumps(obj))
        args.outfile.write("\n")


if __name__ == '__main__':
    # Run input/output filter
    main(process_args())
