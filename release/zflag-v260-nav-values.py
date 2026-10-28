"""ZFLAG v2.0.60: polished centered navigation and safe, typed Flag Library values.
Applies after v2.0.59 full-library patch. Frontend-only, no injector behavior changes.
"""
from pathlib import Path
import json,re,sys
ROOT=Path(sys.argv[1])
def swap(file,old,new):
 text=file.read_text(encoding="utf-8")
 if text.count(old)!=1:raise RuntimeError(f"{file.relative_to(ROOT)}: {text.count(old)} anchors for {old[:100]!r}")
 file.write_text(text.replace(old,new,1),encoding="utf-8")
def typed_catalog():
 file=ROOT/"src/data/flag-library.json"
 data=json.loads(file.read_text(encoding="utf-8"))
 changed=0; unknown=0
 for entry in data:
  name=entry.get("name","");v=str(entry.get("value","")).strip()
  previous=entry.get("type")
  # FastFlag prefix defines the JSON value type. Archive contents may be inconsistent.
  if name.startswith(("FFlag","DFFlag","SFFlag")):
   entry["type"]="boolean" if v.lower() in ("true","false") else "unknown"
  elif name.startswith(("DFInt","FInt","SInt")):
   entry["type"]="integer" if re.fullmatch(r"[+-]?\d+",v) and len(v.lstrip("-+"))<=15 else "unknown"
  elif name.startswith(("DFString","FString","SString")):
   entry["type"]="string"
  elif name.startswith(("FLog","DFLog")):
   entry["type"]="integer" if re.fullmatch(r"[+-]?\d+",v) else "unknown"
  elif name.startswith(("DFFloat","FFloat","DFDouble","FDouble")):
   entry["type"]="number" if re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)",v) else "unknown"
  # Names from broad internal dumps without a prefix retain their source type;
  # preserve them for search and explicitly mark them unverified.
  if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]+", name):
   entry["type"]="unknown"
  if entry["type"]!=previous:changed+=1
  if entry["type"]=="unknown":
   unknown+=1
   if "archive" not in entry.get("description","").lower():
    entry["description"]+=" [Archived value/type inconsistent or unverified; correct before exporting.]"
  entry["value_source"]="Archived example; not a guaranteed default or currently supported value"
 file.write_text(json.dumps(data,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
 print("Catalog:",len(data),"flags,",changed,"type corrections,",unknown,"require manual type review")
typed_catalog()
lib=ROOT/"src/FlagLibrary.tsx"
swap(lib,'  const [selectedValue,setSelectedValue]=useState<Record<string,string>>({})','''  const [selectedValue,setSelectedValue]=useState<Record<string,string>>({})
  const [valueError,setValueError]=useState("")''')
swap(lib,'''function parsedValue(flag: Flag): string|number|boolean {
  if(flag.type === "boolean") return flag.value.toLowerCase() === "true"
  if(flag.type === "integer" || flag.type === "number") return Number(flag.value)
  return flag.value
}''','''function parsedValue(flag: Flag): string|number|boolean {
  const raw=String(flag.value).trim()
  if(flag.type === "unknown") throw new Error(flag.name+" has no confirmed value type. Review an archived key before adding.")
  if(flag.type === "boolean") {
    if(!/^(true|false)$/i.test(raw)) throw new Error(flag.name+": value must be true or false.")
    return raw.toLowerCase()==="true"
  }
  if(flag.type === "integer") {
    if(!/^-?\\d+$/.test(raw)) throw new Error(flag.name+": value must be an integer.")
    const num=Number(raw)
    if(!Number.isSafeInteger(num)) throw new Error(flag.name+": integer exceeds safe precision.")
    return num
  }
  if(flag.type === "number") {
    if(!/^-?(?:\\d+(?:\\.\\d*)?|\\.\\d+)$/.test(raw)) throw new Error(flag.name+": value must be a number.")
    const num=Number(raw)
    if(!Number.isFinite(num)) throw new Error(flag.name+": invalid number.")
    return num
  }
  return String(flag.value)
}''')
swap(lib,'  function mergeFlags(flags:Flag[]){onMerge(Object.fromEntries(flags.map(f=>[f.name,withValue(f)])));setSelected([])}','''  function mergeFlags(flags:Flag[]){
    try {
      const pairs=flags.map(f=>[f.name,withValue(f)] as const)
      onMerge(Object.fromEntries(pairs))
      setSelected([])
      setValueError("")
    } catch (err) {
      setValueError(err instanceof Error ? err.message : "Please correct the flag value first.")
    }
  }''')
swap(lib,'  const safeSelected=FLAGS.filter(f=>selected.includes(f.name)&&f.type!=="unknown")','''  const safeSelected=FLAGS.filter(f=>selected.includes(f.name)&&f.type!=="unknown")
  function validValue(f:Flag):boolean {try {withValue(f);return true}catch{return false}}''')
oldfield='''<div className="zfl-native-value"><input aria-label={"Value for "+f.name} value={selectedValue[f.name]??f.value} onChange={e=>setSelectedValue(v=>({...v,[f.name]:e.target.value}))}/>{f.values&&f.values.length>1&&<details><summary>{f.values.length} values</summary>{f.values.map((v,i)=><button type="button" key={i} onClick={()=>setSelectedValue(old=>({...old,[f.name]:v}))}>{v}</button>)}</details>}</div>'''
newfield='''<div className="zfl-native-value">
                  <label htmlFor={"zfl-value-"+f.name} className="zfl-native-value-label">ACTUAL VALUE <span>{f.type==="boolean"?"BOOLEAN":f.type==="integer"?"INTEGER":f.type==="number"?"NUMBER":f.type==="string"?"STRING":"REVIEW TYPE"}</span></label>
                  {f.type==="boolean" && /^(true|false)$/i.test(selectedValue[f.name]??f.value)
                    ? <select id={"zfl-value-"+f.name} aria-label={"Actual boolean value for "+f.name} value={(selectedValue[f.name]??f.value).toLowerCase()} onChange={e=>setSelectedValue(v=>({...v,[f.name]:e.target.value}))}><option value="true">true</option><option value="false">false</option></select>
                    : <input id={"zfl-value-"+f.name} type="text" spellCheck={false} aria-label={"Actual JSON value for "+f.name} title={"Archived value; expected "+f.type} inputMode={f.type==="integer"||f.type==="number"?"numeric":"text"} value={selectedValue[f.name]??f.value} onChange={e=>setSelectedValue(v=>({...v,[f.name]:e.target.value}))}/>
                  }
                  {f.type==="unknown" && <span className="zfl-native-warning">Unverified value or type — not added automatically</span>}
                  {!validValue(f) && f.type!=="unknown" && <span className="zfl-native-warning">Invalid {f.type} value; correct before adding</span>}
                  {f.values&&f.values.length>1&&<details><summary>{f.values.length} archived values</summary>{f.values.map((v,i)=><button type="button" key={i} onClick={()=>setSelectedValue(old=>({...old,[f.name]:v}))}>{v}</button>)}</details>}
                </div>'''
swap(lib,oldfield,newfield)
swap(lib,'''    <div className="library-header"><span>FLAG / CATEGORY</span><span>IMPORTED VALUE</span><span>STATUS</span><span>SELECT</span></div>''','''    <div className="library-header"><span>FLAG NAME / DESCRIPTION</span><span>ACTUAL JSON VALUE</span><span>STATUS</span><span>SELECT</span></div>
    {valueError && <div className="zfl-error" role="alert">{valueError}<button type="button" onClick={()=>setValueError("")} aria-label="Dismiss value error">×</button></div>}''')
swap(lib,'''disabled={f.type==="unknown"} className={selected.includes(f.name)?"library-select selected":"library-select"}''','''disabled={f.type==="unknown" || !validValue(f)} title={f.type==="unknown"?"Unverified type; cannot add automatically":!validValue(f)?"Correct actual value before adding":"Select flag"} className={selected.includes(f.name)?"library-select selected":"library-select"}''')
swap(lib,'''<p>{f.description}</p><small>{f.category} · {f.type} · {f.source}</small>''','''<p className="zfl-flag-description"><b>DESCRIPTION</b> {f.description}</p><small>{f.category} · {f.type} · {f.source}</small>''')
app=ROOT/"src/App.tsx"
swap(app,'''    if (next !== view) {
      setView(next)
      setPageKey((key) => key + 1)
    }
    mainScrollRef.current?.scrollTo({ top: 0, behavior: settings.animations ? "smooth" : "auto" })''','''    if (next !== view) {
      // Reset old scroll immediately. Smooth scrolling during a page transition
      // causes the newly-mounted page to slide through the prior scroll depth.
      if (mainScrollRef.current) mainScrollRef.current.scrollTop = 0
      setView(next)
      setPageKey((key) => key + 1)
    } else {
      mainScrollRef.current?.scrollTo({ top: 0, behavior: settings.animations ? "smooth" : "auto" })
    }''')
css=ROOT/"src/index.css"
css.write_text(css.read_text(encoding="utf-8")+'''
/* ZFLAG v2.0.60 — CENTERED TOP TABS + NATIVE MOTION.
   Override later legacy page-transition animation:none, without expensive blur
   or DOM re-layout. Respect the app's animations preference. */
.topbar .top-nav{
  justify-self:center !important; align-self:center !important;
  display:flex !important; align-items:center !important;
  width:max-content !important; flex:0 0 auto !important;
  min-width:0 !important; gap:5px !important;
  position:relative !important; margin:0 auto !important;
}
.topbar .top-nav .top-icon.nav-reveal,
.topbar .top-nav .top-icon.nav-reveal:hover,
.topbar .top-nav .top-icon.nav-reveal:focus-visible{
  flex:0 0 36px !important; width:36px !important; min-width:36px !important;
  max-width:36px !important; height:34px !important; padding:0 !important;
  border:1px solid transparent !important; border-radius:9px !important;
  display:inline-flex !important; align-items:center !important;
  justify-content:center !important; gap:0 !important; overflow:visible !important;
  transform:none !important;
}
.topbar .top-nav .top-icon.nav-reveal:hover,
.topbar .top-nav .top-icon.nav-reveal:focus-visible{
  background:rgba(255,255,255,.075) !important;border-color:rgba(255,255,255,.10) !important
}
.topbar .top-nav .top-icon.is-active{
  background:rgba(255,255,255,.10) !important;
  color:#fff !important;border-color:rgba(255,255,255,.14) !important
}
.topbar .top-nav .top-icon.nav-reveal::after{
  bottom:-8px !important;height:2px !important;width:16px !important;
  border-radius:3px !important;background:#f4f4f4 !important
}
.topbar .top-nav .top-icon-label{
  display:block !important;position:absolute !important;
  top:40px !important;left:50% !important;z-index:30 !important;
  max-width:none !important;width:max-content !important;
  padding:5px 9px !important;border:1px solid #383838 !important;
  border-radius:6px !important;background:#101010 !important;
  color:#f0f0f0 !important;font:600 10px/1.35 Inter,"Segoe UI",sans-serif !important;
  transform:translate(-50%,-5px) !important;opacity:0 !important;
  pointer-events:none !important;box-shadow:0 9px 22px rgba(0,0,0,.42) !important;
  transition:opacity 145ms ease,transform 180ms ease !important
}
.topbar .top-nav .top-icon.nav-reveal:hover .top-icon-label,
.topbar .top-nav .top-icon.nav-reveal:focus-visible .top-icon-label{
  max-width:none !important;opacity:1 !important;
  transform:translate(-50%,0) !important
}
.app-shell:not(.reduce-motion) .page-transition:not(:has(.editor-layout)){
  animation:zflag-v260-page 260ms cubic-bezier(.19,1,.22,1) both !important;
}
.app-shell:not(.reduce-motion) .page-transition:has(.editor-layout){
  animation:zflag-v260-editor 150ms ease-out both !important;
}
@keyframes zflag-v260-page{
  from{opacity:.22;transform:translate3d(0,7px,0)}
  to{opacity:1;transform:translate3d(0,0,0)}
}
@keyframes zflag-v260-editor{from{opacity:.55}to{opacity:1}}
.app-shell.reduce-motion .page-transition{animation:none !important}
.theme-light .topbar .top-nav .top-icon.is-active{background:#e5e5e5 !important;border-color:#ccc !important;color:#111 !important}
.theme-light .topbar .top-nav .top-icon-label{background:#fff !important;border-color:#d1d1d1 !important;color:#171717 !important}
.theme-light .topbar .top-nav .top-icon.nav-reveal:hover{background:#ececec !important;border-color:#d1d1d1 !important}
.theme-light .topbar .top-nav .top-icon.is-active::after{background:#333 !important}
@media(max-width:1050px){
 .topbar .top-nav{gap:2px !important}
 .topbar .top-nav .top-icon.nav-reveal,
 .topbar .top-nav .top-icon.nav-reveal:hover,
 .topbar .top-nav .top-icon.nav-reveal:focus-visible{
   flex-basis:31px !important;width:31px !important;min-width:31px !important;max-width:31px !important
 }
}
@media(max-width:720px){.topbar .top-nav .top-icon-label{display:none !important}}
@media(prefers-reduced-motion:reduce){
 .page-transition,.settings-subpage{animation:none !important}
 .topbar .top-nav .top-icon-label{transition:none !important}
}
''',encoding="utf-8")
enhanced=ROOT/"src/FlagLibraryEnhanced.css"
enhanced.write_text(enhanced.read_text(encoding="utf-8")+'''
/* v2.0.60 — descriptions and actual editable JSON values never overlap. */
.zflag-library-full .library-header,
.zflag-library-full .library-row{
 display:grid !important;
 grid-template-columns:minmax(0,1fr) minmax(154px,228px) 108px 48px !important;
 align-items:center !important;
 gap:12px !important;
}
.zflag-library-full .library-header>span{min-width:0 !important;white-space:normal !important}
.zflag-library-full .library-row-copy{min-width:0 !important;overflow:hidden !important}
.zflag-library-full .library-row-copy strong{display:block;overflow-wrap:anywhere;word-break:break-word}
.zflag-library-full .zfl-flag-description{
 display:block !important;max-width:100% !important;overflow:hidden !important;
 overflow-wrap:anywhere !important;word-break:break-word !important;
 line-height:1.5 !important;color:#a7a7a7 !important
}
.zflag-library-full .zfl-flag-description b{
 font:700 9px "Segoe UI",sans-serif;letter-spacing:.1em;
 color:#dedede;margin-right:5px
}
.zflag-library-full .zfl-native-value{min-width:0 !important;max-width:100% !important;overflow:hidden;gap:6px}
.zflag-library-full .zfl-native-value-label{
 display:flex;align-items:center;gap:6px;flex-wrap:wrap;
 font:700 9px/1.3 "Segoe UI",sans-serif;letter-spacing:.08em;color:#e8e8e8
}
.zflag-library-full .zfl-native-value-label span{color:#999;font-weight:500}
.zflag-library-full .zfl-native-value input,
.zflag-library-full .zfl-native-value select{
 width:100% !important;max-width:100% !important;min-width:0 !important;
 padding:9px 10px !important;font:12px Consolas,monospace !important;
 border:1px solid #444 !important;background:#020202 !important;color:#fff !important;
 border-radius:6px !important;overflow:hidden !important;text-overflow:ellipsis !important
}
.zflag-library-full .zfl-native-value input:focus,
.zflag-library-full .zfl-native-value select:focus{border-color:#f1f1f1 !important;outline:none !important}
.zflag-library-full .zfl-native-warning{color:#efbbbb;font-size:10px;line-height:1.45}
.zflag-library-full .zfl-error{
 position:relative;display:flex;align-items:center;justify-content:space-between;gap:10px;
 background:#210c0c;color:#ffd3d3;border:1px solid #6b2e2e;
 padding:10px 14px;margin:8px 0;border-radius:7px;font-size:12px
}
.zflag-library-full .zfl-error button{background:none;border:0;color:#fff;font-size:20px}
@media(max-width:980px){
 .zflag-library-full .library-header{display:none !important}
 .zflag-library-full .library-row{
   grid-template-columns:minmax(0,1fr) minmax(130px,185px) 42px !important;gap:9px !important
 }
 .zflag-library-full .library-row>.library-state{display:none !important}
}
@media(max-width:620px){
 .zflag-library-full .library-row{grid-template-columns:minmax(0,1fr) 40px !important}
 .zflag-library-full .zfl-native-value{grid-column:1 / -1;grid-row:2}
}
''',encoding="utf-8")
for rel in ('package.json','src-tauri/tauri.conf.json'):
 p=ROOT/rel;data=json.loads(p.read_text(encoding="utf-8"));assert data.get("version")=="2.0.59",rel
 data["version"]="2.0.60";p.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
cargo=ROOT/"src-tauri/Cargo.toml";source=cargo.read_text(encoding="utf-8")
source,n=re.subn(r'(?m)^version = "2\.0\.59"$','version = "2.0.60"',source,count=1)
assert n==1,"Cargo version mismatch";cargo.write_text(source,encoding="utf-8")
for directory in (ROOT/"tests",ROOT/"scripts"):
 for p in directory.rglob("*"):
  if not p.is_file() or p.suffix.lower() not in (".py",".ps1",".ts",".tsx",".js",".json"):continue
  try:raw=p.read_text(encoding="utf-8")
  except UnicodeError:continue
  if "2.0.59" in raw:p.write_text(raw.replace("2.0.59","2.0.60"),encoding="utf-8")
app=ROOT/"src/App.tsx";raw=app.read_text(encoding="utf-8");app.write_text(raw.replace("2.0.59","2.0.60"),encoding="utf-8")
# Regression focused on actual value parsing and no disabled motion.
test=ROOT/"tests/test_v260_navigation_values.py"
test.write_text('''import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class ZflagV260Tests(unittest.TestCase):
 def test_catalog_types_and_names(self):
  flags=json.loads((ROOT/"src/data/flag-library.json").read_text(encoding="utf-8"))
  self.assertEqual(len(flags),15965)
  byname={f["name"]:f for f in flags}
  self.assertEqual(byname["FFlagDebugGraphicsPreferD3D11"]["type"],"boolean")
  self.assertEqual(byname["DFIntTaskSchedulerTargetFps"]["type"],"integer")
  self.assertRegex(byname["DFIntTaskSchedulerTargetFps"]["value"].strip(),r"^-?\d+$")
 def test_editor_values_validated(self):
  lib=(ROOT/"src/FlagLibrary.tsx").read_text(encoding="utf-8")
  for marker in ("ACTUAL VALUE","DESCRIPTION","Number.isSafeInteger","Invalid","parsedValue(flag: Flag)","setValueError"):
   self.assertIn(marker,lib)
  self.assertNotIn("flag.value.toLowerCase() === \\"true\\"",lib)
 def test_native_animation_and_centered_nav(self):
  css=(ROOT/"src/index.css").read_text(encoding="utf-8")
  self.assertIn("zflag-v260-page",css)
  self.assertIn("zflag-v260-editor",css)
  self.assertIn("top-nav .top-icon.nav-reveal:hover",css)
  self.assertIn(".app-shell.reduce-motion .page-transition",css)
  app=(ROOT/"src/App.tsx").read_text(encoding="utf-8")
  self.assertIn("mainScrollRef.current.scrollTop = 0",app)
 def test_version(self):
  self.assertEqual(json.loads((ROOT/"package.json").read_text(encoding="utf-8"))["version"],"2.0.60")
''',encoding="utf-8")
print("v2.0.60: catalog types, inline values, stable centered nav, smooth accessible transitions")
