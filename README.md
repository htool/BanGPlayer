# BanGPlayer

Connect to your B&G Vulcan/Zeus from a laptop and use your mouse to control it.
For a new connection you'll need to 'ack' the new connectioned on the MFD.

$ ./BanGPlayer.py -h
usage: BanGPlayer.py [-h] [-c REMOTECONTROLD_PORT] [-r RSTP_PORT] [-d] IP

Remote display for B&G Vulcan/Zeus MFD

positional arguments:
  IP                    IP adress of Zeus/Vulcan MFD

optional arguments:
  -h, --help            show this help message and exit
  -c REMOTECONTROLD_PORT, --remotecontrold-port REMOTECONTROLD_PORT
                        remotecontrold port number (6633)
  -r RSTP_PORT, --rstp-port RSTP_PORT
                        rstp port number (554)
  -d, --debug           debug mode

