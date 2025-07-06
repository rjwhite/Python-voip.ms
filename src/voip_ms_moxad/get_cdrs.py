"""
get Call Display Records using voip.ms API

Get CDR (call Display Records) from one or more of your voip.ms
phone lines.

Examples:
    get-cdrs --help
    get-cdrs --this-month --reverse
    get-cdrs --last-month --quiet
    get-cdrs --from 2023-1-1 --to 2023-1-31 --account 1234_alarm
"""

# Copyright 2018 RJ White
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
try:
    import time
    import re

    from config_moxad import config

    from . import __version__
    from . import globals
    from .constants import FROM_DATE_FLAG, TO_DATE_FLAG
    from .functions import *
except ModuleNotFoundError as err:
    sys.stderr.write( "Error: missing module: %s\n" % err )
    sys.exit(1)


# print usage
#
# Arguments:
#   a dictionary containing values for:
#       'config-file'
#       'padding'
#       'timeout'
# Returns:
#   0
# Exceptions:
#   none

def usage( values ):
    print( "usage: {} [options]*".format( globals.progname ))

    config_file = values.get( 'config-file', '?' )
    padding     = values.get( 'padding', '?' )
    timeout     = values.get( 'timeout', '?' )

    options = """\
    [-a|--account str]     (account name)
    [-c|--config file]     (config-file (default={})
    [-d|--debug]           (debugging output)
    [-f|--from date]       (YYYY-MM-DD - FROM date)
    [-h|--help]            (help)
    [-p|--padding num]     (padding between output fields (default={})
    [-q|--quiet]           (quiet.  No headings and titles)
    [-r|--reverse]         (reverse date order of CDR output)
    [-s|--sheldon]
    [-t|--to date]         (YYYY-MM-DD - TO date)
    [-w|--timeout  num]    (default={})
    [-C|--cost]            (total up costs and duration of CDRs)
    [-L|--last-month]      (want CDR records for LAST month)
    [-T|--this-month]      (want CDR records for THIS month)
    [-V|--version]         (print version of this program)\
    """

    print( options.format( config_file, padding, timeout ))
    return(0)


# main program
#
# Arguments:
#   command-line arguments
# Returns:
#   0:  ok
#   1:  not ok
# Exceptions:
#   none

def main( argv=sys.argv ):
    config_file = None

    progname = argv[0]
    if progname == None or progname == "":
        progname = 'get-cdrs'

    globals.progname = progname     # make available to other functions
    globals.debug_flag = False      # used by functions.debug

    # set some defaults
    # These may be over-written by config file values

    defaults = {
        'padding':   4,
        'timeout':   45,
    }

    # values from the command-line will go into values.
    # Then if any keys are found in values, but not in defaults,
    # then the default values will be copied into values as well

    values = {}

    help_flag       = False
    cost_flag       = False
    quiet_flag      = False
    reverse_flag    = False
    last_month_flag = False
    this_month_flag = False

    account_name    = ""
    from_date       = ""
    to_date         = ""
    method          = 'getCDR'

    num_args = len( argv )
    i = 1
    while i < num_args:
        try:
            arg = argv[i]
            if arg == '-c' or arg == '--config':
                i = i + 1 ;     config_file = argv[i]
            elif arg == '-a' or arg == '--account':
                i = i + 1 ;     account_name = argv[i]
            elif arg == '-w' or arg == '--timeout':
                i = i + 1 ;     values[ 'timeout' ] = argv[i]
            elif arg == '-p' or arg == '--padding':
                i = i + 1 ;     values[ 'padding' ] = argv[i]
            elif arg == '-f' or arg == '--from':
                i = i + 1 ;     from_date = argv[i]
            elif arg == '-t' or arg == '--to':
                i = i + 1 ;     to_date = argv[i]
            elif arg == '-d' or arg == '--debug':
                globals.debug_flag = True
            elif arg == '-L' or arg == '--last-month':
                last_month_flag = True
            elif arg == '-T' or arg == '--this-month':
                this_month_flag = True
            elif arg == '-C' or arg == '--cost':
                cost_flag = True
            elif arg == '-r' or arg == '--reverse':
                reverse_flag = True
            elif arg == '-q' or arg == '--quiet':
                quiet_flag = True
            elif arg == '-s' or arg == '--sheldon':
                print( "Bazinga!" )
                return(0)
            elif arg == '-V' or arg == '--version':
                print( "package version: {0}".format( __version__ ))
                print( "config  version: {0}".format( config.__version__ ))
                return(0)
            elif arg == '-h' or arg == '--help':
                help_flag = True
            else:
                err = "{0}: unknown option: {1}\n".format( progname, arg )
                sys.stderr.write( err )
                return(1)
        except IndexError as err:
            err = "{0}: {1}.  Missing argument value to \'{2}\'?\n". \
                format( progname, err, arg )
            sys.stderr.write( err )
            return(1)

        i = i+1


    if last_month_flag == True and this_month_flag == True:
        err = "{0}: Don't use both --last-month and --this-month together\n". \
            format( progname )  
        sys.stderr.write( err )
        return(1)

    year  = time.localtime()[0]
    month = time.localtime()[1]
    day   = time.localtime()[2]

    if last_month_flag or this_month_flag:
        try:
            should_be_empty( from_date, "you already gave a FROM date" )
            should_be_empty( to_date,   "you already gave a TO date" )
        except ShouldBeEmpty_String as e:
            sys.stderr.write( "{0}: {1}\n".format( progname, e ))
            return(1)

        if last_month_flag:
            # point to previous month
            month = month - 1
            if month == 0:
                month = 12
                year = year - 1

        try:
            from_date = format_date( month, year, FROM_DATE_FLAG )
            to_date   = format_date( month, year, TO_DATE_FLAG )
        except (InvalidArgument, InvalidDate) as e:
            sys.stderr.write( "{0}: {1}\n".format( progname, e ))
            return(1)


    # We need 'from' and 'to' dates.  Make it only today if nothing given.

    if from_date == "" or to_date == "":
        month = "{0:02d}".format( month )
        day   = "{0:02d}".format( day )
        today = "{0:s}-{1:s}-{2:s}".format( str(year), str(month), str(day) )
        if from_date == "":
            from_date = today
        if to_date == "":
            to_date = today

    # do some sanity checking on the dates

    dates = {
        "FROM":     from_date,
        "TO":       to_date
    }

    dates_list = list( dates )
    for d in dates_list:
        var = dates[ d ]
        m = re.match( "^\d{2,4}\-\d{1,2}\-\d{1,2}$", var )
        if not m:
            err = "{0:s}: {1:s} date ({2:s}) has an invalid format\n". \
                format( progname, d, var )
            sys.stderr.write( err )
            return(1)
        else:
            dprint( "{0:s} date passed format check".format( d ))

    try:
        if seconds_since_epoch( from_date ) > seconds_since_epoch( to_date ):
            err = "{0:s}: FROM date ({1:s}) is after TO date ({2:s})\n". \
                format( progname, from_date, to_date )
            sys.stderr.write( err )
            return(1)
        else:
            dprint( "FROM date passed being before the TO date" )

    except (ValueError, InvalidDate) as err:
        sys.stderr.write( "{}: {}\n".format( progname, err ))
        return(1)

    # find the config file we really want

    config_file = find_config_file( config_file ) ;
    if not config_file:
        sys.stderr.write( "{0}: could not find a config file\n". \
            format( progname ))
        return(1) ;
    dprint( "using config file: " + config_file )

    # collect our data from the config file

    config.Config.set_debug( globals.debug_flag )

    # no definitions file.  Our type info is all in our config file.
    try:
        conf = config.Config( config_file, '', AcceptUndefinedKeywords=True )
    except Exception as err:
        sys.stderr.write( "{0}: {1}\n".format( progname, err ))
        return(1)

    dprint( "Config data read ok.  woohoo." )

    required_keywords = {
        'authentication':   [ 'user', 'pass' ],
        'cdrs':             [ 'order', 'title', 'cdrs-wanted' ],
        'time':             [ 'timezone' ]
    }

    sections = conf.get_sections()
    num_errors = 0
    for section in required_keywords:
        dprint( "testing existance of section \'{0:s}\'".format( section ))
        if section not in sections:
            sys.stderr.write( "{0:s}: missing section \'{1:s}\' in {2:s}\n". \
                format( progname, section, config_file ))
            num_errors = num_errors + 1
        else:
            keywords = conf.get_keywords( section )
            for keyword in required_keywords[ section ]:
                dmsg = "testing existance of keyword \'%s\' in section \'%s\'"
                dmsg = dmsg % ( keyword, section )
                dprint( dmsg )
                if keyword not in keywords:
                    err = "%s: missing keyword \'%s\' in section \'cdrs\'" + \
                        " in %s\n"
                    err = err % ( progname, keyword, config_file )
                    sys.stderr.write( err )

                    num_errors = num_errors + 1

    if num_errors > 0:
        return(1)
    dprint( "All mandatory fields in config file found" )

   # values from the config file over-ride any defaults
    keywords = conf.get_keywords( 'cdrs' )
    for keyword in keywords:
        type_ = conf.get_type( 'cdrs', keyword )
        if type_ == 'scalar':
            val = conf.get_values( 'cdrs', keyword )
            defaults[ keyword ] = val
            msg = "Replacing/setting default for \'{0}\' ".format( keyword )
            msg = msg + "value of \'{0}\' from config file".format( val )
            dprint( msg )

    # populate our values with defaults - which could have been updated from
    # the config file
    for field in defaults:
        if ( field not in values ) or ( values[ field ] == None ):
            dprint( "Using \'{0}\' value of \'{1}\' from defaults". \
                format( field, defaults[ field ] ))
            values[ field ] = defaults[ field ]

    # we now have our values settled from defaults, config-file, and cmd-line

    # some things might be a string, from the config-file, or a
    # command-line option - and we want an integer.

    try:
        padding = want_a_positive_integer( values[ 'padding' ], 'padding' )
        timeout = want_a_positive_integer( values[ 'timeout'], 'timeout' )
    except ValueError as err:
        sys.stderr.write( "%s: %s\n" % ( progname, err ))
        return(1)

    # now that we have settled all our values, we can print our usage
    if help_flag:
        u_values = {
            'padding':      padding,
            'config-file':  config_file,
            'timeout':      timeout,
        }
        usage( u_values )
        return(0)

    # we know this stuff exists from the above sanity checks so we 
    # don't have to check

    userid   = conf.get_values( 'authentication', 'user' )
    password = conf.get_values( 'authentication', 'pass' )
    timezone = conf.get_values( 'time', 'timezone' ) ;
    fields   = conf.get_values( 'cdrs', 'order' ) ;
    titles   = conf.get_values( 'cdrs', 'title' ) ;
    wanted   = conf.get_values( 'cdrs', 'cdrs-wanted' ) ;

    keywords = conf.get_keywords( 'cdrs' )
    got_config_field_sizes_flag = False
    if "field-size" in keywords:
        got_config_field_sizes_flag = True
        sizes = conf.get_values( 'cdrs', 'field-size' ) ;

    # fill if any missing data.  The 'fields' also specifies what fields we
    # want, so it is the master of what we want.  use it to handle any missing
    # titles or field sizes

    for field in fields:
        if field not in titles:
            dmsg = "Did not find title for \'%s\' in fields we want" % field
            dprint( dmsg )
            titles[ field ] = field.capitalize()

    dprint( "FROM date = " + from_date )
    dprint( "TO   date = " + to_date )
    dprint( "USER = \'{0:s}\' PASS = \'{1:s}\' TIMEZONE = {2:s}". \
        format( userid, password, timezone ))

    # Build up which type of CDRs we want

    cdrs_wanted = ""
    keys = list(wanted)
    for key in keys:
        val = wanted[ key ]
        if int( val ) == 1:
            cdrs_wanted = cdrs_wanted + "{0:s}=1&".format( key )

    # if we want a specific account
    if account_name != "":
        cdrs_wanted =  cdrs_wanted + "account={0:s}&".format( account_name )

    if cdrs_wanted != "":
        cdrs_wanted = cdrs_wanted[:-1]      # drop trailing '&'

    # put the URL all together

    # build the URL 
    url = "https://voip.ms/api/v1/rest.php" + \
            "?api_username={0:s}&api_password={1:s}&method={2:s}" \
            "&date_from={3:s}&date_to={4:s}&{5:s}&timezone={6:s}". \
                format( userid, password, method, from_date, to_date, \
                cdrs_wanted, timezone )

    dprint( "URL = \'" + url + "\'" )

    try:
        json_struct = send_request( url, timeout )
    except BadWebCall as err:
        # have a nicer message if there are no CDR records
        if "Failed status: no_cdr" in str(err):
            print( "No CDR records were found from {0:s} to {1:s}". \
                format( pretty_date( from_date ), pretty_date( to_date )))
            return(0)
        else:
            sys.stderr.write( "{0}: {1}\n".format( progname, str(err)))
            return(1)

    try:
        status = str( json_struct[ 'status' ] )
    except KeyError as err:
        err = "could not get return 'status' in JSON structure from API call"
        sys.stderr.write( "{0}: {1}\n".format( progname, err ))
        return(1)

    if status == 'no_cdr':
        print( "No CDR records were found from {0:s} to {1:s}". \
            format( pretty_date( from_date ), pretty_date( to_date )))
        return(0)

    if status != 'success':
        err = "API call was not successful.  Got status of '%s'" % status
        sys.stderr.write( "%s: %s\n" % ( progname, err ))
        return(1)

    dprint( 'status = ' + status )

    # get number of CDRs returned

    num_cdrs = len( json_struct[ 'cdr' ] )
    dprint( "Number of CDRs found is " + str( num_cdrs ))
    if num_cdrs == 0:
        print( "No CDR records were found" )
        return(0)

    if quiet_flag == False:
        print( "{0:d} CDR records found from {1:s} to {2:s}\n". \
            format( num_cdrs, pretty_date( from_date ), pretty_date( to_date )))

    # we want to figure out the maximum length of the data in the event that
    # the config did not provide us with the size of output field.  So grab all
    # the data and cache it for later printing while we get the maximum lengths

    data_sizes = {}
    data = []
    for i in range( 0, num_cdrs ):
        cdr_keys = list( json_struct[ 'cdr' ][ i ] )
        data.append( {} )
        for cdr_key in cdr_keys:
            value = json_struct[ 'cdr' ][ i ][ cdr_key ]
            data[i][ cdr_key ] = value      # save the data

            # get and save the maximum length
            # add padding spaces between fields
            data_len = len( value ) + padding   
            if cdr_key not in data_sizes:
                data_sizes[ cdr_key ] = data_len

                dmsg = "\'%s\' initialized to size %d because of size of data"
                dmsg = dmsg % ( cdr_key, data_len )
                dprint( dmsg )

            if data_len > data_sizes[ cdr_key ]:
                data_sizes[ cdr_key ] = data_len

                dmsg = "\'%s\' given size %d because of size of data" % \
                    ( cdr_key, data_len )
                dprint( dmsg )

    # now see if the titles being used exceed the max length of the data used.
    # If so, increase to accomodate the title length

    for field in titles:
        # add padding spaces between fields
        title_len = len( titles[ field ] ) + padding      
        if title_len > data_sizes[ field ]:
            data_sizes[ field ] = title_len
            dprint( "\'{0:s}\' given size {1:d} because of size of title". \
                format( field, title_len ))

    # now see if the config file specified an exact size to use
    # which over-rides the lengths we just created as defaults

    if got_config_field_sizes_flag == True:
        for field in sizes:
            config_len = int( sizes[ field ] )
            # ONLY set this if we have enough room for the title plus 
            # the padding
            if config_len > len( titles[ field ] ) + padding:
                data_sizes[ field ] = config_len
                dmsg = "\'%s\' given size %d because of size of config-file"
                dmsg = dmsg % ( field, config_len )
            else:
                dmsg = "\'%s\' can't set size of %d from config-file" + \
                       " because no room for title"
                dmsg = dmsg % ( field, config_len )
            dprint( dmsg )

    # now build the titles
    full_title      = 'call#' ;
    full_dash_title = '-----' ;

    if quiet_flag == False:
        for field in fields:
            title = titles[ field ]
            size  = data_sizes[ field ]
            dash_size = data_sizes[ field ] - padding
            num_dash_spaces = size - dash_size
            dash_title = ' ' * num_dash_spaces + '-' * dash_size
            full_dash_title = full_dash_title + dash_title

            format_str = "{0:>" + str(size) + "s}"
            full_title = full_title + format_str. \
                format( title.center( dash_size, ' ' ))

        print( full_title )
        print( full_dash_title )

    # now print the records

    if reverse_flag == True:
        data = list( reversed( data ))

    cdr_keys = list( json_struct[ 'cdr' ][ 0 ] )    # just do it once
    count = 1
    for i in range(0, num_cdrs ):
        cdr_record = "{0:-5d}".format( count )
        for field in fields:
            f = data[i][ field ]
            size = data_sizes[ field ]

            # See if we have to truncate the data.  This could happen if
            # the user specifically gave a size in the config file

            data_len = len( f )
            if data_len > ( size - padding ):
                slice_end = size - padding - 3
                f = f[0:slice_end] + "..."

            format_str = "{0:>" + str(size) + "s}"
            cdr_record = cdr_record + format_str.format( f )

        print( cdr_record )
        count = count + 1

    if cost_flag == True:
        accounts_duration = {}
        accounts_costs    = {}
        accounts_calls    = {}
        total_cost        = 0
        total_duration    = 0

        for i in range( 0, num_cdrs ):
            if 'account' in data[i]:
                account = data[i]['account']
                if account not in accounts_calls:
                    # initialize stuff
                    accounts_calls[ account ]    = 1
                    accounts_costs[ account ]    = float( data[i]['total'] )
                    accounts_duration[ account ] = int( data[i]['seconds'] )
                else:
                    accounts_calls[ account ] = accounts_calls[ account ] + 1
                    accounts_costs[ account ] = accounts_costs[ account ] + \
                        float( data[i]['total'] )
                    accounts_duration[ account ] = \
                        accounts_duration[ account ] + int( data[i]['seconds'] )

        for account in accounts_calls:
            total_cost = total_cost + accounts_costs[ account ]
            total_duration = total_duration + accounts_duration[ account ]

        print( "" )
        print( "Total cost is ${0:.2f}".format( total_cost ))
        extra_info = ""
        if total_duration > 60:
            extra_info = " ({0:d} seconds)".format( total_duration )
        print( "Total duration of calls is {0:s}{1:s}". \
            format( convert_seconds( total_duration ), extra_info ))

        total_accounts = len(list( accounts_calls ))
        if account_name == "" and total_accounts != 1:
            for account in accounts_calls:
                print( "" )
                msg = "Total cost of {0:d} calls for account \'{1:s}\'" + \
                    " is ${2:.2f}"
                msg = msg.format( accounts_calls[ account ], account, \
                    accounts_costs[ account ] )
                print( msg )

                extra_info = ""
                if accounts_duration[ account ] > 60:
                    extra_info = " ({0:d} seconds)". \
                        format( accounts_duration[ account ] )

                msg = "Total duration of calls for account \'%s\' is %s%s" % \
                    ( account, convert_seconds( accounts_duration[ account ] ), \
                    extra_info )
                print( msg )

    return(0)
