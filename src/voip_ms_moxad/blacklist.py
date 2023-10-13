"""
print or manipulate black-list from voip.ms API

Print and manage a black-list of numbers for your voip.ms phone lines

Examples:
  black-list --help           ( print usage )
  black-list                  ( print the list of filters along with rule IDs )
  black-list 519-555-0001     (add an entry)
  black-list -X -f 12345      ( delete rule with filter ID 12345 )
  black-list --busy   --note 'DickHeads Inc'  4165551212 ( add an entry )
  black-list --hangup --note 'DickHeads Inc'  --filterid 12345  4165551212
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
import re
try:
    import urllib

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
#       'did-number'
#       'timeout'
#		'routing'
# Returns:
#   0
# Exceptions:
#   none

def usage( values ):
    print( "usage: {} [options]* caller-id".format( globals.progname ))

    config_file = values.get( 'config-file', '?' )
    did_number  = values.get( 'did-number', '?' )
    timeout     = values.get( 'timeout', '?' )
    routing     = values.get( 'routing', '?' )

    options = """\
    [-c|--config  file]     (default={})
    [-d|--debug]            (debugging output)
    [-f|--filterid  num]    (existing rule filter ID to change/delete rule)
    [-h|--help]             (help)
    [-l|--line  DID]        (DID-phone-number (default={}))
    [-n|--note  string]     (descriptive note)
    [-r|--routing  noservice|busy|hangup|disconnected] (default={})
    [-t|--timeout num]      (default={})
    [-B|--busy]             (routing=sys:busy)
    [-D|--disconnected]     (routing=sys:disconnected)
    [-H|--hangup]           (routing=sys:hangup)
    [-N|--noservice]        (routing=sys:noservice)
    [-V|--version]          (print version of this program)
    [-X|--delete]           (delete an entry. Also needs --filterid)\
    """

    print( options.format( config_file, did_number, routing, timeout ))
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
        progname = 'blacklist'

    globals.progname = progname     # make available to other functions
    globals.debug_flag = False      # used by functions.debug

    ROUTING_NO_SERVICE   = "noservice"
    ROUTING_BUSY         = "busy"
    ROUTING_HANG_UP      = "hangup"
    ROUTING_DISCONNECTED = "disconnected"

    validrouting_types = set( [ ROUTING_NO_SERVICE, ROUTING_BUSY, 
                                ROUTING_HANG_UP, ROUTING_DISCONNECTED ] )

    help_flag       = False
    delete_flag     = False
    set_flag        = False
    update_flag     = False
    caller_id       = None
    filter_id       = None

    methods = {
        'get':      'getCallerIDFiltering',
        'set':      'setCallerIDFiltering',
        'delete':   'delCallerIDFiltering'
    }

    defaults = {
        'note':     "Added by {0} program".format( progname ),
        'routing':  ROUTING_NO_SERVICE,
        'callerid': None,
        'did':      None,
        'timeout':  45
    }
    values  = {}

    num_args = len( argv )
    i = 1
    while i < num_args:
        try:
            arg = argv[i]
            if arg == '-c' or arg == '--config':
                i = i + 1 ;     config_file = argv[i]
            elif arg == '-l' or arg == '--line':
                i = i + 1 ;     values[ 'did' ] = argv[i]
            elif arg == '-f' or arg == '--filterid':
                i = i + 1 ;     filter_id = argv[i]
                if not filter_id.isdigit():
                    err = "filter ID ({0:s}) is not numeric".format( filter_id )
                    sys.stderr.write( "{0:s}: {1}\n".format( progname, err ))
                    return(1)
            elif arg == '-n' or arg == '--note':
                i = i + 1 ;     values[ 'note' ] = argv[i]
            elif arg == '-r' or arg == '--routing':
                i = i + 1 ;     values[ 'routing' ] = argv[i]
            elif arg == '-B' or arg == '--busy':
                values[ 'routing' ] = ROUTING_BUSY
            elif arg == '-D' or arg == '--disconnected':
                values[ 'routing' ] = ROUTING_DISCONNECTED
            elif arg == '-H' or arg == '--hangup':
                values[ 'routing' ] = ROUTING_HANG_UP
            elif arg == '-N' or arg == '--noservice':
                values[ 'routing' ] = ROUTING_NO_SERVICE
            elif arg == '-t' or arg == '--timeout':
                i += 1
                timeout = argv[i]
                if not timeout.isdigit():
                    err = "timeout ({0:s}) is not numeric".format( timeout )
                    sys.stderr.write( "{0:s}: {1}\n".format( progname, err ))
                    return(1)
                values[ 'timeout' ] = int( timeout )
            elif arg == '-X' or arg == '--delete':
                delete_flag = True
            elif arg == '-d' or arg == '--debug':
                globals.debug_flag = True
            elif arg == '-a' or arg == '--all':
                all_info_flag = True
            elif arg == '-h' or arg == '--help':
                # we defer printing out the usage until we've gathered
                # what some default values are, from the config, etc
                help_flag = True
            elif arg == '-V' or arg == '--version':
                print( "package version: {0}".format( __version__ ))
                print( "config  version: {0}".format( config.__version__ ))
                return(0)
            else:
                m = re.match( "^\-", arg )
                if m:
                    sys.stderr.write( "{0}: unknown option: \'{1}\'\n". \
                        format( progname, arg ))
                    return(1)

                if caller_id != None:
                    err = "already provided a caller ID"
                    sys.stderr.write( "{0}: {1}: {2}\n". \
                        format( progname, err, caller_id ))
                    return(1)
                else:
                    caller_id = arg
                    values[ 'callerid' ] = caller_id
        except IndexError as err:
            err2 = "{0}.  Missing argument value to \'{1}\'?".format( err, arg )
            sys.stderr.write( "{0}: {1}\n".format( progname, err2 ))
            return(1)

        i = i+1

    # set a flag if we are making changes to an existing entry
    if 'routing' in values or 'note' in values or 'did' in values:
        set_flag = True
        dprint( "We are making changes because one or more of routing, " + 
                "note or did was given as an option" )

        if filter_id != None:
            # we're making changes, not adding new stuff - which could have
            # defaults. save into options to over-ride whatever the current
            # values are, and set a flag

            options = {}
            for field in values:
                options[ field ] = values[ field ]
            update_flag = True
    else:
        if caller_id != None:
            dprint( "given a caller-id - adding an entry using default values" )
            set_flag = True

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

    dprint( "Config data read OK.  double-plus woohoo." )

    # make sure we have our mandatory sections
    num_errors = 0
    needed_sections = [ 'authentication', 'black-list' ]
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
            num_errors = num_errors + 1
            err = "{0}: missing keyword \'{1}\' in section ". \
                format( progname, keyword )
            err = err + "\'authentication\' in {0}\n".format( config_file )
            sys.stderr.write( err )

    if num_errors > 0:
        return(1)

    # We know these exist from the above mandatory checks

    userid   = conf.get_values( 'authentication', 'user' )
    password = conf.get_values( 'authentication', 'pass' )

    dprint( "user\t= {0}".format( userid ))
    dprint( "pass\t= {0}".format( password ))

    # values from the config file over-ride any defaults
    keywords = conf.get_keywords( 'black-list' )
    for keyword in keywords:
        val = conf.get_values( 'black-list', keyword )
        msg = "Replacing/setting default for \'{0}\' ".format( keyword )
        msg = msg + "value of \'{0}\' from config file".format( val )
        dprint( msg )

        defaults[ keyword ] = val

    # populate our values with defaults - which could have been updated from 
    # the config file
    for field in defaults:
        if ( field not in values ) or ( values[ field ] == None ):
            dprint( "Using \'{0}\' value of \'{1}\' from defaults". \
                format( field, defaults[ field ] ))
            values[ field ] = defaults[ field ]

    timeout = int( values[ 'timeout' ] )   # must exist, because was in defaults

    # build the base URL

    base_url = "https://voip.ms/api/v1/rest.php" + \
            "?api_username={0}&api_password={1}". \
                format( userid, password )
    dprint( "BASE URL = " + base_url )

    # Need to check if this is an update of one or more items.  if so, we
    # want to preserve the current values if we did not specifically give new
    # ones as command-line options.

    if update_flag == True:
        dprint( "Crap.  we need to go grab existing values" )
        method = methods[ 'get' ]

        url = base_url + "&method={0}&filtering={1}".format( method, filter_id )
        dprint( "URL for getting OLD data  = " + url )

        try:
            old_data = send_request( url, timeout )
        except BadWebCall as err:
            sys.stderr.write( "{0}: {1}\n".format( progname, str(err)))
            return(1)

        # we should only have 1 entry being returned

        try:
            num_entries = len( old_data[ 'filtering' ] )
        except KeyError as err:
            sys.stderr.write( "{0}: No \'filtering\' data found\n". \
                format( progname ))
            return(1)

        if num_entries != 1:
            err = "{0}: did not get 1 entry (got {1:d}) ". \
                format( progname, num_entries )
            err = err + "for OLD values with filter ID = {0}\n". \
                format( filter_id )
            sys.stderr.write( err )
            return(1)

        fields_we_want = [ 'note', 'routing', 'callerid', 'did' ]
        old_fields = {}
        for field in fields_we_want:
            if field in old_data[ 'filtering' ][0]:
                old_fields[ field ] = old_data[ 'filtering' ][0][ field ]
                dprint( "grabbed OLD data for field \'{0}\' of \'{1}\'". \
                    format( field, old_fields[ field ] ))

        # now over-ride that with whatever we gave on the command-line

        for field in options:
            old_fields[ field ] = options[ field ]
            dprint( "Over-riding field \'{0}\' with cmd-line data \'{1}\'". \
                format( field, options[ field ] ))

        note      = old_fields[ 'note' ]
        caller_id = old_fields[ 'callerid' ]
        did       = old_fields[ 'did' ]
        routing   = old_fields[ 'routing' ]

        if routing.startswith("sys:"):
            routing = routing[4:]
    else:
        note      = values[ 'note' ]
        caller_id = values[ 'callerid' ]
        did       = values[ 'did' ]
        routing   = values[ 'routing' ]

    #  encode stuff that might have spaces or other unfriendly characters
    note     = urllib.parse.quote( note )
    password = urllib.parse.quote( password )

    # see if DID is given, and if so, format it correctly

    if did != None:
        did = did.replace( '-', '' )        # remove dashes
        did = did.replace( ' ', '' )        # remove spaces

        if did.isdigit() == False:
            sys.stderr.write( "{0}: DID is not numeric: {1}\n". \
                format( progname, str( did )))
            return(1)

        dprint( "DID number is now: {0}".format( did ))
    else:
            sys.stderr.write( "{0}: No DID number provided\n". \
                format( progname ))
            return(1)

    # make sure any routing type is valid

    if routing not in validrouting_types:
        sys.stderr.write( "{0}: Invalid routing type: \'{1}\'\n". \
            format( progname, routing ))
        return(1)

    # need to prepend 'sys:' if it isn't there

    m = re.match( "^sys", routing )
    if not m:
        routing = 'sys:' + routing

    # see if a callerID was given. If so, clean it up.

    if caller_id != None:
        caller_id = caller_id.replace( '-', '' )        # remove dashes
        caller_id = caller_id.replace( ' ', '' )        # remove spaces
        m = re.match( "^\d+$", caller_id )
        if not m:
            sys.stderr.write( "{0}: caller ID must be digits: \'{1}\'.\n". \
                format( progname, caller_id ))
            return(1)

    # we finally have default values set to show up in the usage

    if help_flag:
        u_values = { 'config-file': config_file,
                   'timeout':     timeout,
                   'did-number':  did,
                   'routing':     routing
                 }
        usage( u_values )
        return(0)

    # ready to go.

    if delete_flag:
        if set_flag:
            err = "Don't give fields to change along with the delete option"
            sys.stderr.write( "{0}: {1}\n".format( progname, err ))
            return(1)

        if filter_id == None:
            err = "Need to provide a filter ID to delete an entry"
            sys.stderr.write( "{0}: {1}\n".format( progname, err ))
            return(1)

        if caller_id != None:
            err = "Don't provide a caller ID to delete an entry"
            sys.stderr.write( "{0}: {1}\n".format( progname, err ))
            return(1)

        # we are doing a DELETE
        method = methods[ 'delete' ]
    elif set_flag:
        if caller_id == None:
            err = "Need to provide a caller ID to set or change an entry"
            sys.stderr.write( "{0}: {1}\n".format( progname, err ))
            return(1)

        # we are doing a SET
        method = methods[ 'set' ]
    else:
        # we are doing a GET
        method = methods[ 'get' ]

    dprint( "METHOD = " + method )

    # supply our method
    url = base_url + "&method={0}".format( method )

    # add on any fields if we are doing a change (SET)
    if set_flag == True:
        url = url + "&note={0}&routing={1}&callerid={2}&did={3}". \
            format( note, routing, caller_id, did )

    # now see if a filtering option  was given
    if filter_id != None:
        # oh good grief...
        if set_flag == True:
            url = url + "&filter={0}".format( filter_id )
        else:
            url = url + "&filtering={0}".format( filter_id )

        dprint( "...adding filter ID={0}".format( filter_id )) 

    dprint( "URL = " + url )

    try:
        json_struct = send_request( url, timeout )
    except BadWebCall as err:
        sys.stderr.write( "{0}: {1}\n".format( progname, str(err)))
        return(1)

    if delete_flag == True or set_flag == True:
        return(0)     # we're done

    try:
        num_lines = len( json_struct[ 'filtering' ] )
    except KeyError as err:
        err = "No \'filtering\' data found"
        sys.stderr.write( "{0}: {1}\n".format( progname, err ))
        return(1)

    dprint( "Number of lines is " + str( num_lines ))

    # print a title if we have some entries
    # get the max size of the notes
    max_note_len = 0
    for i in range( 0, num_lines ):
        try:
            note_len = len( json_struct[ 'filtering' ][ i ][ 'note' ] )
        except KeyError:
            note_len = 0     # couldn't get it

        if note_len > max_note_len:
            max_note_len = note_len

    if num_lines:
        print( "{0:<16s} {1:<12s} {2:<16s} {3:<28s} {4:s}". \
            format( 'CallerID', 'DID', 'Routing', 'Filter#', 'Note' ))
        print( "{0:<12s} {1:<12s} {2:<20s} {3:<10s} {4:s}". \
            format( '-' * 10, '-' * 10, '-' * 17, '-' * 7, '-' * max_note_len ))

    for i in range( 0, num_lines ):
        # set up defaults in stuff we want
        entry = {
            "filtering":    "unknown",
            "callerid":     "unknown",
            "did":          "unknown",
            "routing":      "unknown",
            "note":         ""
        }

        # collect whatever we found in the data - override defaults
        for field in json_struct[ 'filtering' ][ i ]:
            entry[ field ] = json_struct[ 'filtering' ][ i ][ field ]

        # print entry
        print( "{0:<12s} {1:<12s} {2:<20s} {3:<10d} {4:s}". \
            format( entry[ 'callerid' ], entry[ 'did' ], entry[ 'routing' ], \
                    int( entry[ 'filtering' ]), entry[ 'note' ] ))
    return(0)
