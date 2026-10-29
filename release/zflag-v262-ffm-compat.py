"""ZFLAG v2.0.62: independently implemented FFM-compatible preset import.
No FFM source, binary, version-bound offsets or memory writer is redistributed.
The existing ZFLAG native engine is unchanged.
"""
from pathlib import Path
import json,re,sys
root=Path(sys.argv[1])
lib=root/'src/FlagLibrary.tsx'
s=lib.read_text(encoding='utf-8')
old='  const [selectedValue,setSelectedValue]=useState<Record<string,string>>({})'
assert s.count(old)==1,"Missing Library state anchor"
new='''  const [selectedValue,setSelectedValue]=useState<Record<string,string>>({})
  const [ffmMessage,setFfmMessage]=useState("")
  const [ffmError,setFfmError]=useState(false)
  // Import preset data to the existing editor only; never invoke memory writing.
  async function importFfmJson(file: File | undefined) {
    if (!file) return
    setFfmMessage(""); setFfmError(false)
    try {
      if (file.size > 4*1024*1024) throw new Error("JSON exceeds 4 MB limit")
      const parsed:unknown=JSON.parse(await file.text())
      const object=(value:unknown):value is Record<string,unknown> =>
        value !== null && typeof value === "object" && !Array.isArray(value)
      const sources:unknown[]=Array.isArray(parsed) ? parsed :
        object(parsed) && Array.isArray(parsed.presets) ? parsed.presets : [parsed]
      if (!sources.length || sources.length > 250) throw new Error("Expected 1–250 presets")
      const flags:Record<string,string|number|boolean>={}
      let unique=0, skipped=0, presets=0
      for (const item of sources) {
        if (!object(item)) { skipped++; continue }
        const candidate=object(item.flags) || Array.isArray(item.flags) ? item.flags : item
        const pairs:Array<[string,unknown]>=Array.isArray(candidate) ?
          candidate.filter(object).map(row=>[String(row.name??""),row.value] as [string,unknown]) :
          object(candidate) ? Object.entries(candidate) : []
        let accepted=0
        for (const [name,value] of pairs) {
          if (!/^(?:DFFlag|SFFlag|FFlag|DFInt|SFInt|FInt|DFFloat|SFFloat|FFloat|DFString|SFString|FString|DFLog|FLog)[A-Za-z0-9_]{1,125}$/.test(name)) { skipped++; continue }
          if (!(typeof value==="boolean" || (typeof value==="number" && Number.isFinite(value) && Number.isSafeInteger(value)) || (typeof value==="string" && value.length<=8192))) { skipped++; continue }
          if (!Object.prototype.hasOwnProperty.call(flags,name)) unique++
          if (unique>20000) throw new Error("Import exceeds 20,000 unique flags")
          flags[name]=value; accepted++
        }
        if (accepted) presets++
      }
      if (!unique) throw new Error("No valid flag map or FFM preset flags found")
      onMerge(flags)
      setFfmMessage("Added "+unique.toLocaleString()+" unique flag entries from "+presets+" preset(s) to the editor; "+skipped+" skipped. Nothing injected.")
    } catch (err) {
      setFfmError(true)
      setFfmMessage(err instanceof Error ? err.message : "Invalid preset")
    }
  }
'''
s=s.replace(old,new,1)
anchor='    <div className="library-premades-controls">'
assert s.count(anchor)==1,"Missing premade control anchor"
s=s.replace(anchor,'''    <div className="zfl-ffm-import">
      <label>Import FFM / ZFLAG JSON presets
        <input type="file" accept=".json,application/json" aria-label="Import FFM or ZFLAG JSON presets" onChange={event => { void importFfmJson(event.currentTarget.files?.[0]); event.currentTarget.value="" }} />
      </label>
      <span>Adds a typed draft to your editor. Version-specific offsets and live-memory methods are excluded.</span>
      {ffmMessage && <p role="status" className={ffmError ? "zfl-ffm-error" : "zfl-ffm-success"}>{ffmMessage}</p>}
    </div>
'''+anchor,1)
lib.write_text(s,encoding='utf-8')
css=root/'src/FlagLibraryEnhanced.css'
css.write_text(css.read_text(encoding='utf-8')+'''
/* v2.0.62 FFM JSON preset interoperability (data only) */
.zfl-ffm-import{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin:12px 0;padding:13px;border:1px solid #383838;border-radius:8px;background:#090909;color:#b6b6b6;font-size:12px}
.zfl-ffm-import label{color:#f4f4f4;font-weight:600;display:inline-flex;gap:10px;align-items:center;flex-wrap:wrap}
.zfl-ffm-import input{max-width:210px;color:#ddd;font-size:11px}
.zfl-ffm-import input::file-selector-button{padding:7px;border-radius:6px;border:1px solid #555;background:#171717;color:#eee;cursor:pointer}
.zfl-ffm-import p{flex-basis:100%;margin:0}
.zfl-ffm-error{color:#ffa9a9}.zfl-ffm-success{color:#b6e5cb}
''',encoding='utf-8')
for rel in ('package.json','src-tauri/tauri.conf.json'):
 p=root/rel;obj=json.loads(p.read_text(encoding='utf-8'))
 assert obj['version']=='2.0.61',(rel,obj['version'])
 obj['version']='2.0.62'
 p.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
cargo=root/'src-tauri/Cargo.toml'
x=cargo.read_text(encoding='utf-8')
x,n=re.subn(r'(?m)^version = "2\.0\.61"$','version = "2.0.62"',x,count=1)
assert n==1,"Cargo version anchor mismatch"
cargo.write_text(x,encoding='utf-8')
for folder in ('tests','scripts'):
 for p in (root/folder).rglob('*'):
  if p.suffix not in ('.py','.ps1','.ts','.tsx','.js','.json'): continue
  try: data=p.read_text(encoding='utf-8')
  except UnicodeError: continue
  if '2.0.61' in data:p.write_text(data.replace('2.0.61','2.0.62'),encoding='utf-8')
app=root/'src/App.tsx'
app.write_text(app.read_text(encoding='utf-8').replace('2.0.61','2.0.62'),encoding='utf-8')
test=root/'tests/test_v262_ffm_compat.py'
test.write_text("""import json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Compatibility(unittest.TestCase):
 def test_ui(self):
  s=(ROOT/'src/FlagLibrary.tsx').read_text(encoding='utf-8')
  for marker in ('importFfmJson','Array.isArray(parsed.presets)','onMerge(flags)','Nothing injected.','Version-specific offsets'):
   self.assertIn(marker,s)
 def test_versions(self):
  for p in ('package.json','src-tauri/tauri.conf.json'):
   self.assertEqual(json.loads((ROOT/p).read_text(encoding='utf-8'))['version'],'2.0.62')
 def test_original_engine_retained(self):
  self.assertTrue((ROOT/'native-enhanced/fastflag_injector_gui_enhanced.cpp').exists())
""",encoding='utf-8')
print('ZFLAG 2.0.62: FFM JSON draft import added. Existing C++ engine unchanged.')
