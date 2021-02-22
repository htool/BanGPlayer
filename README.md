# BanGPlayer

Connect to your B&G Vulcan/Zeus from a laptop and use your mouse to control it.

The video connection is gstreamer playing:
 rtsp://vulcan_ip:554/screenmirror

Using the gstreamer dstNavigation we catch mouse events and send them to the home brewn remotecontrold daemon on the MFD on port 6633.

For a new connection you'll need to 'ack' the new connectioned on the MFD.
