"""ZFLAG v2.0.63: evidence-based fallback planning inside the desktop UI.

Only definite failed acknowledgments qualify for a separate retry draft.
No additional engine executable, game memory code, or unverified bypass.
"""
import json
import re
import sys
from pathlib import Path
root=Path(sys.argv[1])
src=root/'src'
module=src/'fallbackPlan.ts'
module.write_text('''export type NativeResult = { name: string; ok: boolean; message?: string }
export type FallbackPlan = {
  flags: Record<string, unknown>
  eligible: number
  skipped: number
  warning: string
}
const unknown = /(?:unknown outcome|timeout|timed out|interrupted|cancelled|missing acknowledgement|not attempted|unverified|access denied|process closed|process restart)/i
export function prepareFallbackPlan(
  original: Record<string, unknown>,
  rows: readonly NativeResult[]
): FallbackPlan {
  const selected:Record<string,unknown> = {}
  let skipped = 0
  const seen = new Set<string>()
  for (const row of rows) {
    if (!row || typeof row.name !== "string" || seen.has(row.name)) { skipped++; continue }
    seen.add(row.name)
    if (row.ok !== false || !Object.prototype.hasOwnProperty.call(original,row.name) || unknown.test(row.message || "")) { skipped++; continue }
    selected[row.name] = original[row.name]
  }
  return { flags:selected,eligible:Object.keys(selected).length,skipped,
    warning:"A confirmed native failure does not mean the alternate engine supports this flag. The new preset is a draft and is not applied automatically." }
}
''',encoding='utf-8')
app=src/'App.tsx'
s=app.read_text(encoding='utf-8')
needle='import { FlagLibrary } from "./FlagLibrary"'
assert s.count(needle)==1, "App import anchor changed"
s=s.replace(needle,needle+'\nimport { prepareFallbackPlan } from "./fallbackPlan"',1)
needle='  function renderPresets() {'
assert s.count(needle)==1, "Presets anchor changed"
s=s.replace(needle,'''  function createFallbackDraft() {
    if (!parsed.ok || !activeTab || !lastApplied?.results?.length) {
      showToast("No verified results","Apply the current preset and check the reported outcomes first.","warning")
      return
    }
    const plan=prepareFallbackPlan(parsed.value,lastApplied.results)
    if (!plan.eligible) {
      showToast("Nothing eligible","Only explicit failed acknowledgments can be included. Unverified results are excluded.","info")
      return
    }
    const base=activeTab.name.replace(/\\\\.json$/i,"")
    newTab(JSON.stringify(plan.flags,null,2),base+"-confirmed-failures.json")
    showToast("Fallback draft ready",String(plan.eligible)+" confirmed failures copied. Select another engine in Settings to test manually; nothing was injected.","info")
  }

  function renderPresets() {''',1)
needle='        <div className="diff-strip">'
assert s.count(needle)==1, "Editor results anchor changed"
s=s.replace(needle,'''        {lastApplied?.results?.length > 0 && <section className="zflag-fallback-draft" aria-label="Engine fallback preparation">
          <strong>Engine fallback · confirmed failures only</strong>
          <p>Prepare a separate JSON draft containing only flags whose native result explicitly failed. Select the alternate engine in Settings before another manual attempt. Unknown or interrupted outcomes are never retried automatically; the original tab is unchanged.</p>
          <button type="button" disabled={!parsed.ok || busy || liveBulkActive} onClick={createFallbackDraft}>Create fallback draft</button>
        </section>}
        <div className="diff-strip">''',1)
app.write_text(s,encoding='utf-8')
css=src/'index.css'
css.write_text(css.read_text(encoding='utf-8')+'''
/* ZFLAG v2.0.63: conservative, non-automatic engine fallback planning. */
.zflag-fallback-draft{display:flex;flex-wrap:wrap;align-items:center;gap:9px 15px;padding:13px 15px;margin:9px 4px 13px;background:#080808;border:1px solid #333;border-radius:9px;color:#dedede}
.zflag-fallback-draft strong{font-size:12px;letter-spacing:.01em}
.zflag-fallback-draft p{flex:1 1 390px;margin:0;color:#aaa;font-size:11px;line-height:1.5}
.zflag-fallback-draft button{cursor:pointer;border:1px solid #777;background:#191919;color:#fff;padding:9px 12px;border-radius:7px;font-size:11px}
.zflag-fallback-draft button:disabled{opacity:.45;cursor:not-allowed}
.theme-light .zflag-fallback-draft{background:#f8f8f8;border-color:#ddd;color:#171717}
.theme-light .zflag-fallback-draft p{color:#555}
''',encoding='utf-8')
for path in (root/'package.json',root/'src-tauri/tauri.conf.json'):
 d=json.loads(path.read_text(encoding='utf-8'))
 assert d['version']=='2.0.62',(path,d['version'])
 d['version']='2.0.63'
 path.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
cargo=root/'src-tauri/Cargo.toml'
t=cargo.read_text(encoding='utf-8')
t,n=re.subn(r'(?m)^version = "2\.0\.62"$','version = "2.0.63"',t,count=1)
assert n==1,"Cargo version anchor missing"
cargo.write_text(t,encoding='utf-8')
for folder in (root/'tests',root/'scripts'):
 for p in folder.rglob('*'):
  if p.suffix not in ('.py','.ps1','.ts','.tsx','.js','.json'):continue
  try:s=p.read_text(encoding='utf-8')
  except UnicodeError:continue
  if '2.0.62' in s:p.write_text(s.replace('2.0.62','2.0.63'),encoding='utf-8')
app.write_text(app.read_text(encoding='utf-8').replace('2.0.62','2.0.63'),encoding='utf-8')
(root/'tests/test_v263_fallback.py').write_text('''from pathlib import Path
import json, unittest
ROOT=Path(__file__).resolve().parents[1]
class FallbackRegression(unittest.TestCase):
 def test_draft_does_not_auto_dispatch(self):
  src=(ROOT/'src/fallbackPlan.ts').read_text(encoding='utf-8')
  self.assertIn('row.ok !== false',src)
  self.assertIn('unknown.test',src)
  self.assertIn('Object.prototype.hasOwnProperty',src)
  self.assertNotIn('fetch(',src)
  self.assertNotIn('applyFlags(',src)
 def test_app_has_manual_fallback(self):
  s=(ROOT/'src/App.tsx').read_text(encoding='utf-8')
  self.assertIn('createFallbackDraft',s)
  self.assertIn('prepareFallbackPlan(parsed.value,lastApplied.results)',s)
  self.assertIn('Create fallback draft',s)
  self.assertIn('newTab(JSON.stringify(plan.flags',s)
 def test_version(self):
  self.assertEqual(json.loads((ROOT/'package.json').read_text(encoding='utf-8'))['version'],'2.0.63')
''',encoding='utf-8')
print("ZFLAG v2.0.63: confirmed failures only -> separate manual fallback draft; existing native paths retained.")
