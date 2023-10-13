"""
send a SMS message

Send a SMS message from one of your voip.ms phone lines

Examples:
    send-sms-message --help
    send-sms-message --recipient 555-123-4567 pick up some butter-tarts
    send-sms-message -r my-wife "I sold the kids"

send-sms-message uses a config file for authentication and defaults
and which of you rvoip.ms phone lines to use as the default.

Any arguments that are not options, are concatonated together
with a single space separator to make up the message.  For eg:

  send-sms-message test -r alfred gabba gabba -l main-DID hey

will send "test gabba gabba hey" to 'alfred' from line 'main-DID'.

'alfred' and 'main-DID' are aliases set in the config file.
"""

# Copyright 2019 RJ White
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

import sys
import re
import os

try:
    import json
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
# Returns:
#   0

def usage( values ):
    print( "usage: {} [option]* -r recipient message-to-send". \
        format( globals.progname ))

    config_file = values.get( 'config-file', '?' )
    did_number  = values.get( 'did-number', '?' )
    timeout     = values.get( 'timeout', '?' )

    options = """\
    [-c|--config file]   (config-file. default={})
    [-d|--debug]         (debugging output)
    [-n|--no-send]       (don't send the message, but show URL to send)
    [-h|--help]          (help)
    [-l|--line phone]    (sender DID-phone-number. default={})
    [-s|--show-aliases]  (show any aliases set in config file)
    [-t|--timeout num]   (default={})
    [-V|--version]       (print version)
    -r|--recipient phone-number\
    """

    print( options.format( config_file, did_number, timeout ))

    return(0)


# main program
#
# Arguments:
#   aray of command-line arguments
# Returns:
#   0:  ok
#   1:  not ok

def main( argv=sys.argv ):
    config_file = None

    progname = argv[0]
    if progname == None or progname == "":
        progname = 'blacklist'

    globals.progname = progname     # make available to other functions
    globals.debug_flag = False      # used by functions.debug

    # set some defaults
    # These may be over-written by config file values

    defaults = {
        'timeout':  42,
        'did':      None,
    }

    # values from the command-line will go into values.
    # Then if any keys are found in values, but not in defaults,
    # then the default values will be copied into values as well

    values = {}

    dont_send_flag    = False     # don't send the message, just print URL
    want_help_flag    = False     # set if -h/--help option used
    show_aliases_flag = False     # show any aliases set
    recipient         = ""        # phone number to send message to
    message           = ""        # the message to send.

    # process options

    num_args = len( argv )
    i = 1
    while i < num_args:
        try:
            arg = argv[i]

            m = re.match( '^-', arg )
            if not m:
                if message != "":
                    message = message + ' '
                message = message + arg

                i += 1
                continue

            if arg == '-d' or arg == '--debug':
                globals.debug_flag = True
            elif arg == '-n' or arg == '--no-send':
                dont_send_flag = True
            elif arg == '-V' or arg == '--version':
                print( "package version: {0}".format( __version__ ))
                print( "config  version: {0}".format( config.__version__ ))
                return(0)
            elif arg == '-c' or arg == '--config':
                i += 1 ;    config_file = argv[i] 
            elif arg == '-r' or arg == '--recipient':
                i += 1 ;    recipient = argv[i] 
            elif arg == '-l' or arg == '--line':
                i += 1 ;    values[ 'did' ] = argv[i] 
            elif arg == '-t' or arg == '--timeout':
                i += 1 ;    values[ 'timeout' ] = argv[i] 
            elif arg == '-s' or arg == '--show-aliases':
                show_aliases_flag = True
            elif arg == '-h' or arg == '--help':
                want_help_flag = True
            else:
                sys.stderr.write( "{0:s}: no such option: {1:s}\n". \
                    format( progname, arg ) )
                return(1)

            i += 1
        except IndexError as err:
            sys.stderr.write( "{0:s}: missing value for option {1:s}\n". \
                format( progname, arg ))
            return(1)

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
    needed_sections = [ 'authentication', 'sms' ]
    sections = conf.get_sections()
    num_errs = 0
    for section in needed_sections:
        if section not in sections:
            num_errs += 1
            sys.stderr.write( "{0:s}: missing section \'{1:s}\' in {2:s}\n". \
                format( progname, section, config_file ))

    if num_errs:
        return(1)

    # make sure we have our mandatory keywords for authentication
    keywords_i_need = [ 'user', 'pass' ]
    keywords = conf.get_keywords( 'authentication' )
    for keyword in keywords_i_need:
        if keyword not in keywords:
            num_errs += 1
            err = "missing keyword \'%s\' in section \'authentication\'" + \
                  " in %s"
            err = err % ( keyword, config_file )
            sys.stderr.write( "{0:s}: {1:s}\n".format( progname, err ))

    if num_errs:
        return(1)

    # We know these exist from the above mandatory checks
    userid   = conf.get_values( 'authentication', 'user' )
    password = conf.get_values( 'authentication', 'pass' )

    dprint( "user = {0:s}".format( userid ))
    dprint( "pass = {0:s}".format( password ))

    # values from the config file over-ride any defaults
    keywords = conf.get_keywords( 'sms' )
    for keyword in keywords:
        type_ = conf.get_type( 'sms', keyword )
        if type_ == 'scalar':
            val = conf.get_values( 'sms', keyword )
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
        if not timeout.isdigit():
            err = "timeout ({0:s}) is not numeric".format( timeout )
            sys.stderr.write( "{0:s}: {1}\n".format( progname, err ))
            return(1)
        timeout = int( timeout )

    # now get the line number we will send texts from

    did = values[ 'did' ]
    if did == None:
        err = "no DID given from either config file or command-line"
        sys.stderr.write( "{0:s}: {1}\n".format( progname, err ))
        return(1)

    dprint( "using DID \'{0:s}\' to send message from".format( did ))

    # now that we've resolved our DID number, whether from the config
    # file or an option, we can now properly print our usage if the
    # user asked for it

    if want_help_flag:
        u_values = { 'config-file': config_file,
                   'did-number':  did,
                   'timeout':     timeout
                 }
        usage( u_values )
        return(0)

    # see if there are aliases

    aliases = {}
    try:
        aliases = conf.get_values( 'sms', 'aliases' )
    except ValueError as err:
        pass

    # see if user wants to see any aliases set up in config file
    if show_aliases_flag:
        alias_keys = aliases.keys()
            
        max_len = 0
        # first get maximum length of aliases
        for key in alias_keys:
            alias = aliases[ key ]
            l = len( alias )
            if l > max_len:
                max_len = l

        max_len += 4        # add some spacing

        # now print them.  First sort the keys (aliases)
        sorted_aliases = list( aliases )
        sorted_aliases.sort()
        for key in sorted_aliases:
            alias = aliases[ key ]
            print( '{1:<{0}} {2}'.format( max_len, key, alias ))

        return(0)

    # sanity checking

    if recipient == "":
        sys.stderr.write( "{0:s}: need to provide --recipient option\n".
            format( progname ))
        num_errs += 1

    if message == "":
        sys.stderr.write( "{0:s}: need to provide a message to send\n".
            format( progname ))
        num_errs += 1

    if num_errs:
        return(1)

    dprint( "config file is {0:s}".format( config_file ))
    dprint( "message is now \"{0:s}\"".format( message ))
    dprint( "recipient is \'{0:s}\'".format( recipient ))
    dprint( "DID number is \'{0:s}\'".format( did ))

    if did in aliases:
        dprint( "found DID \'{0:s}\' in aliases!".format( did ))
        did = aliases[ did ]
        dprint( "DID number to send text FROM is now \'{0:s}\'". \
            format( did ))

    if recipient in aliases:
        dprint( "found recipient \'{0:s}\' in aliases!".format( recipient ))
        recipient = aliases[ recipient ]
        dprint( "recipient number to send text TO is now \'{0:s}\'". \
            format( recipient ))


    # now remove any spaces and dashes from the phone numbers

    recipient = recipient.replace( '-', '' )        # remove dashes
    recipient = recipient.replace( ' ', '' )        # remove dashes
    m = re.match( "^\d+$", recipient )
    if not m:
        err = "recipient phone number must be digits: \'{0:s}\'.". \
            format( recipient )
        sys.stderr.write( "{0:s}: {1:s}\n".format( progname, err ))
        return(1)

    did = did.replace( '-', '' )        # remove dashes
    did = did.replace( ' ', '' )        # remove dashes
    m = re.match( "^\d+$", did )
    if not m:
        err = "DID phone number must be digits: \'{0:s}\'.". \
            format( did )
        sys.stderr.write( "{0:s}: {1:s}\n".format( progname, err ))
        return(1)

    # we now have all the info we need to send the message

    # build the base URL

    base_url = "https://voip.ms/api/v1/rest.php" + \
            "?api_username={0:s}&api_password={1:s}". \
                format( userid, password )
    dprint( "BASE URL = " + base_url )

    # escape the message
    message = urllib.parse.quote( message )

    # add to the rest of the URL
    method = 'sendSMS'
    url = base_url + "&method={0:s}&dst={1:s}&did={2:s}&message={3:s}". \
        format( method, recipient, did, message )

    if dont_send_flag:
        print( 'URL = ' + url )
        return(0)

    # send the request

    try:
         json_struct = send_request( url, timeout )
    except BadWebCall as err:
        sys.stderr.write( "{0:s}: {1:s}\n".format( progname, str(err)))
        return(1)

    # if we appeared to make the call ok, then we're done

    return 0
