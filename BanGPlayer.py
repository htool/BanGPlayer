#!/usr/bin/python3

import logging
import sys
import socket
import time
import base64
import time
import argparse
import gofree

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

mouseEvent = 0
keyboardEvent = 0
pressRelease = 0
opcode = 0

parser = argparse.ArgumentParser(description='Remote display for B&G Vulcan/Zeus MFD')
gofree.add_target_args(parser)
parser.add_argument('-c', '--remotecontrold-port', default=6633, help='remotecontrold port number (6633)')
parser.add_argument('-r', '--rstp-port', default=554, help='rstp port number (554)')
parser.add_argument('-s', '--slow', action='store_true',
                    help='extra buffering and 8 fps for a very slow link')
parser.add_argument('--lan', action='store_true',
                    help='force LAN UDP pipeline (no TCP, latency=0)')
parser.add_argument('-d', '--debug', action='store_true', help='debug mode')
args = vars(parser.parse_args())

packets = {
    'ping': 'AAYAAUQD18M=',
    'auth': 'ACgAAwIAAAAAAGlQYWQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',
    'bla1': 'AAkABAIAAAAAAAE=',
    'bla2': 'AAkABAIAAAAAAAE=',
    'bla3': 'AAwQAV/x4TUEgQMNAgE=',
    'bla4': 'AAwQAV/x4TYEeAL6AAE=',
    'bla5': 'AAwQAV/x4TYEeAL6AgE='
}

if args['debug']:
  logging.getLogger().setLevel(logging.DEBUG)

keyCodes = {
    'Escape': 25, # page
    'm': 50, # menu
    'Up': 78, # zoomin
    'Down': 74, # zoomout
    'p': 16, # power
    'Return': 28, # enter
    'c': 1, # cancel
    'g': 34, # goto
    'a': 45, # mark
    'o': 44 # mob
}

def decode_ping(payload):
    pingid = int.from_bytes(payload, "big")
    return "ping request, id %d" % pingid

def raw_payload(p):
    return ' '.join(['%02x' % n for n in p])

def strip0(b):
    l=''.join([chr(x) for x in b if x != 0])
    return l

def decode_ping_reply(payload):
    pingid = int.from_bytes(payload[0:4], "big")
    stringlen=32
    versionlen=24
    str1=strip0(payload[4:4+stringlen])
    str2=strip0(payload[4+stringlen:4+stringlen+stringlen])
    version=strip0(payload[4+stringlen+stringlen:4+stringlen+stringlen+versionlen])
    rest=payload[4+stringlen+stringlen+versionlen:]
    return "ping reply, id %d, id1 is '%s', id2 is '%s', version is '%s', rest is %s" % (pingid, str1,str2,version,raw_payload(rest))

def decode_authenticate(payload):
    pingid = int.from_bytes(payload[2:6], "big")
    stringlen=32
    str1=strip0(payload[6:6+stringlen])
    return "authenticate: client id, id %d, id1 is '%s'" % (pingid, str1)

def touchbytes(t, x, y, tp, count):
    opcode=0x1001
    b = opcode.to_bytes(2, 'big') + t.to_bytes(4, 'big') + x.to_bytes(2, 'big') + y.to_bytes(2, 'big') + tp.to_bytes(1, 'big') + count.to_bytes(1, 'big')
    b = len(b).to_bytes(2, 'big') + b
    return b

def keybytes(keycode, pressRelease):
    opcode=0x1003
    b = opcode.to_bytes(2, 'big') + keycode.to_bytes(4, 'big') + pressRelease.to_bytes(4, 'big')
    b = len(b).to_bytes(2, 'big') + b
    return b

if args['discover']:
    gofree.discover_and_exit()

mfd_ip = gofree.resolve(args['target'])

print ("Mapped keycodes:\nEscape\t\tPage\nm\t\tMenu\nArrow Up\tZoom in\nArrow Down\tZoom out\np\t\tPower\nEnter\t\tEnter\nc\t\tCancel\ng\t\tGoto\na\t\tMark\no\t\tMOB\n")

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

def on_event(pad, info):
    global mouseEvent
    global keyboardEvent
    event = info.get_event()
    type = event.type
    pressRelease = 0
    keyboardEvent = 0
    if type == Gst.EventType.NAVIGATION:
        e_struct = event.get_structure()
        me = e_struct.get_string('event')
        
        # Catching key presses
        if me == 'key-press':
          if e_struct.has_field('key'):
            pressRelease = 1
            keyboardEvent = 1

        if me == 'key-release':
          if e_struct.has_field('key'):
            pressRelease = 0
            keyboardEvent = 1
 
        if keyboardEvent == 1:
          key = e_struct.get_value('key')
          logging.debug('Key event: %s' % key)
          try:
            keycode = keyCodes[key]
            logging.debug('Keycode: %s' % keycode)
            b=keybytes(keycode, pressRelease)
            try:
              s.send(b)
            except socket.error as err:
              logging.debug("Error sending data: %s" % err)
          except:
            logging.debug('Unmapped key')

        # Send event on press/release and move between press/release
        if me == 'mouse-button-press':
            x = int(e_struct.get_double('pointer_x')[1])
            y = int(e_struct.get_double('pointer_y')[1])
            mouseEvent = 1
            e = 0
        if me == 'mouse-button-release':
            x = int(e_struct.get_double('pointer_x')[1])
            y = int(e_struct.get_double('pointer_y')[1])
            e = 2
        if me == 'mouse-move':
            x = int(e_struct.get_double('pointer_x')[1])
            y = int(e_struct.get_double('pointer_y')[1])
            e = 1

        if mouseEvent == 1:
            logging.debug('Event: %s x: %d y: %d' % (e, x, y))
            b=touchbytes(int(time.time()),x,y,e,1)
            try:
                s.send(b)
            except socket.error as err:
                print("Error sending data: %s" % err)
                # sys.exit(1)
            if e == 2:
                mouseEvent = 0

    return Gst.PadProbeReturn.OK



try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
except socket.error as err:
    print ("Error creating socket: %s" % err)
    sys.exit(1)

try:
    s.connect((mfd_ip, args['remotecontrold_port']))
except socket.gaierror as err:
    print ("Address-related error connecting to server: %s" % err)
    sys.exit(1)
except socket.error as err:
    print ("Connection error: %s" % err)
    sys.exit(1)


time.sleep(1)
logging.debug('Connecting to remotecontrold...')
s.send(base64.b64decode(packets['ping']))
time.sleep(1)
logging.debug('Sending authenticate...')
s.send(base64.b64decode(packets['auth']))
logging.debug('Connected')
s.send(base64.b64decode(packets['bla1']))

# initialize GStreamer
WINDOW_TITLE = 'B&G / Simrad screen'
GLib.set_prgname('BanGPlayer')
GLib.set_application_name(WINDOW_TITLE)
Gst.init(None)
# build the pipeline
# LAN: UDP + latency=0. Remote (Tailscale/Starlink): TCP + jitter buffer,
# no fps cap. --slow keeps the old 8 fps path.

def choose_pipeline_mode():
    if args['slow']:
        return 'slow'
    if args['lan']:
        return 'lan'
    if gofree.is_local_lan(mfd_ip):
        return 'lan'
    return 'remote'


PIPELINES = {
    'slow': (
        'rtspsrc name=source '
        'latency=800 '
        'drop-on-latency=true '
        'protocols=tcp '
        'buffer-mode=auto '
        '! queue max-size-buffers=0 max-size-time=2000000000 leaky=downstream '
        '! decodebin name=decoder '
        '! videorate drop-only=true max-rate=8 '
        '! videoconvert '
        '! autovideosink sync=false'
    ),
    'remote': (
        'rtspsrc name=source '
        'latency=400 '
        'drop-on-latency=true '
        'protocols=tcp '
        'buffer-mode=auto '
        '! queue max-size-buffers=0 max-size-time=1000000000 leaky=downstream '
        '! decodebin name=decoder '
        '! videoconvert '
        '! autovideosink sync=false'
    ),
    'lan': (
        'rtspsrc name=source latency=0 ! decodebin name=decoder ! autovideosink'
    ),
}

mode = choose_pipeline_mode()
logging.info(
    'RTSP %s pipeline to %s (%s)',
    mode,
    mfd_ip,
    'TCP 8 fps' if mode == 'slow'
    else 'TCP latency=400ms' if mode == 'remote'
    else 'UDP latency=0',
)
pipeline = Gst.parse_launch(PIPELINES[mode])
source = pipeline.get_by_name('source')
source.props.location = 'rtsp://' + mfd_ip + ':' + str(args['rstp_port']) + '/screenmirror'

#launch = "rtspsrc location=rtsp://" + args['IP'] + ":5554/screenmirror latency=1 !  rtph264depay ! h264parse ! autovideosink"
#launch = "playbin uri=rtsp://localhost:8554/test uridecodebin0::source::latency=300 ! autovideosink"
#    "videotestsrc ! navigationtest ! videoconvert ! ximagesink"
#    "videotestsrc pattern=snow ! video/x-raw,width=1280,height=800 ! autovideosink"
#pipeline = Gst.parse_launch(launch)
# start playing

pipeline.set_state(Gst.State.PLAYING)

# Navigation events travel upstream from the videosink; probe decodebin so
# LAN, remote, and slow pipelines all see mouse/keyboard events.
decoder = pipeline.get_by_name('decoder')
pad = (decoder.sinkpads[0] if decoder.sinkpads else
       (decoder.pads[0] if decoder.pads else None))
if pad is not None:
    pad.add_probe(Gst.PadProbeType.EVENT_UPSTREAM, on_event)

# wait until EOS or error
bus = pipeline.get_bus()
bus.add_signal_watch()

msg = bus.timed_pop_filtered(
    Gst.CLOCK_TIME_NONE,
    Gst.MessageType.ERROR | Gst.MessageType.EOS
)
