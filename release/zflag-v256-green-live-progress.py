"""ZFLAG v2.0.56: truthful live counters and soft-green process detection.
Runs after v2.0.55 source patches, without changing native write logic.
"""
from pathlib import Path
import sys
root = Path(sys.argv[1])

def replace(rel, old, new):
    path = root / rel
    content = path.read_text(encoding='utf-8')
    n = content.count(old)
    if n != 1:
        raise RuntimeError(f'{rel}: expected one match, found {n}: {old[:140]!r}')
    path.write_text(content.replace(old, new, 1), encoding='utf-8')

replace('src/index.css',
    '.runtime-pill.detected { color: #f2c781 !important; border-color: rgba(226,171,74,.25) !important; background: rgba(226,171,74,.075) !important; }',
    '.runtime-pill.detected { color: #9fe8c4 !important; border-color: rgba(70,209,135,.23) !important; background: rgba(52,171,118,.065) !important; }')
replace('src/index.css',
    '.runtime-pill .status-dot.detected { background: #f2b957 !important; box-shadow: 0 0 0 4px rgba(242,185,87,.10) !important; }',
    '.runtime-pill .status-dot.detected { background: #48d994 !important; box-shadow: 0 0 0 4px rgba(72,217,148,.10) !important; }')

replace('backend/server.py', '''def live_bulk_status() -> dict[str, object]:
    with _BULK_LIVE_LOCK:
        return dict(_BULK_LIVE_STATUS)
''', '''def live_bulk_status() -> dict[str, object]:
    """Return persisted batch totals plus verified *current* native acknowledgments.

    The native sidecar flushes progress one flag at a time. This read-only
    snapshot lets the UI move during a long batch without claiming unknown
    flags were written. Never commit interim rows back to the base counters:
    the worker adds a batch exactly once when its native process returns.
    """
    with _BULK_LIVE_LOCK:
        snapshot = dict(_BULK_LIVE_STATUS)
    if not snapshot.get("active"):
        return snapshot
    current = injection_status()
    if not current.get("active"):
        return snapshot
    total = max(0, int(snapshot.get("total") or 0))
    base_done = max(0, int(snapshot.get("completed") or 0))
    batch_size = min(BULK_LIVE_CHUNK, max(0, total - base_done))
    interim_done = min(batch_size, max(0, int(current.get("completed") or 0)))
    interim_ok = min(interim_done, max(0, int(current.get("applied") or 0)))
    interim_failed = min(interim_done - interim_ok, max(0, int(current.get("failed") or 0)))
    snapshot["completed"] = min(total, base_done + interim_done)
    snapshot["applied"] = max(0, int(snapshot.get("applied") or 0)) + interim_ok
    snapshot["failed"] = max(0, int(snapshot.get("failed") or 0)) + interim_failed
    snapshot["pending"] = max(0, total - snapshot["completed"])
    snapshot["phase"] = "Receiving native acknowledgments" if interim_done else "Scanning current native batch"
    return snapshot
''')
replace('backend/server.py', '''            batch = dict(entries[first:first + BULK_LIVE_CHUNK])
            result = apply_enhanced(batch, source)''', '''            batch = dict(entries[first:first + BULK_LIVE_CHUNK])
            with _BULK_LIVE_LOCK:
                _BULK_LIVE_STATUS["phase"] = f"Scanning batch {first // BULK_LIVE_CHUNK + 1} / {(len(entries) + BULK_LIVE_CHUNK - 1) // BULK_LIVE_CHUNK}"
            result = apply_enhanced(batch, source)''')
replace('backend/server.py', '''                                         failureSamples=failures[:])''', '''                                         failureSamples=failures[:],
                                         phase=f"Batch {first // BULK_LIVE_CHUNK + 1} completed")''')
replace('backend/server.py', '''                                     pending=len(flags)-attempted)''', '''                                     pending=len(flags)-attempted,
                                     phase="Finished" if outcome == "completed" else "Stopped")''')
replace('backend/server.py', '''                                 message="", failureSamples=[])''', '''                                 message="", failureSamples=[], phase="Preparing first batch")''')

replace('src/App.tsx', '''  const [liveBulkProgress, setLiveBulkProgress] = useState({ active: false, completed: 0, total: 0, applied: 0, failed: 0, outcome: "", message: "" })''', '''  const [liveBulkProgress, setLiveBulkProgress] = useState({ active: false, completed: 0, total: 0, applied: 0, failed: 0, outcome: "", message: "", phase: "" })''')
replace('src/App.tsx', '''  const lastApplied = snapshotMatchesTab && !(liveBulkActive && liveBulkOwnerRef.current?.tabId === activeTab?.id) ? lastTabSnapshot : undefined
  const lastApplyStats = useMemo(() => {
    const success = lastApplied?.applied ?? 0
    const failed = lastApplied?.errors ?? 0
    const pending = lastApplied?.pending ?? 0
    const total = success + failed + pending
    const rate = total ? Math.round((success / total) * 100) : 0
    return { success, failed, pending, total, rate }
  }, [lastApplied])''', '''  const isCurrentTabInjecting = liveBulkActive && liveBulkOwnerRef.current?.tabId === activeTab?.id
  const lastApplied = snapshotMatchesTab && !isCurrentTabInjecting ? lastTabSnapshot : undefined
  const lastApplyStats = useMemo(() => {
    const success = isCurrentTabInjecting ? liveBulkProgress.applied : lastApplied?.applied ?? 0
    const failed = isCurrentTabInjecting ? liveBulkProgress.failed : lastApplied?.errors ?? 0
    const total = isCurrentTabInjecting ? liveBulkProgress.total : success + failed + (lastApplied?.pending ?? 0)
    const processed = isCurrentTabInjecting ? Math.min(total, liveBulkProgress.completed) : success + failed
    const pending = Math.max(0, total - processed)
    const rate = total ? Math.round((success / total) * 100) : 0
    const processedRate = total ? Math.round((processed / total) * 100) : 0
    return { success, failed, pending, total, processed, rate, processedRate }
  }, [lastApplied, isCurrentTabInjecting, liveBulkProgress])''')
replace('src/App.tsx', '''      setLiveBulkProgress({ active: true, completed: 0, total: flagCount, applied: 0, failed: 0, outcome: "running", message: "" })''', '''      setLiveBulkProgress({ active: true, completed: 0, total: flagCount, applied: 0, failed: 0, outcome: "running", message: "", phase: "Preparing first batch" })''')
replace('src/App.tsx', '''setLiveBulkProgress({ active: Boolean(state.active), completed: Number(state.completed) || 0, total: Number(state.total) || 0, applied: Number(state.applied) || 0, failed: Number(state.failed) || 0, outcome: String(state.outcome || ""), message: String(state.message || "") })''', '''setLiveBulkProgress({ active: Boolean(state.active), completed: Number(state.completed) || 0, total: Number(state.total) || 0, applied: Number(state.applied) || 0, failed: Number(state.failed) || 0, outcome: String(state.outcome || ""), message: String(state.message || ""), phase: String(state.phase || "") })''')
replace('src/App.tsx', '''    const timer = window.setInterval(() => void poll(), 1500)''', '''    const timer = window.setInterval(() => void poll(), 500)''')
replace('src/App.tsx', '''              {liveBulkProgress.completed.toLocaleString()} / {liveBulkProgress.total.toLocaleString()} · {liveBulkProgress.applied.toLocaleString()} writes · {liveBulkProgress.failed.toLocaleString()} failed''', '''              {liveBulkProgress.completed.toLocaleString()} / {liveBulkProgress.total.toLocaleString()} checked · {liveBulkProgress.applied.toLocaleString()} reported writes · {liveBulkProgress.failed.toLocaleString()} failed
              {liveBulkProgress.completed === 0 && liveBulkProgress.phase && ` · ${liveBulkProgress.phase}`}''')
replace('src/App.tsx', '''        {!lastApplied && <div className="tab-result-empty">{lastTabSnapshot ? "This tab has changed since its last injection — retest for new results." : "No injection results for this tab yet."}</div>}''', '''        {isCurrentTabInjecting && <div className="tab-result-empty" role="status">{lastApplyStats.processed === 0 ? (liveBulkProgress.phase || "Waiting for native batch confirmations") : `Injecting: ${lastApplyStats.processed.toLocaleString()} of ${lastApplyStats.total.toLocaleString()} flags checked. Only reported native writes count as successful.`}</div>}
        {!lastApplied && !isCurrentTabInjecting && <div className="tab-result-empty">{lastTabSnapshot ? "This tab has changed since its last injection — retest for new results." : "No injection results for this tab yet."}</div>}''')
replace('src/App.tsx', '''          <div className="apply-progress-track"><span style={{ width: `${lastApplyStats.rate}%` }} /></div>''', '''          <div className="apply-progress-track" title={isCurrentTabInjecting ? `${lastApplyStats.processed} of ${lastApplyStats.total} acknowledged by native engine` : "Percent of preset with reported native writes"}><span style={{ width: `${isCurrentTabInjecting ? lastApplyStats.processedRate : lastApplyStats.rate}%` }} /></div>''')
replace('src/App.tsx', '''<div className="apply-progress-labels"><b>{lastApplyStats.rate}% reported writes</b><span>{lastApplyStats.success} writes</span><span>{lastApplyStats.failed} failed</span>{lastApplyStats.pending > 0 && <span>{lastApplyStats.pending} unattempted</span>}</div>''', '''<div className="apply-progress-labels">{isCurrentTabInjecting && <strong>{lastApplyStats.processedRate}% checked</strong>}<b>{lastApplyStats.rate}% reported writes</b><span>{lastApplyStats.success} writes</span><span>{lastApplyStats.failed} failed</span>{lastApplyStats.pending > 0 && <span>{lastApplyStats.pending} pending</span>}</div>''')
replace('src/App.tsx', '''                <span className="stat-rate"><b>{lastApplyStats.rate}%</b> of preset</span>''', '''                <span className="stat-rate"><b>{lastApplyStats.rate}%</b> reported writes</span>
                {isCurrentTabInjecting && <span><b>{lastApplyStats.processedRate}%</b> checked</span>}''')

for rel in ('package.json', 'src-tauri/tauri.conf.json', 'scripts/smoke-test-installed-app.ps1',
            'tests/test_release_integrity.py', 'tests/test_large_json_safety_248.py',
            'tests/test_ui_pacing_253.py', 'tests/test_live_ui_pacing_253.py',
            'tests/test_tab_game_profiles_254.py'):
    path = root / rel
    if not path.exists():
        continue
    content = path.read_text(encoding='utf-8')
    if '2.0.55' in content:
        path.write_text(content.replace('2.0.55', '2.0.56'), encoding='utf-8')
    elif rel in ('package.json', 'src-tauri/tauri.conf.json', 'tests/test_release_integrity.py'):
        raise RuntimeError('Expected current app version missing from ' + rel)

# Keep Rust package metadata aligned with the desktop release version.
cargo = root/'src-tauri/Cargo.toml'
content = cargo.read_text(encoding='utf-8')
import re
content, changes = re.subn(r'(?m)^version = "2\\.0\\.\\d+"
import threading
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class LiveCounterTests(unittest.TestCase):
    def test_green_detection_and_memory_access_distinction(self):
        css=(ROOT/'src/index.css').read_text(encoding='utf-8')
        ui=(ROOT/'src/App.tsx').read_text(encoding='utf-8')
        self.assertIn('.runtime-pill.detected { color: #9fe8c4',css)
        self.assertIn('.status-dot.detected { background: #48d994',css)
        self.assertIn('status.connected ? "connected" : status.processDetected ? "detected"',ui)
        self.assertIn('status.connectionIssue ?? undefined',ui)
    def test_streaming_does_not_invent_writes(self):
        backend=(ROOT/'backend/server.py').read_text(encoding='utf-8')
        body=ast.parse(backend)
        fn=next(n for n in body.body if isinstance(n,ast.FunctionDef) and n.name=='live_bulk_status')
        lock=threading.Lock()
        state={'active':True,'total':100,'completed':32,'applied':12,'failed':20,'pending':68,'phase':'Scanning'}
        ns={'_BULK_LIVE_LOCK':lock,'_BULK_LIVE_STATUS':state,
            'BULK_LIVE_CHUNK':32,'injection_status':lambda:{'active':True,'completed':4,'applied':2,'failed':2}}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),str(ROOT/'backend/server.py'),'exec'),ns)
        live=ns['live_bulk_status']()
        self.assertEqual((live['completed'],live['applied'],live['failed'],live['pending']),(36,14,22,64))
        self.assertEqual(state['completed'],32)
        ns['injection_status']=lambda:{'active':False,'completed':0,'applied':0,'failed':0}
        self.assertEqual(ns['live_bulk_status']()['completed'],32)
    def test_live_per_tab_counters_are_real(self):
        ui=(ROOT/'src/App.tsx').read_text(encoding='utf-8')
        self.assertIn('isCurrentTabInjecting',ui)
        self.assertIn('liveBulkProgress.applied',ui)
        self.assertIn('liveBulkProgress.completed',ui)
        self.assertIn('setInterval(() => void poll(), 500)',ui)
        self.assertNotIn('window.confirm(`Inject',ui)
    def test_cap_and_native_batch_still_bounded(self):
        bulk=(ROOT/'backend/zflag_bulk_safe.py').read_text(encoding='utf-8')
        server=(ROOT/'backend/server.py').read_text(encoding='utf-8')
        self.assertIn('MAX_FLAGS = 100_000',bulk)
        self.assertIn('BULK_LIVE_CHUNK = 32',server)
        self.assertIn('_BULK_LIVE_CANCEL.wait(0.25)',server)

if __name__=='__main__': unittest.main()
''', encoding='utf-8')
print('Applied v2.0.56 green detected status and live evidence-backed per-tab progress'), 'version = "2.0.56"', content, count=1)
if changes != 1:
    raise RuntimeError('Rust release version anchor missing')
cargo.write_text(content, encoding='utf-8')

(root/'tests/test_live_counter_256.py').write_text('''import ast
import threading
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class LiveCounterTests(unittest.TestCase):
    def test_green_detection_and_memory_access_distinction(self):
        css=(ROOT/'src/index.css').read_text(encoding='utf-8')
        ui=(ROOT/'src/App.tsx').read_text(encoding='utf-8')
        self.assertIn('.runtime-pill.detected { color: #9fe8c4',css)
        self.assertIn('.status-dot.detected { background: #48d994',css)
        self.assertIn('status.connected ? "connected" : status.processDetected ? "detected"',ui)
        self.assertIn('status.connectionIssue ?? undefined',ui)
    def test_streaming_does_not_invent_writes(self):
        backend=(ROOT/'backend/server.py').read_text(encoding='utf-8')
        body=ast.parse(backend)
        fn=next(n for n in body.body if isinstance(n,ast.FunctionDef) and n.name=='live_bulk_status')
        lock=threading.Lock()
        state={'active':True,'total':100,'completed':32,'applied':12,'failed':20,'pending':68,'phase':'Scanning'}
        ns={'_BULK_LIVE_LOCK':lock,'_BULK_LIVE_STATUS':state,
            'BULK_LIVE_CHUNK':32,'injection_status':lambda:{'active':True,'completed':4,'applied':2,'failed':2}}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),str(ROOT/'backend/server.py'),'exec'),ns)
        live=ns['live_bulk_status']()
        self.assertEqual((live['completed'],live['applied'],live['failed'],live['pending']),(36,14,22,64))
        self.assertEqual(state['completed'],32)
        ns['injection_status']=lambda:{'active':False,'completed':0,'applied':0,'failed':0}
        self.assertEqual(ns['live_bulk_status']()['completed'],32)
    def test_live_per_tab_counters_are_real(self):
        ui=(ROOT/'src/App.tsx').read_text(encoding='utf-8')
        self.assertIn('isCurrentTabInjecting',ui)
        self.assertIn('liveBulkProgress.applied',ui)
        self.assertIn('liveBulkProgress.completed',ui)
        self.assertIn('setInterval(() => void poll(), 500)',ui)
        self.assertNotIn('window.confirm(`Inject',ui)
    def test_cap_and_native_batch_still_bounded(self):
        bulk=(ROOT/'backend/zflag_bulk_safe.py').read_text(encoding='utf-8')
        server=(ROOT/'backend/server.py').read_text(encoding='utf-8')
        self.assertIn('MAX_FLAGS = 100_000',bulk)
        self.assertIn('BULK_LIVE_CHUNK = 32',server)
        self.assertIn('_BULK_LIVE_CANCEL.wait(0.25)',server)

if __name__=='__main__': unittest.main()
''', encoding='utf-8')
print('Applied v2.0.56 green detected status and live evidence-backed per-tab progress')