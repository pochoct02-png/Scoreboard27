"""Read constants, constant pools and DefineFunction2 records from 64-bit APT."""
from pathlib import Path
import struct,re,sys
u32=lambda d,o:struct.unpack_from('<I',d,o)[0]
u64=lambda d,o:struct.unpack_from('<Q',d,o)[0]
def constants(c):
 n=u64(c,32);p=u64(c,40);out=[]
 for i in range(n):
  t=u64(c,p+16*i);v=u64(c,p+16*i+8)
  out.append(c[v:c.index(0,v)].decode() if t==1 else v)
 return out
def pools(d,c):
 out=[]
 for o in range(len(d)-24):
  if d[o]!=0x88:continue
  a=(o+8)&~7;n=u64(d,a);p=u64(d,a+8)
  if 0<n<2000 and p+n*8<=len(d):
   ids=[u64(d,p+8*i) for i in range(n)]
   if max(ids)<len(c):out.append((o,[c[i] for i in ids]))
 return out
def funcs(d):
 out=[]
 for o in range(len(d)-52):
  if d[o]!=0x8e:continue
  a=(o+8)&~7
  if d[a+32:a+48]!=bytes.fromhex('32547698000000007856341200000000'):continue
  name=u64(d,a);n=u32(d,a+8);regs=u32(d,a+12);params=u64(d,a+16);size=u64(d,a+24)
  if a+48+size<=len(d):out.append((o,a+48,size,n,regs,params))
 return out
