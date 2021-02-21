import gi

gi.require_version('Gst', '1.0')
from gi.repository import Gst


def on_event(pad, info):
    event = info.get_event()
    type = event.type
    if type == Gst.EventType.NAVIGATION:
        struct = event.get_structure()
        print ('x: ', (struct.get_double('x')))
        x = int(struct.get_double('x')[1])
        y = int(struct.get_double('y')[1])
        e = struct.get_string('event')
        print('Event: %s x: %d y: %d' % (e, x, y))
    return Gst.PadProbeReturn.OK


# initialize GStreamer
Gst.init(None)
# build the pipeline

pipeline = Gst.parse_launch(
#    "rtspsrc location=rtsp://192.168.105.21:554?channel=0 latency=1 !  rtph264depay ! h264parse !  vaapih264dec low-latency=1 ! vaapisink"
#    "videotestsrc ! navigationtest ! videoconvert ! ximagesink"
    "videotestsrc pattern=snow ! video/x-raw,width=1280,height=800 ! autovideosink"
)
# start playing
pipeline.set_state(Gst.State.PLAYING)

# for some reason no events from the vaapisink bin (first in the list), but the second bin (vaapih264dec) works OK
bin = pipeline.children[1]
# sink = 0, src = 1
pad = bin.pads[0]
pad.add_probe(Gst.PadProbeType.EVENT_UPSTREAM, on_event)

# wait until EOS or error
bus = pipeline.get_bus()
bus.add_signal_watch()

msg = bus.timed_pop_filtered(
    Gst.CLOCK_TIME_NONE,
    Gst.MessageType.ERROR | Gst.MessageType.EOS
)
