"""ZFLAG v2.0.59: full offline FastFlag archive in existing native app Library.
Pure catalog/React UI change. Does not alter any native injection, memory access or Roblox restriction.
"""
from __future__ import annotations
from pathlib import Path
import json,re,sys
ROOT=Path(sys.argv[1]);REPO=Path(sys.argv[2]) if len(sys.argv)>2 else Path.cwd()
arch=REPO/'library/imports'
original=json.loads((arch/'ALL_FFLAGS_EVERYTHING_COMBINED.json').read_text(encoding='utf-8'))
merged=json.loads((arch/'ZFLAG_ALL_FLAGS_6_NEW_UPLOADS_MERGED.json').read_text(encoding='utf-8'))
ALLOW=set('''DFIntCSGLevelOfDetailSwitchingDistance DFIntCSGLevelOfDetailSwitchingDistanceL12 DFIntCSGLevelOfDetailSwitchingDistanceL23 DFIntCSGLevelOfDetailSwitchingDistanceL34 FFlagHandleAltEnterFullscreenManually DFFlagTextureQualityOverrideEnabled DFIntTextureQualityOverride FIntDebugForceMSAASamples DFFlagDisableDPIScale FFlagDebugGraphicsPreferD3D11 FFlagDebugSkyGray DFFlagDebugPauseVoxelizer DFIntDebugFRMQualityLevelOverride FIntFRMMaxGrassDistance FIntFRMMinGrassDistance FFlagDebugGraphicsPreferVulkan FFlagDebugGraphicsPreferOpenGL FIntGrassMovementReducedMotionFactor'''.split())
CATS=[('Networking & Ping',r'net|packet|raknet|ping|connection|mtu|socket|tcp|udp|replicat|sender|receiver|latency|bandwidth|http|websocket|reliab|rtt'),('Caching & Memory',r'cach|memory|mem|heap|alloc|gc|garbage|pool|buffer|reclaim|compress|decompress|warmup|preload'),('Physics & Movement',r'physic|humanoid|collision|gravity|force|raycast|solver|simulat|velocity|jump|movement|damping|penetrat|ragdoll|floor|stick|assembly|character|position|orientation|hipheight'),('FPS & Scheduling',r'fps|frame|task|schedul|thread|timing|renderstep|framerate|targetfps|vsync|tick|heartbeat'),('Textures & Lighting',r'texture|light|shadow|voxel|terrain|grass|material|postfx|bloom|sun|moon|sky|anti.?alias|msaa|pixel|shader|luminance|reflect|ambient'),('Rendering & Graphics',r'graphic|render|vulkan|opengl|d3d|direct3d|gpu|csg|lod|draw|display|camera|viewport|quality|geometry|mesh|frustum'),('UI & Accessibility',r'gui|ui|menu|interface|font|chat|tooltip|chrome|topbar|badge|input|accessib|scroll|keyboard|focus|mouse|cursor|dialog|fullscreen|dpi|localiz|language'),('Audio & Voice',r'sound|audio|voice|microphone|vc|volume|spatialaudio|acoust|occlusi|haptic'),('Security & Telemetry',r'security|telemetry|anticheat|auth|permission|moderation|reportabuse|crash|logger|analytics|tracking|abuse'),('Assets & Loading',r'asset|load|stream|download|content|prefetch|request|cdn|fetch')]
KNOWN={'DFIntTaskSchedulerTargetFps':'Historical FPS scheduler target. Not on published 2025 Player allowlist; use Roblox frame-rate settings.','DFIntS2PhysicsSenderRate':'Historical physics sender-rate configuration. Not on published Player allowlist; may have no effect or be disruptive.','DFIntConnectionMTUSize':'Historical network MTU override. Not on published Player allowlist; incorrect values may worsen connectivity.','DFFlagTextureQualityOverrideEnabled':'Enables a texture quality override.','DFIntTextureQualityOverride':'Texture quality override, typically 0–3; higher values may use more VRAM.','FFlagDebugGraphicsPreferD3D11':'Requests the Direct3D 11 backend. Choose one renderer preference at a time.','FFlagDebugGraphicsPreferVulkan':'Requests Vulkan rendering; performance varies by driver.','FFlagDebugGraphicsPreferOpenGL':'Requests OpenGL graphics backend.','FIntDebugForceMSAASamples':'Requested MSAA samples. Higher samples increase GPU cost.','DFFlagDisableDPIScale':'Disables DPI-related render downscaling; may improve clarity at higher GPU cost.','FFlagHandleAltEnterFullscreenManually':'Changes Alt+Enter fullscreen handling.','FIntGrassMovementReducedMotionFactor':'Grass-motion reduction setting.','DFIntDebugFRMQualityLevelOverride':'Graphics quality-level override.','FFlagDebugSkyGray':'Gray-sky debug rendering setting.','DFFlagDebugPauseVoxelizer':'Voxelizer pause option, which can affect lighting.','FIntFRMMinGrassDistance':'Minimum visible grass distance.','FIntFRMMaxGrassDistance':'Maximum visible grass distance.'}
for k in ALLOW:
 if k.startswith('DFIntCSGLevelOfDetailSwitchingDistance'):KNOWN[k]='Controls level-of-detail switching distance for CSG geometry.'
def normalize(k):
 return k.replace('"','').split(':',1)[0].strip() if k.startswith('"') else k
def category(k):
 return next((name for name,regex in CATS if re.search(regex,k,re.I)),'Other & Experimental')
def value_str(v):
 if v is True:return 'true'
 if v is False:return 'false'
 if v is None:return 'null'
 return str(v)
def type_str(v):
 if isinstance(v,bool) or str(v).lower() in ('true','false'):return 'boolean'
 if re.fullmatch(r'-?\d+',str(v)) and len(str(v))<16:return 'integer'
 if re.fullmatch(r'-?\d+\.\d+',str(v)):return 'number'
 return 'string'
items={}
for source,dat in [('merged 10,518-key JSON',merged),('earlier 8,440-key JSON',original)]:
 for raw,v in dat.items():
  k=normalize(raw)
  if not k:continue
  item=items.setdefault(k,{'name':k,'values':[],'raw_names':[],'sources':[]})
  if source not in item['sources']:item['sources'].append(source)
  if raw!=k:item['raw_names'].append(raw)
  if value_str(v) not in item['values']:item['values'].append(value_str(v))
for k,item in items.items():
 cat=category(k);v=item['values'][0]
 human=re.sub(r'(?<=[a-z0-9])(?=[A-Z])',' ',re.sub(r'^(?:DFFlag|FFlag|DFInt|FInt|FString|DString|FLog|DFLog)','',k)).strip() or k
 entry={'name':k,'value':v,'category':cat,'description':KNOWN.get(k,f'Name suggests internal {cat.lower()} behavior related to "{human}". Meaning, supported values and effect are not documented; description is inferred.'),'evidence':'documented' if k in ALLOW else ('advanced' if cat in ('Networking & Ping','Physics & Movement') else 'archived'),'type':type_str(v),'source':' + '.join(item['sources']),'values':item['values'],'raw_names':item['raw_names']}
 if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]+',k):
  entry['type']='unknown'
  entry['evidence']='archived'
  entry['description']='Nonstandard archive key. Preserved for reference only; excluded from configuration editing. '+entry['description']
 items[k]=entry
ordered=sorted(items.values(),key=lambda d:d['name'].lower())
assert len(ordered)==15965, f'Expected 15,965 distinct flags, got {len(ordered)}'
assert sum(x['evidence']=='documented' for x in ordered)>=15
folder=ROOT/'src/data';folder.mkdir(parents=True,exist_ok=True)
(folder/'flag-library.json').write_text(json.dumps(ordered,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
PRE={
'Low-end / integrated GPU':{'DFFlagTextureQualityOverrideEnabled':True,'DFIntTextureQualityOverride':1,'DFIntCSGLevelOfDetailSwitchingDistance':100,'DFIntCSGLevelOfDetailSwitchingDistanceL12':75,'DFIntCSGLevelOfDetailSwitchingDistanceL23':100,'DFIntCSGLevelOfDetailSwitchingDistanceL34':150,'FIntGrassMovementReducedMotionFactor':0},
'Balanced / mid-range':{'DFFlagTextureQualityOverrideEnabled':True,'DFIntTextureQualityOverride':2,'DFIntCSGLevelOfDetailSwitchingDistance':2000,'DFIntCSGLevelOfDetailSwitchingDistanceL12':1000,'DFIntCSGLevelOfDetailSwitchingDistanceL23':1500,'DFIntCSGLevelOfDetailSwitchingDistanceL34':2500,'FIntDebugForceMSAASamples':2,'FIntGrassMovementReducedMotionFactor':50},
'High fidelity':{'DFFlagTextureQualityOverrideEnabled':True,'DFIntTextureQualityOverride':3,'DFIntCSGLevelOfDetailSwitchingDistance':10000,'DFIntCSGLevelOfDetailSwitchingDistanceL34':10000,'FIntDebugForceMSAASamples':4},
'Minimal grass':{'FIntFRMMinGrassDistance':0,'FIntFRMMaxGrassDistance':0,'FIntGrassMovementReducedMotionFactor':0},
'High DPI clarity':{'DFFlagDisableDPIScale':True},'MSAA 2x':{'FIntDebugForceMSAASamples':2},'MSAA 4x':{'FIntDebugForceMSAASamples':4},'Direct3D 11':{'FFlagDebugGraphicsPreferD3D11':True},'Vulkan':{'FFlagDebugGraphicsPreferVulkan':True},'OpenGL':{'FFlagDebugGraphicsPreferOpenGL':True},'Alt+Enter fullscreen':{'FFlagHandleAltEnterFullscreenManually':True}}
premades=[]
for name,flags in PRE.items():
 assert set(flags).issubset(ALLOW)
 premades.append({'name':name,'category':'Allowlisted graphics / display','status':'allowlisted','source':'Roblox published allowlist; Fishstrap/Bloxstrap examples','description':'Uses published allowlisted names. Not independently tested against current in-game performance or all hardware.','flags':flags})
premades.append({'name':'Legacy FPS 240','category':'Historical FPS','status':'historical','source':'Pre-2025 community presets','description':'Historical example not on the published Roblox Player allowlist; do not assume it works.','flags':{'DFIntTaskSchedulerTargetFps':240}})
md=(arch/'community-collection.md').read_text(encoding='utf-8')
for m in re.finditer(r'```(?:json)?\s*\n(\{[\s\S]*?\})\s*```',md):
 titles=re.findall(r'^###\s+(.+)$',md[:m.start()],re.M)
 name=titles[-1] if titles else 'Historical flag recipe'
 try:f=json.loads(m.group(1))
 except:continue
 if isinstance(f,dict) and f:
  premades.append({'name':name,'category':'Historical community / supplied', 'status':'historical','source':'Uploaded CfwSky historical collection','description':'Archived example only. Not verified on Roblox Player; may be outdated, ineffective, or disruptive.','flags':f})
txt=(arch/'ultimate-fastflag-list.txt').read_text(encoding='utf-8').splitlines()
for i,line in enumerate(txt):
 if '{' not in line or '}' not in line or len(line)>3000:continue
 try:f=json.loads(line[line.index('{'):line.rindex('}')+1])
 except:continue
 if not isinstance(f,dict) or not f:continue
 title=txt[i-1].strip() if i>0 else 'Historical flags'
 if not title or len(title)>68 or title.startswith('{'):title='Historical community flags'
 premades.append({'name':title,'category':'Historical community / supplied','status':'historical','source':'Uploaded UltimateFastFlagList 2024 archive','description':'Archived example only. Not a current working claim; validate each name against Roblox restrictions.','flags':f})
(folder/'flag-premades.json').write_text(json.dumps(premades,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
file=ROOT/'src/FlagLibrary.tsx';s=file.read_text(encoding='utf-8')
def patch(a,b):
 global s
 count=s.count(a)
 if count!=1:raise RuntimeError('UI patch missing anchor ('+str(count)+'): '+a[:110])
 s=s.replace(a,b,1)
patch('import entries from "./data/flag-library.json"','import entries from "./data/flag-library.json"\nimport premades from "./data/flag-premades.json"\nimport "./FlagLibraryEnhanced.css"')
patch('type Flag = {name:string; value:string; category:string; description:string; evidence:string; type:string; source:string}', 'type Flag = {name:string; value:string; category:string; description:string; evidence:string; type:string; source:string; values?:string[]; raw_names?:string[]}')
patch('const FLAGS = entries as Flag[]','const FLAGS = entries as Flag[]\nconst PREMADES = premades as Array<{name:string;category:string;status:"allowlisted"|"historical";description:string;source:string;flags:Record<string,string|number|boolean>}>')
patch('  const [goal,setGoal]=useState("FPS / display")','''  const [goal,setGoal]=useState("FPS / display")
  const [page,setPage]=useState(0)
  const [showPremades,setShowPremades]=useState(false)
  const [premadeFilter,setPremadeFilter]=useState("allowlisted")
  const [presetPage,setPresetPage]=useState(0)
  const [selectedValue,setSelectedValue]=useState<Record<string,string>>({})''')
needle='const filtered=useMemo(()=>FLAGS.filter(f=>(category==="All"||category===f.category)&&(!showOnlyDocumented||f.evidence==="documented")&&`${f.name} ${f.description} ${f.category}`.toLowerCase().includes(search.toLowerCase())).slice(0,200),[category,search,showOnlyDocumented])'
patch(needle,'''const filtered=useMemo(()=>FLAGS.filter(f=>(category==="All"||category===f.category)&&(!showOnlyDocumented||f.evidence==="documented")&&(f.name+" "+f.description+" "+f.category+" "+f.value).toLowerCase().includes(search.toLowerCase())),[category,search,showOnlyDocumented])
  const shown=filtered.slice(page*80,(page+1)*80)
  const pageCount=Math.max(1,Math.ceil(filtered.length/80))
  const visiblePresets=PREMADES.filter(p=>premadeFilter==="all"||(premadeFilter==="allowlisted"?p.status==="allowlisted":p.status==="historical"))
  const shownPresets=visiblePresets.slice(presetPage*18,(presetPage+1)*18)
  function withValue(f:Flag){return parsedValue({...f,value:selectedValue[f.name]??f.value})}''')
patch('  function mergeFlags(flags:Flag[]){onMerge(Object.fromEntries(flags.map(f=>[f.name,parsedValue(f)])));setSelected([])}','  function mergeFlags(flags:Flag[]){onMerge(Object.fromEntries(flags.map(f=>[f.name,withValue(f)])));setSelected([])}')
patch('  return <div className="view-content library-page">','''  return <div className="view-content library-page zflag-library-full">''')
patch('Search imported flags, inspect their value types, and build a draft. Imported does not mean Roblox currently supports a flag.', 'Search every recovered flag, examine archived values and browse curated premades. Archived does not mean currently supported by Roblox.')
patch('    <div className="library-toolbar">','''    <div className="zfl-version-note"><b>15,965 imported flag names</b> · Roblox’s published Player allowlist contains 18 entries. This library is an archive, not a bypass or claim that every flag works. Use published allowlisted names for basic configs; verify actual effects yourself.</div>
    <div className="library-premades-controls"><button type="button" className="library-primary" onClick={()=>setShowPremades(v=>!v)}>{showPremades?"Hide":"Browse"} {PREMADES.length} premade configs</button>{showPremades&&<select value={premadeFilter} onChange={e=>{setPremadeFilter(e.target.value);setPresetPage(0)}}><option value="allowlisted">Allowlisted names</option><option value="historical">Historical / unverified</option><option value="all">All premades</option></select>}</div>
    {showPremades&&<><div className="zfl-native-preset-grid">{shownPresets.map((p,i)=><div className="zfl-native-preset" key={p.name+i}><small className={p.status==="allowlisted"?"allow":"archive"}>{p.status==="allowlisted"?"ALLOWLISTED NAMES · NOT GAME TESTED":"HISTORICAL / UNVERIFIED"}</small><h3>{p.name}</h3><p>{p.description}</p><pre>{JSON.stringify(p.flags,null,2)}</pre><footer><span>{Object.keys(p.flags).length} flags · {p.source}</span><button type="button" className="library-primary" onClick={()=>onMerge(p.flags)}><Plus size={13}/> Add to editor</button></footer></div>)}</div><div className="zfl-native-pages"><button disabled={presetPage===0} onClick={()=>setPresetPage(v=>Math.max(0,v-1))}>Previous</button><span>{presetPage+1} / {Math.max(1,Math.ceil(visiblePresets.length/18))}</span><button disabled={(presetPage+1)*18>=visiblePresets.length} onClick={()=>setPresetPage(v=>v+1)}>Next</button></div></>}
    <div className="library-toolbar">''')
patch('value={search} onChange={e=>setSearch(e.target.value)}','value={search} onChange={e=>{setSearch(e.target.value);setPage(0)}}')
patch('onChange={e=>setShowOnlyDocumented(e.target.checked)}','onChange={e=>{setShowOnlyDocumented(e.target.checked);setPage(0)}}')
patch('onClick={()=>setCategory(c)}','onClick={()=>{setCategory(c);setPage(0)}}')
patch('    <div className="library-results">{filtered.map(f=>','    <div className="library-results">{shown.map(f=>')
patch('<code>{f.value}</code>', '<div className="zfl-native-value"><input aria-label={"Value for "+f.name} value={selectedValue[f.name]??f.value} onChange={e=>setSelectedValue(v=>({...v,[f.name]:e.target.value}))}/>{f.values&&f.values.length>1&&<details><summary>{f.values.length} values</summary>{f.values.map((v,i)=><button type="button" key={i} onClick={()=>setSelectedValue(old=>({...old,[f.name]:v}))}>{v}</button>)}</details>}</div>')
patch('Displaying {filtered.length} matching entries (first 200).', 'Found {filtered.length.toLocaleString()} matching entries; page {page+1} / {pageCount}.')
patch('    <p className="library-disclaimer">', '''    <div className="zfl-native-pages"><button type="button" disabled={page===0} onClick={()=>setPage(p=>Math.max(0,p-1))}>Previous</button><span>Page {page+1} of {pageCount}</span><button type="button" disabled={page+1>=pageCount} onClick={()=>setPage(p=>p+1)}>Next</button></div>
    <p className="library-disclaimer">''')
file.write_text(s,encoding='utf-8')
(ROOT/'src/FlagLibraryEnhanced.css').write_text('''
.zflag-library-full{color:#eee}.zflag-library-full .zfl-version-note{background:#050505;border:1px solid #303030;border-left:3px solid #eee;padding:15px 17px;margin:14px 0 20px;border-radius:9px;color:#a9a9a9;font-size:12px}.zflag-library-full .zfl-version-note b{color:#fff}
.library-premades-controls{display:flex;gap:10px;margin:0 0 15px;align-items:center;flex-wrap:wrap}.library-premades-controls select{padding:10px;border-radius:7px;border:1px solid #3d3d3d;background:#080808;color:#eee}
.zfl-native-preset-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:12px;margin:12px 0 20px}.zfl-native-preset{border:1px solid #333;border-radius:11px;padding:17px;background:#070707;color:#eee;min-width:0}.zfl-native-preset small{font:10px Consolas,monospace;color:#aaa}.zfl-native-preset small.allow{color:#ddd}.zfl-native-preset small.archive{color:#cba6a6}.zfl-native-preset h3{font-size:17px;margin:10px 0 8px}.zfl-native-preset p{font-size:12px;color:#aaa;line-height:1.5;min-height:50px}.zfl-native-preset pre{font:11px/1.5 Consolas,monospace;white-space:pre-wrap;overflow-wrap:anywhere;max-height:140px;min-height:95px;overflow:auto;padding:12px;background:#020202;border:1px solid #272727;border-radius:6px}.zfl-native-preset footer{display:flex;justify-content:space-between;gap:10px;align-items:end}.zfl-native-preset footer span{font-size:10px;color:#888}.zfl-native-preset footer button{flex-shrink:0}
.zfl-native-pages{display:flex;justify-content:center;align-items:center;gap:18px;margin:18px 0 24px;color:#999}.zfl-native-pages button{border:1px solid #444;border-radius:6px;background:#111;color:#eee;padding:9px 13px}.zfl-native-pages button:disabled{opacity:.33;cursor:default}.zfl-native-value{display:flex;flex-direction:column;min-width:0;gap:4px}.zfl-native-value input{width:100%;min-width:80px;border:1px solid #333;border-radius:6px;background:#000;color:#f4f4f4;font:11px Consolas,monospace;padding:8px}.zfl-native-value input:focus{border-color:#bbb;outline:0}.zfl-native-value details{color:#aaa;font-size:10px;max-height:110px;overflow:auto}.zfl-native-value details button{display:block;padding:5px 7px;border:1px solid #333;background:#0e0e0e;color:#ccc;margin:3px 0;border-radius:4px;word-break:break-all;max-width:140px;text-align:left}
@media(max-width:900px){.zfl-native-preset-grid{grid-template-columns:1fr}.zfl-native-value input{max-width:160px}}
''',encoding='utf-8')
# UI/library change only. Do not touch native backend or injector engine.
for rel in ('package.json','src-tauri/tauri.conf.json'):
 p=ROOT/rel;obj=json.loads(p.read_text(encoding='utf-8'));assert obj.get('version')=='2.0.58',rel;obj['version']='2.0.59';p.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
cargo=ROOT/'src-tauri/Cargo.toml';txt=cargo.read_text(encoding='utf-8');txt,n=re.subn(r'(?m)^version = "2\.0\.58"$','version = "2.0.59"',txt,count=1);assert n==1,'Cargo version not found';cargo.write_text(txt,encoding='utf-8')
for directory in (ROOT/'tests',ROOT/'scripts'):
 for p in directory.rglob('*'):
  if not p.is_file() or p.suffix.lower() not in ('.py','.ps1','.ts','.tsx','.js','.json'):continue
  try:raw=p.read_text(encoding='utf-8')
  except UnicodeError:continue
  if '2.0.58' in raw:p.write_text(raw.replace('2.0.58','2.0.59'),encoding='utf-8')
app=ROOT/'src/App.tsx';raw=app.read_text(encoding='utf-8');app.write_text(raw.replace('2.0.58','2.0.59'),encoding='utf-8')
# Preserve invalid identifier records while preventing editor insertion.
integrity=ROOT/'tests/test_release_integrity.py'
content=integrity.read_text(encoding='utf-8')
check="self.assertRegex(entry['name'],r'^[A-Za-z][A-Za-z0-9_]+$')"
assert content.count(check)==1,'Integrity assertion changed'
replacement=(
"if entry.get('type') == 'unknown' and entry.get('description','').startswith('Nonstandard archive key'):\n"
"                self.assertNotRegex(entry['name'],r'^[A-Za-z][A-Za-z0-9_]+$')\n"
"            else:\n"
"                self.assertRegex(entry['name'],r'^[A-Za-z][A-Za-z0-9_]+$')"
)
integrity.write_text(content.replace(check,replacement),encoding='utf-8')
# Use deterministic fixture timestamp to avoid Windows file-time rounding issues.
game_test=ROOT/'tests/test_tab_game_profiles_254.py'
fixture=game_test.read_text(encoding='utf-8')
old_fixture='detect_game_from_logs(log_dir=Path(td))'
assert fixture.count(old_fixture)==1,'Game fixture changed'
game_test.write_text(fixture.replace(old_fixture,'detect_game_from_logs(log_dir=Path(td), now=f.stat().st_mtime+1)'),encoding='utf-8')
# App v259 smoke assertions
assert len(ordered)==15965 and len(premades)>=12
assert 'const shown=filtered.slice(page*80' in s
assert '15,965 imported flag names' in s
assert 'src-tauri' in str(cargo)
print('ZFLAG v2.0.59 library:',len(ordered),'flags,',len(premades),'premade configs; frontend only, native engine unchanged')
