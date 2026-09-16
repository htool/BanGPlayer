# BanGPlayer

Connect to your B&G Vulcan/Zeus from a laptop and use your mouse to control it.
For a new connection you'll need to 'ack' the new connectioned on the MFD.

On the same LAN, omit the address to discover the MFD via GoFree. If several
answer, pass a GoFree name or IP. `./screengrab.py` uses the same discovery
and writes a JPEG of the RTSP screenmirror (default `zeus.jpg`).

Off-LAN (Tailscale/Starlink from hop) the player automatically uses RTSP
over TCP with a 400 ms jitter buffer. That avoids green H.264 artifacts
from UDP packet loss through Tailscale's 1280-byte MTU. On the boat LAN
it still uses UDP with `latency=0`. Use `-s` to cap at 8 fps, or `--lan`
to force the UDP path.

```
$ ./BanGPlayer.py -h
usage: BanGPlayer.py [-h] [--discover] [-c REMOTECONTROLD_PORT] [-r RSTP_PORT]
                     [-s] [--lan] [-d]
                     [IP_OR_NAME]

Remote display for B&G Vulcan/Zeus MFD

positional arguments:
  IP_OR_NAME            IP or GoFree name of Zeus/Vulcan MFD (omit to auto-
                        discover)

options:
  -h, --help            show this help message and exit
  --discover            list GoFree MFDs on the LAN and exit
  -c REMOTECONTROLD_PORT, --remotecontrold-port REMOTECONTROLD_PORT
                        remotecontrold port number (6633)
  -r RSTP_PORT, --rstp-port RSTP_PORT
                        rstp port number (554)
  -s, --slow            extra buffering and 8 fps for a very slow link
  --lan                 force LAN UDP pipeline (no TCP, latency=0)
  -d, --debug           debug mode
```

# Issues
On Ubunutu at some point I got a black screen. VLC also showed a black screen.
Using a SNAP version of VLC made it work for VLC.

$ apt-gegt remove gstreamer1.0-vaapi

was required to make it work again for this script.

