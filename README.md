# programs using voip.ms API
These programs use the API of the voip.ms phone service

## Description
This set of programs uses a config file to supply authentication information to
use the API of the VOIP service at voip.ms.  There is an included example config
file that needs to have the userid and password changed, and the file installed
into your HOME directory.  You can tweak the config file to set which fields 
you are interested in, the order and size of the fields, and the titles.

## programs

* black-list
* get-cdrs
* get-did-info
* send-sms-message

## Installation

To install from downloading from Github:

    make install        # install programs
    make man            # install man-pages

To install from the Python Package Index (PyPI):

    pip install voip-ms-moxad

## Example usages
This will print CDR records from November 11 to November 22, in reverse order
such that records will be numbered from oldest to newest:

    % get-cdrs --from 2017-11-15 --to 2017-11-22 --reverse

This will print last months CDR records and the cost for account 'home':

    % get-cdrs --last-month --cost --account home

This will print the filter rules along with filter IDs to make changes to an existing rule:

    % black-list

This will set a filter rule giving a Busy signal instead of the default NoService message:

    % black-list --note 'Bad Evil Dudes' --busy  416-555-1212 

This will change the previous filter rule from Busy to Hangup instead:

    % black-list --hangup --filterid 12345

This will send a SMS message to barney (an alias set up in the config file):

    % send-sms-message -r barney Time for a beer

This will print all data about each DID, with the phone-number preceded by the (sub)account-name

    % get-did-info --account --all

There is a help option with each program.  For eg:

    % get-cdrs --help

    usage: get-cdrs [options]*
        [-a|--account str]     (account name)
        [-c|--config file]     (config-file (default=/home/rj/.voip-ms.conf)
        [-d|--debug]           (debugging output)
        [-f|--from date]       (YYYY-MM-DD - FROM date)
        [-h|--help]            (help)
        [-p|--padding num]     (padding between output fields (default=3)
        [-q|--quiet]           (quiet.  No headings and titles)
        [-r|--reverse]         (reverse date order of CDR output)
        [-s|--sheldon]
        [-t|--to date]         (YYYY-MM-DD - TO date)
        [-w|--timeout  num]    (default=120)
        [-C|--cost]            (total up costs and duration of CDRs)
        [-L|--last-month]      (want CDR records for LAST month)
        [-T|--this-month]      (want CDR records for THIS month)
        [-V|--version]         (print version of this program)    


## API setup.
You need to set up your voip.ms service to permit access to it.  This includes
providing which IP addresses can use it.  Please see the following URL for instructions:

    https://voip.ms/m/api.php
