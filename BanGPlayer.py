#!/usr/bin/python3

import gi
import logging
import sys
import socket
import time

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


gi.require_version('Gst', '1.0')
from gi.repository import Gst

sendEvent = 0

packets = {
    'hello': b'AAYAAUQD18M=',
    'id': b'AHsAAkQD18MAVnVsY2FuIDEyAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABWdWxjYW4gMTIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADAuMC4wAAAAAAAAAAAAAAAAAAAAAAAAAgAAAAEAAAAZAAAABQAAABAFAAMgBQADIAAAAIE='
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


def on_event(pad, info):
    global sendEvent
    event = info.get_event()
    type = event.type
    if type == Gst.EventType.NAVIGATION:
        struct = event.get_structure()
        x = int(struct.get_double('pointer_x')[1])
        y = int(struct.get_double('pointer_y')[1])
        me = struct.get_string('event')

        # Send event on press/release and move between press/release
        if me == 'mouse-button-press':
            sendEvent = 1
            e = 0
        if me == 'mouse-button-release':
            e = 2
        if me == 'mouse-move':
            e = 1

        if sendEvent == 1:
            print('Event: %s x: %d y: %d' % (e, x, y))
            b=touchbytes(int(time.time()),x,y,e,1)
            try:
                s.send(b)
            except socket.error as err:
                print ("Error sending data: %s" % err)
                # sys.exit(1)
            if e == 2:
                sendEvent = 0

    return Gst.PadProbeReturn.OK


if len(sys.argv) != 2:
    print('Usage: ' + sys.argv[0] + ' <B&G MFD ip>')
    sys.exit(0)

remoteIP = sys.argv[1]



# initialize GStreamer
Gst.init(None)
# build the pipeline

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


time.sleep(0.5)
s.send(packets['hello'])
time.sleep(0.5)
s.send(packets['id'])
print('Connected remote touchpad')

pipeline = Gst.parse_launch('rtspsrc name=source latency=0 ! decodebin ! autovideosink')
source = pipeline.get_by_name('source')
source.props.location = 'rtsp://' + remoteIP + ':554/screenmirror'

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

msg = bus.timed_pop_filtered(
    Gst.CLOCK_TIME_NONE,
    Gst.MessageType.ERROR | Gst.MessageType.EOS
)
