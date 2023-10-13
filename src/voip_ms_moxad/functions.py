import sys
import os
import re
import datetime
import time

from . import globals
from .constants import FROM_DATE_FLAG, TO_DATE_FLAG 

_progname = globals.progname
if _progname == None:
    _progname = ''
else:
    _progname = _progname + ': '

# These modules should already be installed
try:
    import json
    import requests
except Exception as err:
    sys.stderr.write( "{0}{1}\n".format( _progname, err ))
    sys.stderr.write( "{0}use 'pip install' to install missing module\n". \
        format( _progname ))
    sys.exit(1)


# define some new exceptions

class BadWebCall( Exception ): pass
class InvalidArgument( Exception ): pass
class ShouldBeEmpty_String( Exception ): pass
class InvalidDate( Exception ): pass

def dprint( str ):
    """
    print debug statement if globals.debug_flag is True

    Arguments:
        string to print
    Returns:
        0
    Exceptions:
        none
    Globals:
        globals.debug_flag
        globals.progname
    """

    if globals.debug_flag == False:
        return None

    prefix = 'debug: '
    if globals.progname != None:
        prefix = prefix + globals.progname + ': '

    print( "{}{}".format ( prefix, str ))
    return None


def find_config_file( config=None ):
    """
    Find a config file to use.

    Passed a pathname of the last-ditch effort config file,
    which is likely the pathname given with the -c/--config
    option to the program.

    We accept the *last* *existing* config file from the list:
      $HOME/.voip-ms.conf
      environment variable VOIP_MS_CONFIG_FILE
      the pathname passed as an argument

    Arguments:
        config file pathname
    Returns:
        config-file  (could potentially be None)
    Globals:
        globals.progname
    Exceptions:
        KeyError
    """

    sprefix = sys._getframe().f_code.co_name + "(): "
    eprefix = sprefix

    progname = globals.progname
    if progname:
        eprefix = "{}: {}".format( progname, sprefix )

    final_config = None

    home = None
    try:
        home = os.environ[ 'HOME' ]
    except Exception:
        err = "could not get HOME environment variable"
        sys.stderr.write( "{0}{1}\n".format( eprefix, err ))
        # keep going

    # see if there is a config in the users HOME directory
    if home:
        pathname = home + '/' + ".voip-ms.conf"
        if os.path.isfile( pathname ):
            dprint( "{0}found config {1}".format( sprefix, pathname ))
            final_config = pathname
        else:
            dprint( "{0}no config found in HOME".format( sprefix ))

    # see if the user set an environment variable VOIP_MS_CONFIG_FILE
    try:
        pathname = os.environ[ 'VOIP_MS_CONFIG_FILE' ]
        if os.path.isfile( pathname ):
            dprint( "{0}found config via VOIP_MS_CONFIG_FILE: {1}". \
                format( sprefix, pathname ))
            final_config = pathname
    except KeyError:
        dprint( "{0}environment variable VOIP_MS_CONFIG_FILE not set ". \
            format( sprefix ))

    # see if the user provided a config file and if the file exists
    if config:
        if os.path.isfile( config ):
            dprint( "{0}found config given by option: {1}". \
                format( sprefix, config ))
            final_config = config
        else:
            dprint( "{0}config file given by option does not exist: {1}". \
                format( sprefix, config ))

    if final_config:
        dprint( "{0}final config file to use: {1}". \
            format( sprefix, final_config ))
    else:
        dprint( "{0}could not find a config file".format( sprefix ))

    return( final_config )


def send_request( url, timeout=60 ):
    """
    send a URL to the voip.ms API

    Arguments:
        1:  URL
        2:  optional timeout in seconds
    Returns:
        JSON structure
    Globals:
        globals.progname
    Exceptions:
        BadWebCall
    """

    sprefix = sys._getframe().f_code.co_name + "(): "
    eprefix = sprefix

    progname = globals.progname
    if progname:
        eprefix = "{}: {}".format( progname, sprefix )

    if url == None or url == "":
        err = "{}URL is undefined or empty string".format( prefix )
        raise TypeError( err )

    dprint( "{0}URL = {1}".format( sprefix, url ))

    try:
        res = requests.get( url, timeout=timeout )
        json_data = res.text
        json_struct = json.loads( json_data )
        status = str( json_struct[ 'status' ] )
    except Exception as err:
        raise BadWebCall( "{0}{1}".format( sprefix, err )) from None

    if status != 'success':
        raise BadWebCall( "{0}Failed status: {1}". \
            format( sprefix, status ))

    dprint( "{0}status = {1}".format( sprefix, status ))

    return( json_struct )


def convert_seconds( seconds ):
    """
    Convert seconds into a pretty string of hours, mins and seconds

    Arguments:
        number of seconds
    Returns:
        string. eg: "10 hours, 19 mins, 48 secs"
    Exceptions:
        InvalidArgument
    """

    my_name = sys._getframe().f_code.co_name

    if str( seconds ).isdigit() == False:
        raise InvalidArgument( "{0:s}(): Argument not a number: \'{1:s}\'.". \
            format( my_name, str( seconds ) ))

    mixed = ""

    seconds = int( seconds )        # in case given as a string
    if seconds == 0:
        return "0 secs"

    hours = int( seconds / ( 60 * 60 ))
    if hours:
        seconds = seconds - ( hours * ( 60 * 60 ))
        hour_str = "hours"
        if hours == 1:
            hour_str = "hour"
        mixed =  "{0:d} {1:s}, ".format( hours, hour_str )

    mins = int( seconds / 60 )
    if mins:
        seconds = seconds - ( mins * 60 )
        min_str = "mins"
        if mins == 1: 
            min_str = "min"     # singular
        mixed = "{0:s}{1:d} {2:s}, ".format( mixed, mins, min_str )

    sec_str = "secs"
    if seconds == 1:
        sec_str = "sec"

    mixed = "{0:s}{1:d} {2:s}".format( mixed, seconds, sec_str )

    return( mixed ) ;


def pretty_date( dayt ):
    """
    Convert a date of format YYYY-MM-DD into a pretty human-readable
    string such as '2017-02-04' -> Sat Feb 04, 2017

    Arguments:
        date of format YYYY-MM-DD
    Returns:
        string.  eg: Sat Feb 04, 2017
    Exceptions:
        InvalidDate
    """

    my_name = sys._getframe().f_code.co_name

    try:
        year, month, day = dayt.split("-")
    except:
        raise InvalidDate( "{0:s}(): Bad date. input was \'{1:s}\'". \
            format( my_name, dayt ))

    d =  datetime.date( int(year), int(month), int(day) )
    return( d.strftime("%a %b %d, %Y") )


def seconds_since_epoch( dayt ):
    """
    Convert a date of format YYYY-MM-DD into number of seconds since the
    Unix epoch such as '2017-02-04' -> 1517720400

    Arguments:
        date of format YYYY-MM-DD
    Returns:
        string.  eg: 1517720400
    Exceptions:
        InvalidDate
    """

    my_name = sys._getframe().f_code.co_name

    try:
        year, month, day = dayt.split("-")
        d = datetime.datetime( int(year), int(month), int(day), 0, 0). \
            strftime('%s')
    except:
        raise InvalidDate( "{}(): Bad date. input was \'{}\'". \
            format( my_name, dayt ))

    return( d )


def should_be_empty( some_string, msg ):
    """
    Test an argument if it is an empty string.
    raises the exception ShouldBeEmpty_String if it is not.

    Arguments:
        a string
    Returns:
       None if an empty string
    Exceptions:
        ShouldBeEmpty_String
    """

    if some_string != "":
        raise ShouldBeEmpty_String( msg )

    return( None )


def format_date( mon, year, flag):
    """
    Format a date.
    This might be called by a progrram like get-cdrs if the --last-month
    or --this-month options are called and we need a first and last mday
    of month in a format of YYYY-MM-DD

    Arguments:
        1: month - int
        2: year  - int
        3: flag  - FROM_DATE_FLAG | TO_DATE_FLAG
    Returns:
        YYYY-MM-DD
    Exceptions:
        InvalidArgument
        InvalidDate
    """

    my_name = sys._getframe().f_code.co_name

    # Jan = 1,  Dec = 12 - but days_in_month indexed starting at 0
    days_in_month = [ 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31 ]

    if ( str( mon ).isdigit == False ) or ( mon > 12 ):
        raise InvalidArgument( "{0:s}(): Invalid 1st argument (month): {1:s}". \
            format( my_name, str( mon ) ))

    if str( year ).isdigit() == False:
        raise InvalidArgument( "{0:s}(): Invalid 1st argument (year): \'{1:s}\'". \
            format( my_name, str( year ) ))

    if ( len( str( year )) != 2) and ( len( str( year )) != 4 ):
        raise InvalidArgument( "{0:s}(): Invalid 2nd argument (year): \'{1:d}\'". \
            format( my_name, year ))

    if ( flag != FROM_DATE_FLAG ) and ( flag != TO_DATE_FLAG):
        raise InvalidArgument( "{0:s}(): Invalid 3rd argument: \'{1:s}\'". \
            format( my_name, str( flag ) ))

    if year < 100:
        year = year + 2000

    current_year = time.localtime()[0]
    if year > current_year:
        raise InvalidDate( "{0:s}(): year {1:d} is past current year ({2:d})". \
            format( my_name, year, current_year ))

    num_days = days_in_month[ mon - 1 ]
    try:
        if ( is_leap_year( year )):
            if mon == 2:
                num_days = num_days + 1     # February and a leap year
    except (InvalidArgument, InvalidDate) as err:
        raise

    # want the month and day to be 2 digits
    mon      = "{0:02d}".format( int( mon ))
    num_days = "{0:02d}".format( int( num_days ))

    if flag == FROM_DATE_FLAG:
        dayt = "{0:s}-{1:s}-01".format( str(year), str(mon) )
    else:
        dayt = "{0:s}-{1:s}-{2:s}".format( str(year), str(mon), str(num_days) )

    return( dayt )


def is_leap_year( year ):
    """
    Is it a leap year?
    Assume a 2-digit year is 20xx

    Arguments:
        year (YYYY)
    Returns:
       0: No
       1: yes
    Exceptions:
        InvalidArgument
        InvalidDate
    """

    my_name = sys._getframe().f_code.co_name

    if str( year ) == "" :
        raise InvalidArgument( "{0:s}(): Invalid 1st argument (year)". \
            format( my_name ))

    # must be all digits
    if str( year ).isdigit() == False:
        raise InvalidDate( "{0:s}(): Invalid (year): \'{1:s}\'". \
            format( my_name, str( year ) ))

    # if 2 digits, make it 4 - this century
    if year < 100:
        year = year + 2000

    # must be 4 digits
    m = re.match( "^\d\d\d\d$", str( year ))
    if m == False:
        raise InvalidDate( "{0:s}(): Invalid (year): \'{1:s}\'". \
            format( my_name, str( year ) ))

    if year % 4:
        leap_year = False
    elif year % 100:
        leap_year = True
    elif year % 400:
        leap_year = False
    else:
        leap_year = True

    if leap_year == True:
        dprint( "{0:s}(): {1:d} IS a leap year".format( my_name, year ))
        return(1)
    else:
        dprint( "{0:s}(): {1:d} is NOT a leap year".format( my_name, year ))
        return(0)



def want_a_positive_integer( value, name=None ):
    """
    Test a value is a positive integer.
    If it's a string, convert it to an integer

    Arguments:
        1: value to be tested
        2: optional descriptive name for the value
    Returns:
        value as an integer
    Exceptions:
        BadValue
    prepare an error message if needed
    """

    if name:
        err = "'%s' must be a positive number.  got \'%s\'." % ( name, value )
    else:
        err = "value '%s' must be a positive number." % ( value )

    if isinstance( value, str ):
        if value.isdigit() == False:
            raise ValueError( err )

        value = int( value )

    if value < 0:
        raise BadValue( err )

    return( value )
