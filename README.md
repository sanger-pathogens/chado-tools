# chado-tools

Python3 command line script providing various tools for accessing CHADO databases

[![Build Status](https://travis-ci.org/sanger-pathogens/chado-tools.svg?branch=master)](https://travis-ci.org/sanger-pathogens/chado-tools)

## Prerequisites

* PostgreSQL
* Python 3.6 or higher

## Installation

Download the latest release from this github repository, or clone the repository.

Change the file with [default connection settings](pychado/data/defaultDatabase.yml) such that it contains an existing PostgreSQL database to which you can connect.
Note: This database is only used for housekeeping purposes, it will never be changed or removed by `chado-tools`. You can thus simply use one of the built-in PostgreSQL databases, such as `template0`. 

Then run the tests:

    python3 setup.py test

If the tests all pass, install:

    python3 setup.py install

## Usage

The installation will put a single script called `chado` in your PATH.
The usage is:

    chado <command> [options]

* To list the available commands and brief descriptions, just run `chado -h` or `chado --help`.
* To display the version of the program, type `chado -v` or `chado --version`.
* Use `chado <command> -h` or `chado <command> --help` to get a detailed description and the usage of that command.

## Available commands

| Command               | Description                                                          |
|-----------------------|----------------------------------------------------------------------|
| connect               | connect to a CHADO database for an interactive session               |
| create                | create a new instance of the CHADO schema                            |
| dump                  | dump a CHADO database into an archive file                           |
| restore               | restore a CHADO database from an archive file                        |
| import                | import data from a text file into a table of a CHADO database        |
| export                | export data from a table of a CHADO database into a text file        |

## Examples

Create a new database called `insects` according to the current GMOD schema:

    chado create insects
    
Dump this database into an archive called `insects.dump`:

    chado dump insects insects.dump

## Note

Unless explicitly specified by the flag `-c`, all commands employ the [default connection settings](pychado/data/defaultDatabase.yml) also used to run the tests.
