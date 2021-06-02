# Migration Utilities 

A framework to support migration of data from Fedora 3 to Fedora 6 repositories. This version of
migration-utils has been adapted for UMD Libraries use to extract Fedora 2 FOXML objects to an
intermediate format, then convert to a format suitable for loading into Avalon or Archelon. The
original README.md is available at [README-orig.md](README-orig.md).

## Components

*target-dir* is a parameter used by the following applications which refers to an input/output directory for their
operations, not to be confused with the Maven output directory containing migration-utils-*-driver.jar.

All JSON files are in a compact format; each object is one complete document on a single line

[org.fcrepo.migration.PicocliMigratorFedora2](src/main/java/org/fcrepo/migration/PicocliMigratorFedora2.java), which is invoked with --action=info to produce an info.json file containing summary information for the FOXML objects.  At this point the UMDM and UMAM objects have not been linked.

* Input: fedora *objects* and *datastreams* directories; optional list of pids, otherwise all objects
* Output: info.json file with summary information for selected FOXML objects.

[scripts/filter.py](scripts/filter.py) - Filter Fedora objects for export (by collection, status, etc) and link UMDM with their related UMAM objects.

* Input - info.json format file
* Output - export.json format file, similar to info.json file but filtered for matching UMDM objects with their hasPart UMAM objects listed under the 'hasPart' key in the UMDM object

[org.fcrepo.migration.PicocliMigratorFedora2](src/main/java/org/fcrepo/migration/PicocliMigratorFedora2.java), which is invoked with --action=export to extract FOXML objects and datastreams.

* Input: export.json format file; fedora *objects* and *datastreams* directories
* Output: export.csv file with summary information for selected FOXML objects; each UMDM and UMAM has its own row.  Datastreams are also exported to directories *target-dir*/umd_XXX for each parent UMDM object.

[scripts/avalon.py](scripts/avalon.py) - generate batch_manifest.csv which is ready for batch load into Avalon

* Input: export.csv and exported objects and datastreams
* Output: Avalon formatted batch_manifest.csv

## Building

The migration-utils Java software is built with [Maven 3](https://maven.apache.org) and requires Java 11 and Maven 3.1+.

```bash
mvn clean install -DskipTests=true -Dcheckstyle.skip
```

You will need python 3.8+ to use the Python scripts in the scripts folder.

## Example

```bash
# Extract summary information about all FOXML objects.
#
# Creates export/info.json
java -jar target/migration-utils-*-driver.jar \
    --action=info \
    --objects-dir=objects \
    --datastreams-dir=datastreams \
    --target-dir=export

# Filter for UMDM objects which are in the Films@UM collection, are marked Complete or Private,
# and are UMD_VIDEO. Also merges UMAM objects under their "parent" UMDM object via the
# hasPart relationship.
#
# Creates export/filter.json
scripts/filter.py \
    --infile=export/info.json \
    --outfile=export/filter.json \
    --collection=umd:1158 \
    --status='Complete,Private' \
    --type=UMD_VIDEO

# Export objects from objects and datastreams folders into the export folder, with summary
# information in export.csv.
#
# Creates export/export.csv and export/umd_XXX directories for each UMDM.
java -jar target/migration-utils-*-driver.jar \
    --action=export \
    --objects-dir=objects \
    --datastreams-dir=datastreams \
    --filter-json=export/filter.json \
    --target-dir=export

# Use the contents of the export directory and the export.csv file to generate
# batch_manifest.csv for import into Avalon.
#
# Creates export/batch_manifest.csv
scripts/avalon.py \
     --title='Films@UM Migration' \
     --email='wallberg@umd.edu' \
     --target-dir=export

```
