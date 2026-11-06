#!/usr/bin/env python3
"""Check ACM root-shell access and an ECM DHCP handshake through QEMU USB."""
import socket,select,time,struct,sys
from pathlib import Path
s=socket.socket(socket.AF_UNIX);s.connect(sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parents[1] / '.work/nand.usb.sock'));buffer=b''
def line(prefix,timeout=5):
 global buffer
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  if b'\n' in buffer:
   value,buffer=buffer.split(b'\n',1)
   if value.startswith(prefix):return value.decode()
  elif select.select([s],[],[],.1)[0]:
   chunk=s.recv(65536)
   if not chunk:raise RuntimeError('bridge closed')
   buffer+=chunk
 raise TimeoutError(prefix)
def cmd(value):s.sendall((value+'\n').encode())
def token(ep,direction,data):
 for _ in range(200):
  cmd(f'TOKEN{direction} {ep} {data}')
  answer=line(f'TOKEN {ep} {direction} '.encode())
  if ' ACK' in answer:return bytes.fromhex(answer.split(' ACK',1)[1].strip()) if direction=='IN' else int(answer.split(' ACK',1)[1].strip())
  if 'ERROR' in answer or 'STALL' in answer:raise RuntimeError(answer)
  time.sleep(.01)
 raise TimeoutError(answer)
def control(bm,request,value=0,index=0,length=0):
 setup=struct.pack('<BBHHH',bm,request,value,index,length)
 cmd('SETUP '+setup.hex());line(b'SETUPACK')
 if bm&128:
  result=token(0,'IN',str(length));token(0,'OUT','');return result
 token(0,'IN','0');return b''
line(b'CONNECT');cmd('RESET');line(b'RESETDONE')
print('device',control(128,6,0x100,length=18).hex())
control(0,5,1)
config=control(128,6,0x200,length=255)
print('config',config.hex())
interfaces=[];pos=0
while pos<len(config):
 size,kind=config[pos:pos+2];assert size>=2
 d=config[pos:pos+size]
 if kind==4:
  interface={'num':d[2],'alt':d[3],'cls':d[5],'sub':d[6],'eps':[]};interfaces.append(interface)
 elif kind==5:interface['eps'].append((d[2],d[3]&3))
 pos+=size
print(interfaces)
control(0,9,1)
acm=next(i for i in interfaces if i['cls']==2 and i['sub']==2)
acmdata=next(i for i in interfaces if i['num']==acm['num']+1)
ecm=next(i for i in interfaces if i['cls']==2 and i['sub']==6)
ecmdata=next(i for i in interfaces if i['num']==ecm['num']+1 and i['alt']==1)
control(1,11,1,ecmdata['num']);control(0x21,0x22,3,acm['num'])
def endpoints(i):
 return next(ep&127 for ep,typ in i['eps'] if typ==2 and not ep&128),next(ep&127 for ep,typ in i['eps'] if typ==2 and ep&128)
aout,ain=endpoints(acmdata);eout,ein=endpoints(ecmdata)
def write(ep,payload):
 while payload:
  done=token(ep,'OUT',payload.hex())
  if not done:time.sleep(.01)
  payload=payload[done:]
time.sleep(.5)
write(aout,b'id; echo USB_ACM_OK\r')
console=b''
for _ in range(100):
 time.sleep(.05)
 console+=token(ain,'IN','4096')
 if b'uid=0(root)' in console and b'USB_ACM_OK' in console:break
print('ACM',console.decode(errors='replace'));assert b'uid=0(root)' in console
mac=bytes.fromhex('020000770002');xid=0x12345678

def checksum(data):
 words=struct.unpack('!%dH'%(len(data)//2),data);total=sum(words)
 while total>>16:total=(total&65535)+(total>>16)
 return (~total)&65535

def dhcp(kind,requested=None):
 bootp=struct.pack('!BBBBIHH4s4s4s4s16s64s128s',1,1,6,0,xid,0,0x8000,b'\0'*4,b'\0'*4,b'\0'*4,b'\0'*4,mac+b'\0'*10,b'\0'*64,b'\0'*128)
 opts=b'\x63\x82\x53\x63\x35\x01'+bytes([kind])+b'\x37\x03\x01\x03\x06'
 if requested:opts+=b'\x32\x04'+requested+b'\x36\x04'+socket.inet_aton('192.168.77.1')
 payload=bootp+opts+b'\xff';udp=struct.pack('!HHHH',68,67,len(payload)+8,0)+payload
 ip=struct.pack('!BBHHHBBH4s4s',0x45,0,len(udp)+20,1,0,64,17,0,b'\0'*4,b'\xff'*4)
 ip=ip[:10]+struct.pack('!H',checksum(ip))+ip[12:]
 return b'\xff'*6+mac+b'\x08\x00'+ip+udp

def reply(kind):
 for _ in range(30):
  frame=token(ein,'IN','4096')
  if len(frame)<282 or frame[12:14]!=b'\x08\x00':continue
  header=14+(frame[14]&15)*4;packet=frame[header+8:]
  if len(packet)<240 or struct.unpack('!I',packet[4:8])[0]!=xid:continue
  pos=240;options={}
  while pos<len(packet):
   opt=packet[pos];pos+=1
   if opt==255:break
   if opt==0:continue
   size=packet[pos];pos+=1;options[opt]=packet[pos:pos+size];pos+=size
  if options.get(53)==bytes([kind]):return packet[16:20]
 raise RuntimeError('no DHCP reply')
control(0x21,0x43,0x0f,ecm['num'])
write(eout,dhcp(1));offered=reply(2);print('DHCPOFFER',socket.inet_ntoa(offered))
write(eout,dhcp(3,offered));leased=reply(5);print('DHCPACK',socket.inet_ntoa(leased));assert leased==offered
s.close()
