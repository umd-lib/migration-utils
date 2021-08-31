#!/usr/bin/env python3

import json
from argparse import ArgumentParser, FileType

# Filter Fedora objects in json info format
#
# Input - json info file with flat list of all objects
#
# Output - json info file which is filtered for matching UMDM objects and
#          their hasPart UMAM objects listed under the 'hasPart' key in the
#          UMDM object


def process_args():
    """ Process command line arguments. """

    # Setup command line arguments
    parser = ArgumentParser()

    parser.add_argument("-i", "--infile", required=True,
                        type=str,
                        help="JSON input file")

    parser.add_argument("-o", "--outfile", required=True,
                        type=FileType('w', encoding='UTF-8'),
                        help="JSON output file")

    parser.add_argument("-c", "--collection", required=False,
                        type=str,
                        help="Comma-separated list of collection pids")

    parser.add_argument("-s", "--status", required=False,
                        default="Complete,Private",
                        type=str,
                        help="Comma-separated list of doInfo.status " +
                             "(default: Complete,Private")

    parser.add_argument("-t", "--type", required=False,
                        type=str, help="Comma-separated list of doInfo.type")

    # Process command line arguments
    args = parser.parse_args()

    if args.collection:
        args.collection = [e.strip() for e in args.collection.split(',')]
        print(f"Filter Collections: {args.collection}")

    if args.status:
        args.status = [e.strip() for e in args.status.split(',')]
        print(f"Filter Status: {args.status}")

    if args.type:
        args.type = [e.strip() for e in args.type.split(',')]
        print(f"Filter Type: {args.type}")

    return args


def match(args, object):
    """ Determine if this is a UMDM matches the filter conditions. """

    # Check if this is a UMDM object
    if 'ds' not in object:
        return False, None
    ds = object['ds']

    if 'doInfo' not in ds:
        return False, None
    doInfo = ds['doInfo']

    # Yes, now get relationships, if they are present
    rels_mets = None
    rels = None
    if 'rels-mets' in ds:
        rels_mets = ds['rels-mets']
        if 'rels' in rels_mets:
            rels = rels_mets['rels']

    # Check the collection filter
    if args.collection:
        if not rels or 'isMemberOfCollection' not in rels:
            return False, None

        is_match = False
        for collection in args.collection:
            if collection in rels['isMemberOfCollection']:
                is_match = True

        if not is_match:
            return False, None

    # Check the status filter
    if args.status:
        if 'status' not in doInfo:
            return False, None

        if doInfo['status'] not in args.status:
            return False, None

    # Check the type filter
    if args.type:
        if 'type' not in doInfo:
            return False, None

        if doInfo['type'] not in args.type:
            return False, None

    # We have a match, return the parts
    if not rels or 'hasPart' not in rels:
        return True, []
    else:
        return True, rels['hasPart']


def main(args):
    """ Main input/output filter. """

    # We make two passes through the input file:
    #  1. Collect all UMDM objects which match the filters
    #  2. Collect all UMAM for the matching UMDM

    umdm = []
    parts = {}
    partsCount = 0

    # Collect all UMDM matching the filters
    print("Finding UMDM")
    with open(args.infile, 'r', encoding='UTF-8') as infile:
        for line in infile:
            object = json.loads(line)

            is_match, has_parts = match(args, object)
            if is_match:
                # Add the title
                title = "<unknown>"
                if ('ds' in object
                    and 'umdm' in object['ds']
                    and 'umdm_title' in object['ds']['umdm']):
                    title = object['ds']['umdm']['umdm_title']
                object['title'] = title

                # Save the UMDM object
                umdm.append(object)

                # Map the UMAM pids to their parent UMDM
                for part in has_parts:
                    parts[part] = object

    print(f"  {len(umdm)}")

    # Collect all UMAM for the matching UMDM
    print("Finding UMAM")
    with open(args.infile, 'r', encoding='UTF-8') as infile:
        for line in infile:
            object = json.loads(line)

            umamPid = object['pid']

            if (umamPid in parts
               and 'ds' in object
               and 'amInfo' in object['ds']):

                # Add the UMAM
                umdmObject = parts[umamPid]

                if 'hasPart' not in umdmObject:
                    umdmObject['hasPart'] = []

                umdmObject['hasPart'].append(object)

                partsCount += 1

    print(f"  {partsCount}")

    # Write out the results
    print("Writing output JSON")
    for object in umdm:
        args.outfile.write(json.dumps(object))
        args.outfile.write("\n")
    args.outfile.close()


if __name__ == '__main__':

    # Process command line arguments
    args = process_args()

    # Run input/output filter
    main(args)
