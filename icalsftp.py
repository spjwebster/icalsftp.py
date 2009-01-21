#!/usr/bin/python

from icalendar import Calendar, Event
import paramiko, plistlib, sys, os, glob, tempfile, getpass, re, types
import keychain

def print_usage():
    print "icalsftp.py \"Calendar title\" <username@hostname:/base/path>"

calendars_path = os.path.expanduser( "~/Library/Calendars/" )

if len( sys.argv ) != 3:
    print "Expected 2 arguments, got %s" % str( len( sys.argv ) )
    print_usage()
    sys.exit(1)

calendar_title = sys.argv[ 1 ]

host_re = re.compile( r'^((sftp|ssh)://)?((?P<username>[^@]+)@)?(?P<hostname>[^:]+?):(?P<base_path>.+)?$' )
m = host_re.match( sys.argv[ 2 ] )
if m:
    username = m.group( 'username' )
    hostname = m.group( 'hostname' )
    base_path = m.group( 'base_path' )
else:
    print "Bad hostname"
    print_usage()
    sys.exit(1)

port = 22

cal_found = False

for calendar_filename in glob.glob( os.path.join( calendars_path, '*.calendar' ) ):
    calendar_path = os.path.join( calendars_path, calendar_filename )

    cal_info = plistlib.readPlist( os.path.join( calendar_path, 'Info.plist' ) )

    if cal_info[ 'Title' ] == calendar_title:
        cal_found = True
        
        combined_cal = Calendar()
        combined_cal[ 'CALSCALE' ] = 'GREGORIAN'
        combined_cal[ 'PRODID' ] = '-//Apple Inc.//iCal 3.0//EN'
        combined_cal[ 'VERSION' ] = '2.0'
        combined_cal[ 'X-WR-CALNAME' ] = calendar_title

        for event_filename in glob.glob( os.path.join( calendar_path, 'Events', '*.ics' ) ):

            cal = Calendar.from_string( open( os.path.join( calendar_path, 'Events', event_filename ), 'rb' ).read() )
            
            for component in cal.subcomponents:
                if isinstance( component, Event):
                    combined_cal.add_component( component )

        tmp_path = os.path.join( tempfile.mkdtemp(), '%s.ics' % calendar_title )
        f = open( tmp_path, 'wb' )
        f.write( combined_cal.as_string() )
        f.close()

if cal_found == False:
    print "Could not find calendar with title '%s'" % calendar_title
    sys.exit( 1 )


#paramiko.util.log_to_file('icalsftp.log')
kc = keychain.Keychain()
keychain_entry = kc.get_generic_password( 'login', username, 'sftp://%s' % hostname )

if type( keychain_entry ) == types.TupleType and password[ 0 ] == False:
    password = getpass.getpass( 'Password for %s@%s: ' % ( username, hostname ) )
else:
    password = keychain_entry[ 'password' ]

if password != None:
    kc.set_generic_password( 'login', username, password, 'sftp://%s' % hostname )

hostkey = None
hostkey_type = None

host_keys = paramiko.util.load_host_keys( os.path.expanduser( '~/.ssh/known_hosts' ) )
if host_keys.has_key( hostname ):
    hostkey_type = host_keys[ hostname ].keys()[ 0 ]
    hostkey = host_keys[ hostname ][ hostkey_type ]
    
try:
    trans = paramiko.Transport( ( hostname, port ) )
    trans.connect( username = username, password = password, hostkey = hostkey )
    sftp = paramiko.SFTPClient.from_transport( trans )

    sftp.put( tmp_path, os.path.join( base_path, os.path.basename( tmp_path ) ) )
    trans.close()
    
    
except Exception, e:
    print '*** Caught exception: %s: %s' % (e.__class__, e)
    traceback.print_exc()
    try:
        trans.close()
    except:
        pass
    sys.exit(1)
