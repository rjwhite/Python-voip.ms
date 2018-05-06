# setup.py

from distutils.core import setup

setup( 
    name                = "python-voip.ms",
    version             = "0.2",
    scripts             = [ 'scripts/black-list', 'scripts/get-cdrs', 'scripts/get-did-info', 'scripts/write-phone-CDR-records' ],
    author              = "RJ White",
    author_email        = "rj@moxad.com",
    maintainer          = "RJ White",
    maintainer_email    = "rj@moxad.com",
    url                 = "http://github.com/rjwhite/Python-voip.ms",
    description         = "command-line scripts to use voip.ms API",
    long_description    = "command-line scripts to use voip.ms API",
    download_url        = "http://github.com/rjwhite/Python-voip.ms",
    license             = "GNU General Public",
    )
