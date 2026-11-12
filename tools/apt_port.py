"""Small, append-only editor for the little-endian 64-bit APT in supplied packs."""
import struct
from pathlib import Path
U=lambda d,o:struct.unpack_from('<Q',d,o)[0]
P=lambda v:struct.pack('<Q',v)
def read_big(path):
 d=Path(path).read_bytes(); n=struct.unpack_from('>I',d,8)[0];pos=16;out={}
 for _ in range(n):
  off,size=struct.unpack_from('>II',d,pos);pos+=8;end=d.index(0,pos);name=d[pos:end].decode();pos=end+1
  assert off+size<=len(d);out[name]=d[off:off+size]
 return out
def write_big(path,files):
 table_size=16+sum(9+len(n.encode()) for n in files);off=(table_size+63)&~63;entries=[];body=bytearray(off)
 for name,data in files.items():
  entries.append(struct.pack('>II',off,len(data))+name.encode()+b'\0');body.extend(data);off+=len(data)
  pad=(-off)%64;body.extend(bytes(pad));off+=pad
 body[:16]=b'BIG4'+struct.pack('<I',len(body))+struct.pack('>II',len(files),table_size)
 table=b''.join(entries);body[16:16+len(table)]=table;Path(path).parent.mkdir(parents=True,exist_ok=True);Path(path).write_bytes(body)
class Apt:
 def __init__(self,files):
  self.files=files.copy();self.d=bytearray(files['0']);self.c=bytearray(files['1']);self.root=U(self.c,24)
  assert self.d[:14] in [b'Apt Data:1:7:8',b'Apt Data:1:8:8']; self.const=[]
  for i in range(U(self.c,32)):
   t,v=struct.unpack_from('<QQ',self.c,U(self.c,40)+16*i);self.const.append((t,v))
 def string(self,s):
  b=s.encode()+b'\0';self.align();o=len(self.d);self.d.extend(b);return o
 def align(self,n=8):self.d.extend(bytes((-len(self.d))%n))
 def append(self,b):self.align();o=len(self.d);self.d.extend(b);return o
 def addconst(self,s):
  raw=s.encode()+b'\0'
  for i,(t,v) in enumerate(self.const):
   if t==1 and self.c[v:v+len(raw)]==raw:return i
  self.c.extend(bytes((-len(self.c))%8));v=len(self.c);self.c.extend(raw);self.const.append((1,v));return len(self.const)-1
 def replaceconst(self,old,new):
  for i,(t,v) in enumerate(self.const):
   if t==1 and self.c[v:self.c.index(0,v)].decode()==old:
    self.c.extend(bytes((-len(self.c))%8));p=len(self.c);self.c.extend(new.encode()+b'\0');self.const[i]=(1,p)
 def rootitems(self):
  f=U(self.d,self.root+40);n=U(self.d,f);p=U(self.d,f+8)
  return f,[U(self.d,p+8*i) for i in range(n)]
 def setitems(self,items):
  f,_=self.rootitems();p=self.append(b''.join(P(i) for i in items));self.d[f:f+16]=P(len(items))+P(p)
 def addaction(self,code,first=False):
  p=self.append(code);item=self.append(P(1)+P(p));_,items=self.rootitems();self.setitems(([item]+items) if first else (items+[item]))
 def finish(self):
  self.c.extend(bytes((-len(self.c))%8));p=len(self.c);self.c.extend(b''.join(P(t)+P(v) for t,v in self.const));self.c[32:48]=P(len(self.const))+P(p)
  self.files['0']=bytes(self.d);self.files['1']=bytes(self.c);return self.files
class Code:
 def __init__(self,apt,start):self.a=apt;self.start=start;self.b=bytearray();self.pool=[];self.labels={};self.fix=[];self.functions={}
 def op(self,*b):self.b.extend(b);return self
 def align(self):self.b.extend(bytes((-(self.start+len(self.b)))%8))
 def string(self,s,op=0xa2):
  if s not in self.pool:self.pool.append(s)
  i=self.pool.index(s);assert i<256;return self.op(op,i)
 def reg(self,n):return self.op(0xb9,n)
 def num(self,n):
  if n==0:return self.op(0x59)
  if n==1:return self.op(0x5a)
  assert 0<=n<=127;return self.op(0xb5,n)
 def path(self,*parts):
  self.string(parts[0],0xae)
  for p in parts[1:]:self.string(p,0xaf)
  return self
 def member(self,s):return self.string(s,0xaf)
 def call(self,s):return self.string(s,0xb2)
 def branch(self,label,op=0x9d):
  self.op(op);self.align();self.fix.append((len(self.b),label));self.b.extend(bytes(4))
 def label(self,label):self.labels[label]=len(self.b)
 def function(self,name,body,params=0):
  self.reg(0).string(name).op(0x8e);self.align();header=len(self.b)
  self.b.extend(P(0)+struct.pack('<II',params,0x01290008)+P(0)+P(0)+bytes.fromhex('32547698000000007856341200000000'))
  begin=len(self.b);body(self);size=len(self.b)-begin;self.b[header+24:header+32]=P(size)
  if params:
   # Fix parameter table once code is appended; pointers are APT file offsets.
   self.functions[header]=(begin,size,params)
  self.op(0x4f)
 def complete(self):
  self.op(0)
  for off,label in self.fix:struct.pack_into('<i',self.b,off,self.labels[label]-(off+4))
  return bytes(self.b)
def action(apt,emit):
 # Reserve header: CONSTANTPOOL, 7 padding, count, pointer.
 apt.align();start=len(apt.d);c=Code(apt,start);c.op(0x88);c.align();c.b.extend(bytes(16));emit(c);raw=c.complete()
 p=apt.append(raw);assert p==start
 ids=[apt.addconst(s) for s in c.pool];pool=apt.append(b''.join(P(i) for i in ids));apt.d[p+8:p+24]=P(len(ids))+P(pool)
 for header,(_,_,n) in c.functions.items():
  params=apt.append(b''.join(P(3+i)+P(apt.string('arg'+str(i))) for i in range(n)))
  apt.d[p+header+16:p+header+24]=P(params)
 return p,c
