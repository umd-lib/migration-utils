#!/usr/bin/env python3

import json
import sys
from urllib.parse import urlparse

# Get list of duplicate pids

dups = {}

with open(sys.argv[1], 'r') as pids:
    for pid in pids:
        dups[pid.strip()] = []

print(f'Looking for {len(dups)} duplicate pids', file=sys.stderr)

# Read JSON records, looking for matching pids
# Store their FOXML location and image location
for line in sys.stdin:

    try:
        record = json.loads(line)

        pid = record['pid']

        if pid in dups:
            foxml = record['foxml']

            if 'ds' in record:
                ds = record['ds']

                if 'image' in ds:
                    image = ds['image']
                    dups[pid].append(('umam', foxml, image['location']))
                elif 'umdm' in ds:
                    umdm = ds['umdm']
                    dups[pid].append(('umdm', foxml, umdm['umdm_title']))

    except Exception as e:
        print(f'{type(e)}: {e}')
        print(line)

# Read through the pids
for pid, foxml_list in dups.items():
    if len(foxml_list) != 2:
        print(f"pid {pid} does not have 2 entries: {foxml_list}", file=sys.stderr)
    else:
        # if type == 'umdm':
        #     for type, foxml, text in foxml_list:
        #         print(type, pid, foxml, text)

        if foxml_list[0][0] == 'umam':
            local_url = None
            local_foxml = None
            fcrepo_url = None
            fcrepo_foxml = None

            for type, foxml, location in foxml_list:
                url = urlparse(location)
                if url.hostname == 'fcrepo.lib.umd.edu':
                    fcrepo_url = url
                    fcrepo_foxml = foxml
                elif url.hostname == 'local.fedora.server':
                    local_url = url
                    local_foxml = foxml
                else:
                    raise Exception(f"Unexpected URL {url.hostname=} for {pid=}, {foxml=}")

            if local_url is None:
                raise Exception(f"Missing local_url for {pid=}")
            elif fcrepo_url is None:
                raise Exception(f"Missing fcrepo_url for {pid=}")
            else:
                print(f"mv {fcrepo_foxml} {local_foxml}")
