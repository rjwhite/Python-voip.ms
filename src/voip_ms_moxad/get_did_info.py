"""
get info about your voip.ms phone lines

Get information about each of your voip.ms phone lines

Examples:
  get-did-info.py --help     - print options
  get-did-info.py            - print list of DID numbers
  get-did-info.py --account  - print list (sub)account:DID-number
  get-did-info.py --all      - print all data available about the DID(s)
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
    import json

    from config_moxad import config

    from .functions import find_config_file, dprint, send_request, BadWebCall
    from . import globals
    from . import __version__
except ModuleNotFoundError as err:
    sys.stderr.write( "Error: missing module: %s\n" % err )
    sys.exit(1)


# print usage
#
# Arguments:
#   a dictionary containing values for:
#       'config-file'
#       'timeout'
# Returns:
#   0
# Exceptions:
#   none

def usage( values ):
    print( "usage: {} [options]*".format( globals.progname ))


    config_file = values.get( 'config-file', '?' )
    timeout     = values.get( 'timeout', '?' )

    options = """\
    [-a|--all]             (all info about DID(s))
    [-c|--config file]     (config-file. (default={})
    [-d|--debug]           (debugging output)
    [-h|--help]            (help)
    [-l|--line phone-num]  (DID-number)
    [-t|--timeout num]     (default={})
    [-A|--account]         (print (sub)account name(s) instead of DID)
    [-V|--version]         (print version of this program)\
    """

    print( options.format( config_file, timeout ))
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
    progname = argv[0]
    if progname == None or progname == "":
        progname = 'get-did-info'

    globals.progname = progname     # make available to other functions
    globals.debug_flag = False      # used by functions.debug

    # set some defaults

    all_info_flag = False
    account_flag  = False
    help_flag     = False
    method        = 'getDIDsInfo'
    config_file   = None

    # These may be over-written by config-file values

    defaults = {
        'did':      None,
        'timeout':  42,
    }

    # values from the command-line will go into values.
    # Then if any keys are found in defaults, but not in values,
    # then the default values will be copied into values as well
    # bringing in any changes from the config file

    values = {}

    # handle command-line options

    num_args = len( argv )
    i = 1
    while i < num_args:
        try:
            arg = argv[i]
            if arg == '-c' or arg == '--config':
                i = i + 1 ;     config_file = argv[i]
            elif arg == '-l' or arg == '--line':
                i = i + 1 ;     values[ 'did' ] = argv[i]
            elif arg == '-A' or arg == '--account':
                account_flag = True
            elif arg == '-t' or arg == '--timeout':
                i += 1 ;        values[ 'timeout' ] = argv[i]
            elif arg == '-d' or arg == '--debug':
                globals.debug_flag = True
            elif arg == '-a' or arg == '--all':
                all_info_flag = True
            elif arg == '-h' or arg == '--help':
                help_flag = True
            elif arg == '-V' or arg == '--version':
                print( "package version: {0}".format( __version__ ))
                print( "config  version: {0}".format( config.__version__ ))
                return(0)
            else:
                sys.stderr.write( "{0}: unknown option: {1}\n". \
                    format( progname, arg ))
                return(1)

        except IndexError as err:
            sys.stderr.write( "{}: {}.  Missing argument value to \'{}\'?\n". \
                format( progname, err, arg ))
            return(1)

        i = i+1

    # find the config file we really want

    config_file = find_config_file( config_file ) ;
    if not config_file:
        sys.stderr.write( "{0}: could not find a config file\n". \
            format( progname ))
        return(1) ;
    dprint( "using config file: " + config_file )

    config.Config.set_debug( globals.debug_flag )

    # no definitions file.  Our type info is all in our config file.
    try:
        conf = config.Config( config_file, '', AcceptUndefinedKeywords=True )
    except Exception as err:
        sys.stderr.write( "{0}: {1}\n".format( progname, err ))
        return(1)

    dprint( "Config data read ok.  woohoo." )

    # make sure we have our mandatory sections
    num_errors = 0
    needed_sections = [ 'authentication' ]
    sections = conf.get_sections()
    for section in needed_sections:
        if section not in sections:
            num_errors = num_errors + 1
            sys.stderr.write( "{0}: missing section \'{1}\' in {2}\n". \
                format( progname, section, config_file ))

    if num_errors > 0:
        return(1)

    # make sure we have our mandatory keywords for authentication
    keywords_i_need = [ 'user', 'pass' ]
    keywords = conf.get_keywords( 'authentication' )
    for keyword in keywords_i_need:
        if keyword not in keywords:
            err = "missing keyword \'{0}\'".format( keyword )
            err = err + " in section \'authentication\' in {0}". \
                format( config_file )
            sys.stderr.write( "{0}: {1}\n".format( progname, err ))
            num_errors += 1

    if num_errors > 0:
        return(1)

    userid   = conf.get_values( 'authentication', 'user' )
    password = conf.get_values( 'authentication', 'pass' )

    dprint( "user\t= {0}".format( userid ))
    dprint( "pass\t= {0}".format( password ))

    # values from the config file over-ride any defaults
    keywords = conf.get_keywords( 'info' )
    for keyword in keywords:
        type_ = conf.get_type( 'info', keyword )
        if type_ == 'scalar':
            val = conf.get_values( 'info', keyword )
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

    timeout = values[ 'timeout' ]

    if isinstance( timeout, str ):
        # must have got it from the cmd-line or the config file
        if not timeout.isdigit():
            err = "timeout ({0:s}) is not numeric".format( timeout )
            sys.stderr.write( "{0:s}: {1}\n".format( progname, err ))
            return(1)
        timeout = int( timeout )

    if help_flag:
        usage( { 'config-file': config_file, 'timeout': timeout } )
        return(0)

    # see if DID is given, and if so, format it correctly

    did = values[ 'did' ]
    if did:
        dprint( "DID number was given as a command-line option: {0}". \
            format( did ))
        did = did.replace( '-', '' )        # remove dashes
        did = did.replace( ' ', '' )        # remove spaces

        if did.isdigit() == False:
            sys.stderr.write( "{0}: DID is not numeric: {1}\n". \
                format( progname, str(did)))
            return(1)

        dprint( "Command-line option DID number is now: {0}".format( did ))

    if did:
        dprint( "Final DID number being used is {0}".format( did ))

    # build the URL 
    url = "https://voip.ms/api/v1/rest.php" + \
            "?api_username={0}&api_password={1}&method={2}". \
                format( userid, password, method )

    if did:
        url = url + "&did={0}".format( did )

    dprint( "URL = " + url )

    try:
        json_struct = send_request( url, timeout )
    except BadWebCall as err:
        sys.stderr.write( "{0}: {1}\n".format( progname, str(err)))
        return(1)

    # get number of DIDs returned

    num_dids = len( json_struct[ 'dids' ] )
    dprint( "Number of DIDs found is " + str( num_dids ))

    # we want to figure out the maximum length of the keywords.
    # and we only want to do it once, so only the first DID is used

    did_keys = list( json_struct[ 'dids' ][ 0 ] )
    max_key_len = len( max( did_keys, key=len ))

    # now get our data

    if 'dids' not in json_struct:
        sys.stderr.write( "{0}: missing key \'did\' in return data\n". \
            format( progname ))
        return(1)

    i = 0
    for d in json_struct[ 'dids' ]:
        try:
            line = json_struct[ 'dids' ][ i ][ 'did' ]
        except ( KeyError ) as err:
            dprint( "Could not get DID (line) name: {0}. skipping.". \
                format( err ))
            continue

        try:
            account = json_struct[ 'dids' ][ i ][ 'routing' ]
        except ( KeyError ) as err:
            dprint( "Could not get routing (account) name: {0}".format( err ))
            dprint( "Setting account to \'unknown\'" ) 
            account = 'unknown'

        if account_flag == True:
            account = account.replace( 'account:', '' )
            did_info = account + ':' + line
        else:
            did_info = line

        print( did_info )

        # now print the rest of the data
        if all_info_flag:
            for did_field in sorted( did_keys):
                try:
                    v = str( json_struct[ 'dids' ][ i ][ did_field ] )
                except ( KeyError ) as err:
                    dprint( "Could not get value for DID {0}". \
                        format( did_field))
                    dprint( "Setting DID to empty string" )
                    v = ""

                format_str = "\t{0:" + str( max_key_len ) + "s}    {1}"
                print( format_str.format( did_field, v ))

            if num_dids > 1: print( "" )

        i = i + 1

    return(0)
