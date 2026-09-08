#!/usr/bin/python3
"""Grab one JPEG from a B&G Zeus/Vulcan RTSP screenmirror.

Same rtspsrc → decodebin pipeline as BanGPlayer.py, but jpegenc + appsink
instead of autovideosink. Uses the same GoFree discovery as BanGPlayer.py.
"""

import argparse
import logging
import sys
import time

import gofree

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def grab(ip, port, outfile, settle=3.0, protocols='tcp'):
    import gi
    gi.require_version('Gst', '1.0')
    from gi.repository import Gst

    Gst.init(None)
    launch = (
        'rtspsrc name=source latency=200 protocols=%s ! '
        'decodebin ! videoconvert ! jpegenc ! '
        'appsink name=sink max-buffers=1 drop=true sync=false'
    ) % protocols
    pipeline = Gst.parse_launch(launch)
    pipeline.get_by_name('source').set_property(
        'location', 'rtsp://%s:%s/screenmirror' % (ip, port)
    )
    sink = pipeline.get_by_name('sink')
    bus = pipeline.get_bus()
    ret = pipeline.set_state(Gst.State.PLAYING)
    if ret == Gst.StateChangeReturn.FAILURE:
        raise RuntimeError('failed to start GStreamer pipeline')

    deadline = time.time() + max(settle, 0.5)
    err = None
    while time.time() < deadline:
        msg = bus.timed_pop_filtered(
            50 * Gst.MSECOND,
            Gst.MessageType.ERROR | Gst.MessageType.EOS
        )
        if msg is None:
            continue
        if msg.type == Gst.MessageType.ERROR:
            gerr, debug = msg.parse_error()
            err = '%s (%s)' % (gerr, debug)
            break
        if msg.type == Gst.MessageType.EOS:
            err = 'EOS before settle'
            break
    if err:
        pipeline.set_state(Gst.State.NULL)
        raise RuntimeError(err)

    sample = sink.emit('try-pull-sample', 5 * Gst.SECOND)
    pipeline.set_state(Gst.State.NULL)
    if sample is None:
        raise RuntimeError('no video sample after %.1fs' % settle)
    buf = sample.get_buffer()
    ok, info = buf.map(Gst.MapFlags.READ)
    if not ok:
        raise RuntimeError('could not map JPEG buffer')
    try:
        data = bytes(info.data)
    finally:
        buf.unmap(info)
    with open(outfile, 'wb') as f:
        f.write(data)
    return len(data)


def main():
    parser = argparse.ArgumentParser(
        description='Screengrab a B&G Vulcan/Zeus RTSP screenmirror'
    )
    gofree.add_target_args(parser)
    parser.add_argument(
        '-r', '--rstp-port', default=554, help='RTSP port number (554)'
    )
    parser.add_argument(
        '-o', '--output', default='zeus.jpg', help='JPEG output path'
    )
    parser.add_argument(
        '--settle',
        type=float,
        default=3.0,
        help='seconds to wait for the picture to update before grabbing'
    )
    parser.add_argument(
        '--protocols',
        default='tcp',
        help='rtspsrc protocols (tcp or udp)'
    )
    parser.add_argument('-d', '--debug', action='store_true', help='debug mode')
    args = parser.parse_args()
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    if args.discover:
        gofree.discover_and_exit()
    ip = gofree.resolve(args.target)
    try:
        n = grab(ip, args.rstp_port, args.output, args.settle, args.protocols)
    except Exception as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    print('wrote %s (%d bytes)' % (args.output, n))


if __name__ == '__main__':
    main()
