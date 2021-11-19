# migration/info/fedora2

## Introduction

This subdirectory contains files for testing the Fedora 2 migration
"info" action via JUnit.

## inputs

The "inputs" subdirectory contains the files that are used as inputs for the
"info" action.

These inputs were taken from the `libdpiprocessing.lib.umd.edu` server.

The `inputs/objects` directory contains a sampling of object files from the
`/processing/processing/fedora2/objects/` directory.


The `inputs/datastreams` directory contains datastream folders from the
`/processing/processing/fedora2/exports/all` directory associated with the objects. 


## expected

The "expected" subdirectory contains the excepted output from the "info"
action.

The `info.json` file was taken from the `/processing/processing/fedora2/exports`
directory and simplified to the handful of entries actually used.
