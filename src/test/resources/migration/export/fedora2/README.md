# migration/export/fedora2

## Introduction

This subdirectory contains files for testing the "export" action via JUnit.

## inputs

The "inputs" subdirectory contains the files that are used as inputs into the
"export" action.

These inputs were taken from the `/processing/processing/fedora2` of the
`libdpiprocessing.lib.umd.edu` server.


The `filter.json` file was taken from the
`/processing/processing/fedora2/exports/all` directory and simplified to only a
handful of entries.

The "object" files associated with the entries in the `filter.json` file were
then places in the `objects` subdirectory.

## expected

The "expected" subdirectory contains the excepted output from the "export"
action.

The `export.json` file was taken from the
`/processing/processing/fedora2/exports/all` directory and simplified to the handful
of entries actually exported.

The associated datastream folders were also downloaded from the
`/processing/processing/fedora2/exports/all` directory.
