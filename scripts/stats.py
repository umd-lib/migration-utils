#!/usr/bin/env python3

import json
import sys
from collections import defaultdict

# Some basic stats about the Fedora 2 FOXML objects in streaming
# JSON format

# Setup the counters
count = defaultdict(int)

count['collection'] = defaultdict(int)

count['rels'] = defaultdict(int)

for doType in ['none', 'umdm', 'umam']:
    count[doType] = defaultdict(int)
    count[doType]['type'] = defaultdict(int)
    count[doType]['status'] = defaultdict(int)

# Map collection pid to title
collections = {}

# Collect stats from each object
for line in sys.stdin:
    count['total'] += 1

    try:
        record = json.loads(line)

        pid = record['pid']
        is_collection = False

        if 'ds' in record:
            ds = record['ds']

            if not ('doInfo' in ds or 'amInfo' in ds):
                count['none']['total'] += 1

            if 'doInfo' in ds:
                do = ds['doInfo']
                count['umdm']['total'] += 1

                if 'type' in do:
                    count['umdm']['type'][do['type']] += 1

                    if do['type'] == "UMD_COLLECTION":
                        is_collection = True

                if 'status' in do:
                    count['umdm']['status'][do['status']] += 1

            if 'amInfo' in ds:
                do = ds['amInfo']
                count['umam']['total'] += 1

                if 'type' in do:
                    count['umam']['type'][do['type']] += 1

                if 'status' in do:
                    count['umam']['status'][do['status']] += 1

            if 'rels-mets' in ds:
                rels = ds['rels-mets']['rels']

                for rel, values in rels.items():
                    for p in values:
                        if rel == 'isMemberOfCollection':
                            count['collection'][p] += 1

                        count['rels'][rel] += 1

            if 'umdm' in ds:
                umdm = ds['umdm']

                if is_collection:
                    if pid not in count['collection']:
                        count['collection'][pid] = 0

                    if 'umdm_title' in umdm:
                        collections[pid] = umdm['umdm_title']
                    else:
                        collections[pid] = "<missing title>"

    except Exception as e:
        print(f'{type(e)}: {e}')
        print(line)

# Print the result
print(f"Total Ojects: {count['total']}")

for doType in ['none', 'umdm', 'umam']:
    print()
    print(doType)
    print(f"  total: {count[doType]['total']}")
    print(f"  type:")
    for type in count[doType]['type']:
        print(f"    {type}: {count[doType]['type'][type]}")
    print(f"  status:")
    for type in count[doType]['status']:
        print(f"    {type}: {count[doType]['status'][type]}")

print()
print("relationships")
for rel, c in count['rels'].items():
    print(f"  {rel}: {c}")

print()
print("isMemberOfCollection")
for pid, c in count['collection'].items():
    if pid in collections:
        title = collections[pid]
    else:
        title = "<missing collection>"

    print(f"  {pid} - {title}: {c}")