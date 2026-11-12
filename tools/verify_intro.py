"""Static integrity checks and execution tests for the emitted bridge (not FIFA16)."""
import argparse,struct,json,hashlib
from pathlib import Path
from apt_port import Apt,read_big,U
from inspect_apt import funcs,constants,pools
from build_intro import NS9,NS10,isolate
class Obj(dict):
 def __init__(self,*a,**k):super().__init__(*a,**k);self.parent=None
 def getv(self,k):return self[k] if k in self else self.parent.getv(k) if self.parent else None
class Func:
 def __init__(self,vm,start,size,cp,params,flags):self.vm=vm;self.start=start;self.size=size;self.cp=cp;self.params=params;self.flags=flags
 def __call__(self,target,*args):return self.vm.run(self.start,self.size,self.cp,target,args,self.params,self.flags)
def get(o,k):
 if isinstance(o,Obj):return o.getv(k)
 if isinstance(o,dict):return o.get(k)
 if isinstance(o,(list,str)) and k=='length':return len(o)
 if isinstance(o,list) and isinstance(k,int):return o[k] if k<len(o) else None
 if isinstance(o,str) and k=='split':return lambda target,sep:target.split(sep)
 raise AssertionError(('invalid member read',o,k))
class VM:
 def __init__(self,files,glob):self.d=files['0'];self.const=constants(files['1']);self.glob=glob
 def run(self,start,size,cp=None,target=None,args=(),params=(),flags=0x129):
  d=self.d;end=start+size;pc=start;stack=[];regs={1:target,2:self.glob}
  for (reg,name),v in zip(params,args):regs[reg]=v
  steps=0
  while pc<end:
   steps+=1;assert steps<20000
   op=d[pc];pc+=1
   def u32():
    nonlocal pc
    v=struct.unpack_from('<I',d,pc)[0];pc+=4;return v
   def u64():
    nonlocal pc
    v=U(d,pc);pc+=8;return v
   if op in [0x88,0x8e,0x87,0x99,0x9d,0xb8]:pc=(pc+7)&~7
   if op==0:break
   elif op==0x88:
    n=u64();p=u64();cp=[self.const[U(d,p+8*i)] for i in range(n)]
   elif op==0xb9:stack.append(regs.get(d[pc]));pc+=1
   elif op==0xa2:stack.append(cp[d[pc]]);pc+=1
   elif op==0xae:stack.append(get(self.glob,cp[d[pc]]));pc+=1
   elif op==0xaf:
    o=stack.pop();stack.append(get(o,cp[d[pc]]));pc+=1
   elif op==0xb2:
    method=cp[d[pc]];pc+=1;o=stack.pop();n=stack.pop();a=[stack.pop() for _ in range(n)];f=get(o,method);assert callable(f),(method,o);f(o,*a)
   elif op==0x52:
    method=stack.pop();o=stack.pop();n=stack.pop();a=[stack.pop() for _ in range(n)];f=get(o,method);assert callable(f),(method,o);stack.append(f(o,*a))
   elif op==0x4e:
    k=stack.pop();o=stack.pop();stack.append(get(o,k))
   elif op==0x4f:
    v=stack.pop();k=stack.pop();o=stack.pop();assert isinstance(o,dict),(o,k);o[k]=v
   elif op==0x87:regs[u32()]=stack[-1]
   elif op==0x17:stack.pop()
   elif op==0x59:stack.append(0)
   elif op==0x5a:stack.append(1)
   elif op==0xb5:stack.append(d[pc]);pc+=1
   elif op==0x73:stack.append(True)
   elif op==0x74:stack.append(False)
   elif op in [0x75,0x76]:stack.append(None)
   elif op==0x49:b=stack.pop();a=stack.pop();stack.append(a==b)
   elif op==0x48:b=stack.pop();a=stack.pop();stack.append(a<b)
   elif op==0x12:stack.append(not stack.pop())
   elif op in [0x99,0x9d,0xb8]:
    delta=struct.unpack_from('<i',d,pc)[0];pc+=4
    take=True if op==0x99 else bool(stack.pop())
    if op==0xb8:take=not take
    if take:pc+=delta
   elif op==0x8e:
    name=u64();n=u32();regflags=u32();p=u64();length=u64();pc+=16
    par=[(U(d,p+16*i),U(d,p+16*i+8)) for i in range(n)]
    stack.append(Func(self,pc,length,cp,par,regflags>>16));pc+=length
   else:raise AssertionError(('unsupported opcode',hex(op),hex(pc-1)))
  assert not stack,('unbalanced stack',stack,hex(start))

def assert_graph(files):
 a=Apt(files);d=a.d;r=a.root;count=U(d,r+56);table=U(d,r+64)
 assert table+count*8<=len(d)
 for i in range(count):
  p=U(d,table+8*i)
  if p:assert p+16<=len(d) and U(d,p+8)==0x09876543,(i,p)
 f,items=a.rootitems()
 for p in items:
  t=U(d,p)
  assert t in [1,3,5,8]
  if t in [1,8]:assert U(d,p+(16 if t==8 else 8))<len(d)
 for _,start,size,n,reg,p in funcs(d):
  if n:
   assert p+16*n<=len(d)
   for i in range(n):assert U(d,p+16*i)<(reg&65535)
 # Parse constant pools and all referenced strings.
 constants(files['1']);return {'characters':count,'root_items':len(items),'functions':len(funcs(d))}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--fc27',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);args=ap.parse_args();fc=args.fc27;out=args.output
 f9=read_big(out/f'game/globalComponents/{NS9}/{NS9}.big');f10=read_big(out/f'game/globalComponents/{NS10}/{NS10}.big');fw=read_big(out/'game/overlays/overlay_9042.big')
 result={'runtime_tested':False,'graphs':{n:assert_graph(f) for n,f in [('texts',f9),('panel',f10),('wrapper',fw)]}}
 original=isolate(read_big(fc/'globalComponents/overlayComponents_10/overlayComponents_10.big'))
 # Verify byte-for-byte preservation of the actual FC27 frame and motion code.
 result['original_fc27_functions']={}
 for name,start,length in [('InitAnimation',0x9040,584),('AnimateIn',0x9338,1527),('AnimateOut',0x9a20,243)]:
  assert f10['0'][start:start+length]==original['0'][start:start+length],name
  result['original_fc27_functions'][name]=hashlib.sha256(f10['0'][start:start+length]).hexdigest()
 for filename,data in original.items():
  if filename not in ['0','1']:assert f10[filename]==data,filename
 result['all_panel_textures_and_geometry_preserved']=True
 # Execute emitted bytecode, including function tables and jump operands.
 proto=Obj();proto['Shutdown']=lambda o:o.__setitem__('shutdown_count',o.get('shutdown_count',0)+1)
 fullproto=Obj();glob=Obj(game=Obj(overlays=Obj(Champions=Obj(overlay_10042=Obj(prototype=proto))),globalComponents=Obj({NS10:Obj(FullPanel=Obj(prototype=fullproto))}),globalClasses=Obj(AnimationManager=Obj(ClearAnimations=lambda o,target:None))),ION_Localization=Obj(ToUpperCase=lambda o,s:s.upper()),cafe=Obj(utility=Obj(Delegate=Obj(Create=lambda o,target,f:lambda:f(target)))))
 crests=[];glob['getCreationCentreAsset']=lambda o,*a:crests.append(a)
 vm=VM(fw,glob);a=Apt(fw);_,items=a.rootitems();p=U(a.d,items[-1]+8);vm.run(p,len(vm.d)-p)
 instance=Obj(mcPanel=Obj(mcNextFixtureTexts=Obj(mcHomeCrest=Obj(),mcAwayCrest=Obj()),mcMaskFullPanel=Obj(),mcContentHolder=Obj()));instance.parent=proto
 calls=[];callbacks=[];instance['Init']=lambda o:calls.append('init');instance['mcPanel']['AnimateOut']=lambda o,callback:callbacks.append(callback)
 data=['']*18;data[2]='El Libertador';data[3]='FC Barcelona';data[5]='241';data[6]='Como 1907';data[8]='1745';payload='|'.join(data)
 proto['Update'](instance,payload)
 assert [instance[k] for k in ['m_sStadiumName_upper','m_sTeamNameHome15_upper','m_sTeamNameAway15_upper']]==['EL LIBERTADOR','FC BARCELONA','COMO 1907']
 assert [a[1] for a in crests]==['241','1745'];assert calls==['init']
 proto['Update'](instance,payload);assert calls==['init']
 proto['Update'](instance,'broken');proto['Update'](instance,None);assert calls==['init']
 proto['Remove'](instance);assert len(callbacks)==1;callbacks.pop()();assert instance['_visible']==False and instance['shutdown_count']==1
 proto['Update'](instance,payload);assert calls==['init','init'] and instance['_visible']
 proto['Remove'](instance);old=callbacks.pop();data[3]='Real Madrid';proto['Update'](instance,'|'.join(data));old();assert instance['_visible'] and instance['shutdown_count']==1
 result['bridge_execution']=['dynamic names/stadium','native crest resolver','duplicate-update suppression','incomplete-update rejection','exit callback','reentry','stale exit callback guard']
 # Execute the specialized FullPanel initialization with typed text stubs.
 pv=VM(f10,glob);pa=Apt(f10);_,items=pa.rootitems();p=U(pa.d,items[-1]+8);pv.run(p,len(pv.d)-p)
 full=glob['game']['globalComponents'][NS10]['FullPanel']
 for key in ['NEXT_FIXTURE_NAME_CONFIG','NEXT_FIXTURE_STADIUM_CONFIG','AWAY_CREST_FINAL_POS_X','HOME_CREST_FINAL_POS_X','CREST_DEFAULT_POS_Y','TEAM_NAME_DEFAULT_POS_Y','STADIUM_TEXT_DEFAULT_POX_Y']:full[key]=key
 texts=[]
 panel=Obj(mcNextFixtureTexts=Obj(),mcPlayerToWatch=Obj(),mcTableView=Obj(),mcTitle=Obj());panel.parent=fullproto
 for clip in ['mcHomeName','mcAwayName','mcStadiumName','mcHomeCrest','mcAwayCrest','mcScoreHome','mcScoreAway','mcMinutes','mcDivider','mcLeagueLogo']:panel['mcNextFixtureTexts'][clip]=Obj(Initialize=lambda o,*a:texts.append(a))
 cfg=Obj(aHomeTeamName=['BARCELONA'],aAwayTeamName=['COMO'],aStadiumName=['STADIUM'],nPosXHomeName=-200,nPosXAwayName=200,nPosXStadiumNameOverride=0)
 fullproto['Initialize'](panel,cfg);assert [x[0] for x in texts]==[['COMO'],['BARCELONA'],['STADIUM']]
 assert panel['mcNextFixtureTexts']['mcHomeName']['_x']==-200
 assert panel['mcNextFixtureTexts']['mcAwayName']['_x']==200
 assert panel['mcNextFixtureTexts']['mcLeagueLogo']['_visible'] and not panel['mcPlayerToWatch']['_visible']
 result['panel_initialization']='passed; no modern player data providers invoked'
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
