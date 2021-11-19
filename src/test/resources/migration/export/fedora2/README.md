# migration/export/fedora2

## Introduction

This subdirectory contains files for testing the "export" action via JUnit.

## inputs

The "inputs" subdirectory contains the files that are used as inputs for the
"export" action.

These inputs were taken from the `libdpiprocessing.lib.umd.edu` server.

The `inputs/filter.json` file was taken from the
`/processing/processing/fedora2/exports/all` directory and simplified to only a
handful of entries.

The `inputs/objects` directory contains a the object files associated with the
entries in the "filter.json" file.

## expected

The "expected" subdirectory contains the excepted output from the "export"
action.

The `export.json` file was taken from the
`/processing/processing/fedora2/exports/all` directory and simplified to the handful
of entries actually exported.

The associated datastream folders were downloaded from the
`/processing/processing/fedora2/exports/all` directory.
