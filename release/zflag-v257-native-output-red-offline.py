"""ZFLAG v2.0.57: bounded native per-flag output feed plus red offline badge.

Apply after v2.0.56 and before the shared Windows build/tests. Native write
algorithms and Roblox memory access are unchanged. This feed includes only
validated native checkpoint records and completed batches, not guessed successes.
"""
from pathlib import Path
import re
import sys
root = Path(sys.argv[1])

def load(rel): return (root/rel).read_text(encoding='utf-8')
def save(rel, s): (root/rel).write_text(s, encoding='utf-8')
def once(s, before, after, name):
    n = s.count(before)
    if n != 1: raise RuntimeError(f'{name}: expected exactly one source anchor, found {n}: {before[:100]!r}')
    return s.replace(before, after, 1)

back = load('backend/server.py')
# Store at most 160 committed per-flag acknowledgments. Each new run resets it.
start = back.index('def live_bulk_status(')
back = back[:start] + '_BULK_LIVE_RECENT: list[dict[str, object]] = []\n_BULK_LIVE_OUTPUT_LIMIT = 160\n\n' + back[start:]
start = back.index('def live_bulk_status(')
end = back.index('def cancel_live_bulk(', start)
new_status = '''def live_bulk_status():
    """Return bounded live output without treating scanned-but-unconfirmed flags as applied.

    Finished batches are immutable entries in _BULK_LIVE_RECENT. During an
    active native subprocess, a separate per-flag checkpoint file supplies
    the provisional tail. These two portions are never persisted together.
    """
    with _BULK_LIVE_LOCK:
        snapshot = dict(_BULK_LIVE_STATUS)
        recent = list(_BULK_LIVE_RECENT)
    if not snapshot.get("active"):
        snapshot["recentRows"] = recent[-_BULK_LIVE_OUTPUT_LIMIT:]
        return snapshot
    with _INJECTION_STATUS_LOCK:
        native_active = bool(_INJECTION_STATUS.get("active"))
        native_path = _INJECTION_STATUS.get("path")
        native_flags = _INJECTION_STATUS.get("flags")
    if native_active and isinstance(native_path, str) and isinstance(native_flags, dict):
        # The checkpoint reader checks each flag name against the exact batch,
        # validates booleans, rejects duplicates and incomplete JSON lines.
        rows = recover_native_progress(native_path, native_flags)[:BULK_LIVE_CHUNK]
        total = max(0, int(snapshot.get("total") or 0))
        base_done = max(0, int(snapshot.get("completed") or 0))
        count = min(len(rows), BULK_LIVE_CHUNK, max(0, total-base_done))
        current = rows[:count]
        current_ok = sum(row.get("ok") is True for row in current)
        recent.extend({"index":base_done+i+1, "name":row["name"],
                       "ok":row["ok"], "message":row.get("message", "")}
                      for i,row in enumerate(current))
        snapshot["completed"] = base_done + count
        snapshot["applied"] = max(0,int(snapshot.get("applied") or 0)) + current_ok
        snapshot["failed"] = max(0,int(snapshot.get("failed") or 0)) + (count-current_ok)
        snapshot["pending"] = max(0, total-snapshot["completed"])
        snapshot["phase"] = "Receiving native acknowledgments" if count else "Scanning current native batch"
    snapshot["recentRows"] = recent[-_BULK_LIVE_OUTPUT_LIMIT:]
    return snapshot


'''
back = back[:start] + new_status + back[end:]
# Install commits after each native batch; do not add synthetic successes.
start = back.index('def _live_bulk_worker(')
end = back.index('def start_live_bulk(', start)
worker = back[start:end]
marker = '            with _BULK_LIVE_LOCK:\n'
rows_at = worker.index('rows=result.get(')
result_prefix, result_suffix = worker[:rows_at], worker[rows_at:]
if result_suffix.count(marker) != 1:
    raise RuntimeError('Native worker result commit point changed')
result_suffix = result_suffix.replace(marker, '''            with _BULK_LIVE_LOCK:
                _BULK_LIVE_RECENT.extend(
                    {"index":first+i+1, "name":row["name"], "ok":row["ok"],
                     "message":str(row.get("message", ""))[:500]}
                    for i,row in enumerate(rows)
                    if isinstance(row,dict) and isinstance(row.get("name"),str)
                    and type(row.get("ok")) is bool
                )
                if len(_BULK_LIVE_RECENT) > _BULK_LIVE_OUTPUT_LIMIT:
                    del _BULK_LIVE_RECENT[:-_BULK_LIVE_OUTPUT_LIMIT]
''',1)
worker = result_prefix + result_suffix
back = back[:start] + worker + back[end:]
# Clear stale output only at the start of a new manually triggered bulk run.
start = back.index('def start_live_bulk(')
end = back.index('class Runtime:',start)
body = back[start:end]
marker = '        _BULK_LIVE_CANCEL.clear()'
body = once(body, marker, '        _BULK_LIVE_RECENT.clear()\n'+marker, 'clear old native feed')
back = back[:start] + body + back[end:]
save('backend/server.py', back)

ui = load('src/App.tsx')
ui = once(ui, 'type ActivityFilter = "all" | "success" | "warning" | "error"',
 '''type ActivityFilter = "all" | "success" | "warning" | "error"
type NativeFeedRow = { index: number; name: string; ok: boolean; message: string }''', 'native feed type')
# The v2.0.56 progress UI has a phase property. Keep one owner ID for tab isolation.
needle = '  const [liveBulkActive, setLiveBulkActive] = useState(false)'
ui = once(ui, needle, needle+'''
  const [nativeFeedTabId, setNativeFeedTabId] = useState<string | null>(null)
  const [nativeFeedFollow, setNativeFeedFollow] = useState(true)
  const nativeFeedScrollRef = useRef<HTMLDivElement | null>(null)''', 'feed state')
# The progress shape is inferred from its initializer. Preserve native evidence types.
pattern = r'(const \[liveBulkProgress, setLiveBulkProgress\] = useState\(\{[^\n]*?)(\}\))'
def augment_progress(m):
    value=m.group(1)
    if 'recentRows:' in value: return m.group(0)
    return value+',recentRows:[] as NativeFeedRow[]'+m.group(2)
ui,n = re.subn(pattern,augment_progress,ui,count=1)
if n != 1: raise RuntimeError('Live progress state initializer missing')
# The initializer and polling function BOTH supply recentRows to TS state.
pattern = r'setLiveBulkProgress\(\{([^\n]*?)\}\)'
seen=0
def augment_updates(m):
    global seen
    seen += 1
    body=m.group(1)
    if 'recentRows:' in body: return m.group(0)
    if 'state.' in body:
        return 'setLiveBulkProgress({' + body + ',recentRows:Array.isArray(state.recentRows) ? state.recentRows.slice(-160).filter((row: unknown) => row !== null && typeof row === "object").map((row: unknown) => { const entry = row as Record<string, unknown>; return { index:Number(entry.index)||0, name:String(entry.name||""), ok:entry.ok===true, message:String(entry.message||"") } }) : []})'
    return 'setLiveBulkProgress({' + body + ',recentRows:[] as NativeFeedRow[]})'
ui = re.sub(pattern,augment_updates,ui)
if seen < 2: raise RuntimeError('Missing live progress initializer or poll update')
# Only pressing Inject starts scrolling; opening JSON files never does.
ui = once(ui, '      setLiveBulkActive(true)', '''      setNativeFeedTabId(activeTab?.id ?? null)
      setEditorBottomTab("activity")
      setLiveBulkActive(true)''', 'start output on inject')
# Keep the last 160 native rows after stopping, isolated to the originating tab.
anchor = '  const isCurrentTabInjecting = liveBulkActive && liveBulkOwnerRef.current?.tabId === activeTab?.id'
if ui.count(anchor) != 1: raise RuntimeError('Per-tab live status anchor changed')
ui = ui.replace(anchor, anchor+'''
  const nativeFeedForActiveTab = nativeFeedTabId === activeTab?.id && (liveBulkActive || liveBulkProgress.recentRows.length > 0)
  const nativeFeedRows = nativeFeedForActiveTab ? liveBulkProgress.recentRows :
    (lastTabSnapshot && snapshotMatchesTab ? (lastTabSnapshot.results ?? []).slice(-160).map((row, i) => ({ index:i+1, name:row.name, ok:row.ok===true, message:row.message ?? "" })) : [])
  const lastNativeRowIndex = nativeFeedRows.length ? nativeFeedRows[nativeFeedRows.length-1].index : 0
  useEffect(() => {
    if (nativeFeedFollow && nativeFeedScrollRef.current)
      nativeFeedScrollRef.current.scrollTop = nativeFeedScrollRef.current.scrollHeight
  }, [nativeFeedFollow, lastNativeRowIndex, activeTabId])''', 1)
# Present it first, without removing the backend-wide activity log panel.
needle = '                <div className="grouped-log-list">{renderActivityGroups()}</div>'
ui = once(ui,needle,'''                {(liveBulkActive && nativeFeedForActiveTab || nativeFeedRows.length > 0) && <section className="native-flag-output" aria-label="Native FastFlag output">
                  <div className="native-flag-output-heading"><strong>{nativeFeedForActiveTab && liveBulkActive ? "LIVE NATIVE OUTPUT" : "LAST NATIVE RESULTS"}</strong>
                    <span>{nativeFeedRows.length} latest rows · verified responses only</span>
                    <button type="button" onClick={() => setNativeFeedFollow((value) => !value)} aria-pressed={nativeFeedFollow}>{nativeFeedFollow ? "Follow: ON" : "Follow: OFF"}</button>
                  </div>
                  <div className="native-flag-output-rows" ref={nativeFeedScrollRef} role="log" aria-live="off">
                    {nativeFeedRows.length === 0 ? <div className="native-flag-output-pending">Scanning flags — waiting for native acknowledgments…</div> : nativeFeedRows.map((entry) => <div className={cn("native-flag-output-row", entry.ok ? "is-success" : "is-error")} key={`${entry.index}-${entry.name}`}>
                      <span className="native-flag-output-index">{String(entry.index).padStart(5,"0")}</span>
                      <span className="native-flag-output-status">{entry.ok ? "✓ APPLIED" : "✕ FAILED"}</span>
                      <code title={entry.name}>{entry.name}</code>
                      <span className="native-flag-output-detail" title={entry.message}>{entry.message || (entry.ok ? "Native setter acknowledged" : "Native setter rejected")}</span>
                    </div>)}
                  </div>
                </section>}
                <div className="grouped-log-list">{renderActivityGroups()}</div>''', 'output in Activity panel')
save('src/App.tsx',ui)

css = load('src/index.css')
css += '''
/* v2.0.57 - Roblox absence is red, and the native output follows original CLI pacing. */
.runtime-pill:not(.connected):not(.detected) { color: #ef9295 !important; border-color: rgba(235,70,80,.23) !important; background: rgba(235,65,75,.075) !important; }
.runtime-pill .status-dot:not(.online):not(.detected) { background: #f16873 !important; box-shadow: 0 0 0 4px rgba(241,104,115,.1) !important; }
.native-flag-output { border:1px solid rgba(255,255,255,.09); border-radius:8px; background:#0b0d10; margin: 6px 4px 9px; overflow:hidden; }
.native-flag-output-heading { display:flex; gap:12px; align-items:center; padding:7px 10px; color:#aeb4bf; font-size:10px; border-bottom:1px solid rgba(255,255,255,.08); }
.native-flag-output-heading strong { color:#d9e1ed; font-size:10px; letter-spacing:.045em; }
.native-flag-output-heading button { margin-left:auto; background:transparent; border:1px solid rgba(255,255,255,.12); border-radius:6px; color:#b8c6d1; padding:3px 8px; font-size:10px; }
.native-flag-output-rows { height:165px; overflow-y:auto; font:10.5px/1.6 ui-monospace,SFMono-Regular,Consolas,monospace; }
.native-flag-output-pending { padding:16px 12px; color:#8e959f; }
.native-flag-output-row { display:flex; align-items:center; gap:9px; padding:2px 9px; min-width:0; border-bottom:1px solid rgba(255,255,255,.025); }
.native-flag-output-index { flex:0 0 auto; color:#58616d; }
.native-flag-output-status { flex:0 0 76px; font-weight:700; }
.native-flag-output-row.is-success .native-flag-output-status { color:#63d6a4; }
.native-flag-output-row.is-error .native-flag-output-status { color:#f2828b; }
.native-flag-output-row code { color:#e0e6ec; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; flex:0 1 45%; }
.native-flag-output-detail { color:#737e8b; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; flex:1 1 auto; }
'''
save('src/index.css',css)

for rel in ('package.json','src-tauri/tauri.conf.json','scripts/smoke-test-installed-app.ps1',
            'tests/test_release_integrity.py','tests/test_large_json_safety_248.py',
            'tests/test_ui_pacing_253.py','tests/test_tab_game_profiles_254.py','tests/test_streaming_256.py'):
    path=root/rel
    if not path.is_file(): continue
    s=path.read_text(encoding='utf-8')
    if '2.0.56' in s: path.write_text(s.replace('2.0.56','2.0.57'), encoding='utf-8')
    elif rel in ('package.json','src-tauri/tauri.conf.json','tests/test_release_integrity.py'):
        raise RuntimeError('Version anchor missing in '+rel)
cargo=root/'src-tauri/Cargo.toml'
s=cargo.read_text(encoding='utf-8')
s,n=re.subn(r'(?m)^version = "2\.0\.\d+"$', 'version = "2.0.57"',s,count=1)
if n!=1: raise RuntimeError('Rust version missing')
cargo.write_text(s,encoding='utf-8')

(root/'tests/test_native_output_257.py').write_text('''import ast,threading,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class NativeOutput(unittest.TestCase):
    def test_offline_red_and_output_bounded(self):
        css=(ROOT/'src/index.css').read_text(encoding='utf-8')
        self.assertIn('.runtime-pill:not(.connected):not(.detected)',css)
        self.assertIn('.native-flag-output-rows',css)
        ui=(ROOT/'src/App.tsx').read_text(encoding='utf-8')
        self.assertIn('setEditorBottomTab("activity")',ui)
        self.assertIn('nativeFeedScrollRef',ui)
        self.assertIn('recentRows.slice(-160)',ui)
        self.assertIn('aria-live="off"',ui)
    def test_checkpoint_rows_not_fake_and_no_mutation(self):
        tree=ast.parse((ROOT/'backend/server.py').read_text(encoding='utf-8'))
        fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='live_bulk_status')
        state={'active':True,'total':100,'completed':32,'applied':10,'failed':22,'pending':68}
        feed=[{'index':32,'name':'old','ok':False,'message':'unsupported'}]
        ns={'_BULK_LIVE_LOCK':threading.Lock(),'_BULK_LIVE_STATUS':state,
        '_BULK_LIVE_RECENT':feed,'_BULK_LIVE_OUTPUT_LIMIT':160,
        '_INJECTION_STATUS_LOCK':threading.Lock(),
        '_INJECTION_STATUS':{'active':True,'path':'unique','flags':{'A':'true','B':'false'}},
        'BULK_LIVE_CHUNK':32,
        'recover_native_progress':lambda path,flags:[{'name':'A','ok':True,'message':'ok'},{'name':'B','ok':False,'message':'no'}]}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'<mock>','exec'),ns)
        result=ns['live_bulk_status']()
        self.assertEqual((result['completed'],result['applied'],result['failed'],result['pending']),(34,11,23,66))
        self.assertEqual([x['index'] for x in result['recentRows']],[32,33,34])
        self.assertEqual(state['completed'],32)
        self.assertEqual(len(feed),1)
    def test_native_record_ring_and_reset(self):
        s=(ROOT/'backend/server.py').read_text(encoding='utf-8')
        self.assertIn('_BULK_LIVE_RECENT.clear()',s)
        self.assertIn('del _BULK_LIVE_RECENT[:-_BULK_LIVE_OUTPUT_LIMIT]',s)
        self.assertIn('recover_native_progress(native_path, native_flags)',s)
''',encoding='utf-8')
print('Applied ZFLAG v2.0.57: bounded native FastFlag output and red Roblox offline status')