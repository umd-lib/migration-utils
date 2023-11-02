#!/usr/bin/env python3

import json
import csv

# Sample filter.json records for testing with archelon.py
#
# Input files: export/{info.json, filter.json, export.csv}
# Output files: sample/{info.json, filter.json, export.csv}

N = 500

count = {}
pids = set()

# Read all input records
with open("export/filter.json", mode='r') as export_filter_file:

    # Write selected sample records
    with open("sample/filter.json", mode='w') as sample_filter_file:
        for line in export_filter_file:

            record = json.loads(line)

            # Extract data from the record
            try:
                ds = record['ds']
                status = ds['doInfo']['status']
                if status != 'Complete':
                    continue

                pid = record['pid']
                rtype = ds['doInfo']['type']
                cols = ds['rels-mets']['rels']['isMemberOfCollection']

            except Exception:
                continue

            # Determine if this record should be included in the sample set
            include = False
            for col in cols:

                # Selection key: type and collection
                key = (rtype, col)

                if key not in count:
                    print(key)
                    count[key] = 0

                if count[key] % N == 0:
                    include = True

                count[key] += 1

            if include:
                # Include in the sample set
                pids.add(pid)
                for umam in record['hasPart']:
                    pids.add(umam['pid'])

                sample_filter_file.write(line)

# Create export.csv with all matching pids
with open("export/export.csv", mode='r') as export_export_file:
    export_csv = csv.DictReader(export_export_file)

    with open("sample/export.csv", 'w') as sample_export_file:
        sample_csv = csv.DictWriter(sample_export_file, export_csv.fieldnames)
        sample_csv.writeheader()

        for record in export_csv:
            if record['umdm'] in pids:
                sample_csv.writerow(record)

# Create info.json with all matching pids
with open("export/info.json", mode='r') as export_info_file:

    with open("sample/info.json", mode='w') as sample_info_file:

        for line in export_info_file:
            record = json.loads(line)

            if record['pid'] in pids:
                sample_info_file.write(line)
