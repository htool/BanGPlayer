import yaml
import sys
import socket
import time

with open(r'packets.yaml') as file:
    # The FullLoader parameter handles the conversion from YAML
    # scalar values to Python the dictionary format
    packets = yaml.load(file, Loader=yaml.FullLoader)

who=None
curstream=b''

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

# sent by 0: len:  10 opcode: 1001  raw payload 5f f1 e1 35 04 81 03 0d 00 01

def decode_touch(payload):
    events={ 0: 'touch', 1: 'slide', 2: 'release' }
    event=events[payload[8]]
    x=''
    for xoffset in range(4):
        for xlen in range(1,3):
            xval=int.from_bytes(payload[xoffset:xoffset+xlen], "big")
            x+='(%d %d %4d) ' % (xoffset,xlen,xval)
    return 'touch event: time %9d %-7s (type %2d)  x: %4d y: %4d  count %d' % (int.from_bytes(payload[0:4], 'big'), event, payload[8], int.from_bytes(payload[4:6], 'big'), int.from_bytes(payload[6:8], 'big'), payload[9])

decoders = { 1: decode_ping, 2: decode_ping_reply, 3: decode_authenticate, 0x1001: decode_touch }

def decode(peer, curstream):
    if peer == None:
        return
    while len(curstream) > 0:
        length=int.from_bytes(curstream[0:2], "big")
        assert length > 2
        opcode=int.from_bytes(curstream[2:4], "big")
        length -= 2 # trimmed off opcode
        payload=curstream[4:4+length]
        assert len(payload) == length
        if opcode in decoders:
            decode = 'decoding: ' + decoders[opcode](payload)
        else:
            decode = 'raw payload %s' % raw_payload(payload)
        print('sent by %d: len: %3d opcode: %4x  %s' % (peer, length, opcode, decode))
        curstream=curstream[4+length:]

for p in list(packets):
    f=p.replace('peer','').split('_')
    assert len(f) == 2
    peerno,sequence=int(f[0]),int(f[1])
    chunk=packets[p]
    if who != peerno:
#        print('peer changed from %s to %s, so decoding the stream so far' % (who, peerno))
#        decode(who, curstream)
        curstream=b''
    else:
        pass
    #    print('same peer talking %s and %s, so adding to the stream' % (who, peerno))
    curstream += chunk
    #print('chunk: %s stream so far: %s' % (chunk,curstream))
    who = peerno

#decode(who, curstream)

def touchbytes(t, x, y, tp, count):
    opcode=0x1001
    b = opcode.to_bytes(2, 'big') + t.to_bytes(4, 'big') + x.to_bytes(2, 'big') + y.to_bytes(2, 'big') + tp.to_bytes(1, 'big') + count.to_bytes(1, 'big')
    b = len(b).to_bytes(2, 'big') + b
    return b

#for len in range(10):
#    b = bytes([len]) + b'A' * 10000
#    print('sending: %s' % b)
#    s.send(b)

if len(sys.argv) != 4:
    print('usage: puthon3 client.py X Y IP')
    sys.exit(0)

x,y=int(sys.argv[1]),int(sys.argv[2])

#1180 770

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((sys.argv[3], 6633))

print('sending hello')
s.send(packets['peer0_0'])
time.sleep(0.5)
print('sending own id')
time.sleep(0.5)
s.send(packets['peer0_1'])
time.sleep(0.5)
print('sending touch info')

b=touchbytes(int(time.time()),x,y,0,1)
decode(3, b)
s.send(b)

time.sleep(0.5)

b=touchbytes(int(time.time()),x,y,2,1)
decode(3, b)
s.send(b)

sys.exit(0)

for x in [1, 1337]:
    for y in [2, 2223]:
            for tp in [0,1,2]:
                b=touchbytes(int(time.time()),x,y,tp,1)
                decode(3, b)
                s.send(b)


