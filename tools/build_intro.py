"""Build an experimental FIFA16 bridge around the supplied FC27 FullPanel.
Inputs are local paths; no game files or credentials are distributed by this script.
"""
import argparse,struct,json,hashlib,zipfile
from pathlib import Path
from apt_port import Apt,Code,action,read_big,write_big,U,P
NS9='fc27Components____9';NS10='fc27Components____10'
def store(c,n):c.op(0x87);c.align();c.b.extend(struct.pack('<I',n));c.op(0x17)
def this(c,*members):
 c.reg(1)
 for m in members:c.member(m)
def static(c,field):c.path('game','globalComponents',NS10,'FullPanel',field)
def put(c,obj,name,value):obj(c);c.string(name);value(c);c.op(0x4f)
def prop(name):return lambda c:this(c,name)
def value(n):return lambda c:c.num(n)
def boolean(v):return lambda c:c.op(0x73 if v else 0x74)
def objpath(*parts):return lambda c:this(c,*parts)
def config(c):c.reg(3)
def cfgprop(name):return lambda c:c.reg(3).member(name)
def staticval(name):return lambda c:static(c,name)
def method(c,obj,name,args=()):
 for emit in reversed(args):emit(c)
 c.num(len(args));obj(c);c.call(name)
def empty_sprite(apt):
 frame=apt.append(P(0)+P(0))
 return apt.append(P(5)+P(0x09876543)+P(0)+P(0)+P(1)+P(frame)+P(0))

def filtered(apt,ids):
 _,items=apt.rootitems();items=[i for i in items if U(apt.d,i)==8 and U(apt.d,i+8) in ids];apt.setitems(items)
def isolate(files):
 # Replacements preserve every original APT/CONST offset and numeric field.
 out=files.copy()
 for name in ['0','1']:
  out[name]=out[name].replace(b'overlayComponents_10',NS10.encode()).replace(b'overlayComponents_9',NS9.encode())
 return out
def add_root_action(apt,emit):
 p,c=action(apt,emit);item=apt.append(P(1)+P(p));_,items=apt.rootitems();apt.setitems(items+[item]);return p,c

def panel_initialize(c):
 put(c,lambda c:c.reg(1),'m_ConfigFullPanel',lambda c:c.reg(3))
 # Only the next-fixture/head-to-head mode is initialized. FC27's original
 # Initialize also dereferences modern player providers for unused PTW modes.
 for clip,arr,fmt in [('mcAwayName','aAwayTeamName','NEXT_FIXTURE_NAME_CONFIG'),('mcHomeName','aHomeTeamName','NEXT_FIXTURE_NAME_CONFIG'),('mcStadiumName','aStadiumName','NEXT_FIXTURE_STADIUM_CONFIG')]:
  method(c,objpath('mcNextFixtureTexts',clip),'Initialize',[cfgprop(arr),staticval(fmt)])
 for clip in ['mcPlayerToWatch','mcTableView','mcTitle']:put(c,objpath(clip),'_visible',boolean(False))
 put(c,objpath('mcNextFixtureTexts'),'_visible',boolean(True))
 for clip in ['mcScoreHome','mcScoreAway','mcMinutes','mcDivider']:
  put(c,objpath('mcNextFixtureTexts',clip),'_visible',boolean(False))
 put(c,objpath('mcNextFixtureTexts','mcLeagueLogo'),'_visible',boolean(True))
 for field,const in [('m_nAwayCrestNextFixtureFinalXPos','AWAY_CREST_FINAL_POS_X'),('m_nHomeCrestNextFixtureFinalXPos','HOME_CREST_FINAL_POS_X')]:put(c,lambda c:c.reg(1),field,staticval(const))
 for field,cfg in [('m_nAwayTeamFinalPosX','nPosXAwayName'),('m_nHomeTeamFinalPosX','nPosXHomeName')]:put(c,lambda c:c.reg(1),field,cfgprop(cfg))
 for clip,final in [('mcAwayCrest','AWAY_CREST_FINAL_POS_X'),('mcHomeCrest','HOME_CREST_FINAL_POS_X')]:
  put(c,objpath('mcNextFixtureTexts',clip),'_x',staticval(final));put(c,objpath('mcNextFixtureTexts',clip),'_y',staticval('CREST_DEFAULT_POS_Y'))
 for clip,cfg in [('mcAwayName','nPosXAwayName'),('mcHomeName','nPosXHomeName')]:
  put(c,objpath('mcNextFixtureTexts',clip),'_x',cfgprop(cfg));put(c,objpath('mcNextFixtureTexts',clip),'_y',staticval('TEAM_NAME_DEFAULT_POS_Y'))
 put(c,objpath('mcNextFixtureTexts','mcStadiumName'),'_x',cfgprop('nPosXStadiumNameOverride'))
 put(c,objpath('mcNextFixtureTexts','mcStadiumName'),'_y',staticval('STADIUM_TEXT_DEFAULT_POX_Y'))

def update(c):
 # Reject incomplete game updates before touching the currently displayed intro.
 c.reg(3).op(0x76,0x49);c.branch('update_return')
 c.string('|').num(1).reg(3).string('split').op(0x52);store(c,4)
 c.reg(4).member('length').num(9).op(0x48);c.branch('update_return')
 # Ignore identical updates while visible, so the entrance cannot restart each tick.
 this(c,'_fc27Active');c.op(0x12);c.branch('update_begin')
 this(c,'_fc27LastData');c.reg(3).op(0x49);c.branch('update_return')
 c.label('update_begin')
 put(c,lambda c:c.reg(1),'_fc27LastData',lambda c:c.reg(3))
 put(c,lambda c:c.reg(1),'_fc27Active',boolean(True))
 put(c,lambda c:c.reg(1),'_visible',boolean(True))
 put(c,lambda c:c.reg(1),'_alpha',value(100))
 for field,index in [('m_sTeamNameHome15_upper',3),('m_sTeamNameAway15_upper',6),('m_sStadiumName_upper',2)]:
  def text(c,i=index):c.reg(4).num(i).op(0x4e).num(1).reg(2).member('ION_Localization').string('ToUpperCase').op(0x52)
  put(c,lambda c:c.reg(1),field,text)
 for field,index in [('m_nHomeCrestId',5),('m_nAwayCrestId',8)]:put(c,lambda c:c.reg(1),field,lambda c,i=index:c.reg(4).num(i).op(0x4e))
 put(c,lambda c:c.reg(1),'m_sStadiumCity_upper',lambda c:c.string(''))
 # Cancel an earlier exit callback before restarting the native overlay.
 for target in [objpath('mcPanel','mcMaskFullPanel'),objpath('mcPanel','mcNextFixtureTexts'),objpath('mcPanel','mcContentHolder')]:
  method(c,lambda c:c.path('game','globalClasses','AnimationManager'),'ClearAnimations',[target])
 method(c,lambda c:c.reg(1),'Init')
 # Native FIFA16 asset resolver also handles Creation Centre crests.
 for side,index in [('Home',5),('Away',8)]:
  method(c,lambda c:c.reg(2),'getCreationCentreAsset',[lambda c:c.string('crest/dark'),lambda c,i=index:c.reg(4).num(i).op(0x4e),objpath('mcPanel','mcNextFixtureTexts','mc'+side+'Crest'),value(100)])
 c.label('update_return')
def remove(c):
 put(c,lambda c:c.reg(1),'_fc27Active',boolean(False))
 # Keep FC27's exit, then run a native completion callback.
 this(c,'_fc27Finish');c.reg(1).num(2).path('cafe','utility','Delegate').string('Create').op(0x52)
 c.num(1);this(c,'mcPanel');c.call('AnimateOut')
def finish(c):
 # If Update arrived during the exit, an old callback must not hide the new intro.
 this(c,'_fc27Active');c.branch('finish_return')
 put(c,lambda c:c.reg(1),'_visible',boolean(False))
 method(c,lambda c:c.reg(1),'__fc27NativeShutdown')
 c.label('finish_return')
def register(c):pass

def wrapper_bridge(c):
 c.path('game','overlays','Champions','overlay_10042','prototype');store(c,0)
 put(c,lambda c:c.reg(0),'__fc27NativeShutdown',lambda c:c.reg(0).member('Shutdown'))
 c.function('Update',update,1);c.function('Remove',remove);c.function('_fc27Finish',finish)
 c.function('RegisterComponentForShutdown',register,1)

def panel_bridge(c):
 c.path('game','globalComponents',NS10,'FullPanel','prototype');store(c,0)
 c.function('Initialize',panel_initialize,1)

def patch_fonts(apt):
 # Replace only complete property-read chains. Padding uses push-zero/pop,
 # preserving bytecode positions, jump distances, and stack effects.
 c=apt.c;const=[]
 for t,v in apt.const:const.append(c[v:c.index(0,v)].decode() if t==1 else v)
 d=apt.d
 from inspect_apt import pools
 allpools=pools(d,const)
 for poolindex,(off,cp) in enumerate(allpools):
  region_end=allpools[poolindex+1][0] if poolindex+1<len(allpools) else len(d)
  names=['game','globalClasses','StyleManager']
  if not all(s in cp for s in names):continue
  replacements=[]
  for font in ['FONT_NAME_CHAMPIONS_REGULAR','FONT_NAME_CHAMPIONS_LIGHT']:
   if font not in cp:continue
   i=len(cp)+len(replacements);assert i<256
   pat=bytes([0xae,cp.index('game'),0xaf,cp.index('globalClasses'),0xaf,cp.index('StyleManager'),0xaf,cp.index(font)])
   replacement=bytes([0xa2,i,0x59,0x17,0x59,0x17,0x59,0x17]);pos=off
   while True:
    pos=d.find(pat,pos,region_end)
    if pos<0:break
    d[pos:pos+8]=replacement;pos+=8
   replacements.append(apt.addconst('Champions Regular'))
  if replacements:
   a=(off+8)&~7;n=U(d,a);p=U(d,a+8);new=apt.append(d[p:p+8*n]+b''.join(P(i) for i in replacements));d[a:a+16]=P(n+len(replacements))+P(new)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--fc27',required=True,type=Path);ap.add_argument('--native',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);a=ap.parse_args();out=a.output
 fc=a.fc27;native=a.native
 comp9=Apt(isolate(read_big(fc/'globalComponents/overlayComponents_9/overlayComponents_9.big')))
 filtered(comp9,{210,211,219,86})
 # Only MultiText is used by this intro. Neither FB rendering nor ImageLoader
 # is used in that character graph; clear imports and their unused references.
 comp9.d[comp9.root+0x54:comp9.root+0x58]=struct.pack('<I',0)
 comp9.d[comp9.root+0x58:comp9.root+0x60]=P(0)
 table=U(comp9.d,comp9.root+0x40);empty=empty_sprite(comp9)
 for char in [64,199]:comp9.d[table+8*char:table+8*char+8]=P(empty)
 comp10=Apt(isolate(read_big(fc/'globalComponents/overlayComponents_10/overlayComponents_10.big')))
 filtered(comp10,{183,184,150})
 # Remove BasePlayerDisplay import, unused in the next-fixture mode.
 n=struct.unpack_from('<I',comp10.d,comp10.root+0x54)[0];p=U(comp10.d,comp10.root+0x58);entries=[]
 for i in range(n):
  e=bytes(comp10.d[p+32*i:p+32*i+32])
  if U(e,16)!=136:entries.append(e)
 comp10.d[comp10.root+0x54:comp10.root+0x58]=struct.pack('<I',len(entries));new=comp10.append(b''.join(entries));comp10.d[comp10.root+0x58:comp10.root+0x60]=P(new)
 table=U(comp10.d,comp10.root+0x40);empty=empty_sprite(comp10);comp10.d[table+136*8:table+137*8]=P(empty)
 patch_fonts(comp10);add_root_action(comp10,panel_bridge)
 wrap=Apt(isolate(read_big(fc/'Overlays/Champions/overlay_10042.big')))
 wrap.replaceconst('overlay_Common_042','BaseOverlay');add_root_action(wrap,wrapper_bridge)
 files9=comp9.finish();files10=comp10.finish();fileswrap=wrap.finish()
 write_big(out/f'game/globalComponents/{NS9}/{NS9}.big',files9)
 write_big(out/f'game/globalComponents/{NS10}/{NS10}.big',files10)
 write_big(out/'game/overlays/overlay_9042.big',fileswrap)
 # Include the unchanged v0.1 native baseline, since its ASI plugin is disabled.
 with zipfile.ZipFile(Path(__file__).resolve().parent.parent/'fc27_nativo_v01_prueba.zip') as z:
  for overlay in ['9002','9018']:
   (out/f'game/overlays/overlay_{overlay}.big').write_bytes(z.read(f'FC27_NATIVO_v01/game/overlays/overlay_{overlay}.big'))
 for overlay in ['9002','9018','9042']:
  backup=out/f'RESTAURAR/game/overlays/overlay_{overlay}.big';backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes((native/f'game/overlays/overlay_{overlay}.big').read_bytes())
 fonts=out/'fonts';fonts.mkdir(exist_ok=True)
 for f in (native/'fonts').glob('Champions*.ttf'):(fonts/f.name).write_bytes(f.read_bytes())
 report={'version':'0.2-intro-experimental','runtime_tested':False,'scope':'new intro; unchanged v0.1 native scoreboard and lineup baseline included','native_data_indices':{'stadium':2,'home_name':3,'home_crest':5,'away_name':6,'away_crest':8},'fc27_animation_functions_preserved':['InitAnimation','AnimateIn','AnimateOut'],'files':{str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file() and p.name!='MANIFEST.json'}}
 (out/'MANIFEST.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
