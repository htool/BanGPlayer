#!/usr/bin/python3

import gi
import logging
import sys
import socket
import time
import base64
import time


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


gi.require_version('Gst', '1.0')
from gi.repository import Gst

mouseEvent = 0
keyboardEvent = 0
pressRelease = 0
opcode = 0

packets = {
    'ping': 'AAYAAUQD18M=',
    'auth': 'ACgAAwIAAAAAAGlQYWQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',
    'bla1': 'AAkABAIAAAAAAAE=',
    'bla2': 'AAkABAIAAAAAAAE=',
    'bla3': 'AAwQAV/x4TUEgQMNAgE=',
    'bla4': 'AAwQAV/x4TYEeAL6AAE=',
    'bla5': 'AAwQAV/x4TYEeAL6AgE='
}

keyCodes = {
    'Escape': 25, # page
    'm': 50, # menu
    'Up': 78, # zoomin
    'Down': 74, # zoomout
    'p': 16, # power
    'Return': 28, # enter
    'c': 1, # cancel
    'g': 34, # goto
    'm': 45, # mark
    'o': 44 # mob
}

print (keyCodes)

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
          try:
            keycode = keyCodes[key]
            print('Key event: %s %s' % (keycode, key))
            b=keybytes(keycode, pressRelease)
            try:
              s.send(b)
            except socket.error as err:
              print ("Error sending data: %s" % err)
          except:
            print('Unmapped key')

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
            print('Event: %s x: %d y: %d' % (e, x, y))
            b=touchbytes(int(time.time()),x,y,e,1)
            try:
                s.send(b)
            except socket.error as err:
                print ("Error sending data: %s" % err)
                # sys.exit(1)
            if e == 2:
                mouseEvent = 0

    return Gst.PadProbeReturn.OK


if len(sys.argv) != 2:
    print('Usage: ' + sys.argv[0] + ' <B&G MFD ip>')
    sys.exit(0)

remoteIP = sys.argv[1]

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
except socket.error as err:
    print ("Error creating socket: %s" % err)
    sys.exit(1)

try:
    s.connect((remoteIP, 6633))
except socket.gaierror as err:
    print ("Address-related error connecting to server: %s" % err)
    sys.exit(1)
except socket.error as err:
    print ("Connection error: %s" % err)
    sys.exit(1)


time.sleep(1)
print('Connecting to remotecontrold...')
s.send(base64.b64decode(packets['ping']))
time.sleep(1)
print('Sending authenticate...')
s.send(base64.b64decode(packets['auth']))
print('Connected')
s.send(base64.b64decode(packets['bla1']))

# initialize GStreamer
Gst.init(None)
# build the pipeline


pipeline = Gst.parse_launch('rtspsrc name=source latency=0 ! decodebin ! autovideosink')
source = pipeline.get_by_name('source')
source.props.location = 'rtsp://' + remoteIP + ':5554/screenmirror'

#launch = "rtspsrc location=rtsp://" + remoteIP + ":5554/screenmirror latency=1 !  rtph264depay ! h264parse ! autovideosink"
#launch = "playbin uri=rtsp://localhost:8554/test uridecodebin0::source::latency=300 ! autovideosink"
#    "videotestsrc ! navigationtest ! videoconvert ! ximagesink"
#    "videotestsrc pattern=snow ! video/x-raw,width=1280,height=800 ! autovideosink"
#pipeline = Gst.parse_launch(launch)
# start playing

pipeline.set_state(Gst.State.PLAYING)

# for some reason no events from the vaapisink bin (first in the list), but the second bin (vaapih264dec) works OK
bin = pipeline.children[1]
# sink = 0, src = 1
pad = bin.pads[0]
#pad = pipeline.children[0]

pad.add_probe(Gst.PadProbeType.EVENT_UPSTREAM, on_event)

# wait until EOS or error
bus = pipeline.get_bus()
bus.add_signal_watch()
# bus.set_title('B&G Player')

msg = bus.timed_pop_filtered(
    Gst.CLOCK_TIME_NONE,
    Gst.MessageType.ERROR | Gst.MessageType.EOS
)
