"""v2.0.56 exact-release-compatible patch: green badge and evidence-backed live counters."""
from pathlib import Path
import re, sys
root=Path(sys.argv[1])

def load(rel): return (root/rel).read_text(encoding='utf-8')
def save(rel, data): (root/rel).write_text(data, encoding='utf-8')
def once(text, a, b, label):
    n=text.count(a)
    if n!=1: raise RuntimeError(f'{label}: expected one anchor, got {n}: {a[:90]!r}')
    return text.replace(a,b,1)

css=load('src/index.css')
css=once(css,'.runtime-pill.detected { color: #f2c781 !important; border-color: rgba(226,171,74,.25) !important; background: rgba(226,171,74,.075) !important; }',
'.runtime-pill.detected { color: #9fe8c4 !important; border-color: rgba(70,209,135,.23) !important; background: rgba(52,171,118,.065) !important; }','badge')
css=once(css,'.runtime-pill .status-dot.detected { background: #f2b957 !important; box-shadow: 0 0 0 4px rgba(242,185,87,.10) !important; }',
'.runtime-pill .status-dot.detected { background: #48d994 !important; box-shadow: 0 0 0 4px rgba(72,217,148,.10) !important; }','dot')
save('src/index.css',css)

back=load('backend/server.py')
start=back.index('def live_bulk_status(')
end=back.index('def cancel_live_bulk(',start)
new_status='''def live_bulk_status():
    """Combine finished batch totals with current verified per-flag checkpoints.

    Intermediate counts are read-only and never added to stored totals. The
    worker commits a complete batch once after its native process finishes.
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


'''
back=back[:start]+new_status+back[end:]
# Exact v250 release source uses compact formatting; reviewed copy uses spaces.
pattern=r'(?m)^(?P<indent>[ \t]*)batch\s*=\s*dict\(entries\[first\s*:\s*first\s*\+\s*BULK_LIVE_CHUNK\]\)\s*\n(?P=indent)result\s*=\s*apply_enhanced\(batch,\s*source\)'
def replace_batch(m):
    pad=m.group('indent')
    insert=(f'{pad}batch=dict(entries[first:first+BULK_LIVE_CHUNK])\n'
            f'{pad}with _BULK_LIVE_LOCK:\n'
            f'{pad}    _BULK_LIVE_STATUS["phase"] = f"Scanning batch {{first // BULK_LIVE_CHUNK + 1}} / {{(len(entries) + BULK_LIVE_CHUNK - 1) // BULK_LIVE_CHUNK}}"\n'
            f'{pad}result=apply_enhanced(batch,source)')
    return insert
back,n=re.subn(pattern,replace_batch,back)
if n!=1: raise RuntimeError(f'Worker batch anchor: {n}')
# Set an initial, honest phase without inventing completed writes.
back,n=re.subn(r'(?P<start>_BULK_LIVE_STATUS\.update\(active=True,[\s\S]*?failureSamples\s*=\s*\[\]\))',
    lambda m: m.group('start')[:-1]+', phase="Preparing first batch")',back,count=1)
if n!=1: raise RuntimeError('Missing bulk starting status')
save('backend/server.py',back)

ui=load('src/App.tsx')
# Current version has a single-line state initializer, but the spacing varies.
pattern=r'const \[liveBulkProgress, setLiveBulkProgress\] = useState\(\{([^\n]+?)\}\)'
def add_phase(m):
    if 'phase:' in m.group(1): return m.group(0)
    return m.group(0)[:-2]+',phase:""})'
ui,n=re.subn(pattern,add_phase,ui,count=1)
if n!=1: raise RuntimeError('Missing progress initializer')
# Two updates: initialization and poll. Keep their existing fields.
pattern=r'setLiveBulkProgress\(\{([^\n]*?)\}\)'
updates=0
def patch_state(m):
    global updates
    updates += 1
    content=m.group(1)
    if 'phase:' in content: return m.group(0)
    if 'state.' in content:
        return 'setLiveBulkProgress({' + content + ',phase:String(state.phase || "")})'
    return 'setLiveBulkProgress({' + content + ',phase:"Preparing first batch"})'
ui=re.sub(pattern,patch_state,ui)
if updates<2: raise RuntimeError(f'Expected >=2 progress updates: {updates}')
# v254 tab-scoped stats; use the streaming state only for the active running tab.
start=ui.index('  const lastApplied = snapshotMatchesTab &&')
end=ui.index('  const failedResults =',start)
ui=ui[:start]+'''  const isCurrentTabInjecting = liveBulkActive && liveBulkOwnerRef.current?.tabId === activeTab?.id
  const lastApplied = snapshotMatchesTab && !isCurrentTabInjecting ? lastTabSnapshot : undefined
  const lastApplyStats = useMemo(() => {
    const success = isCurrentTabInjecting ? liveBulkProgress.applied : (lastApplied?.applied ?? 0)
    const failed = isCurrentTabInjecting ? liveBulkProgress.failed : (lastApplied?.errors ?? 0)
    const total = isCurrentTabInjecting ? liveBulkProgress.total : success + failed + (lastApplied?.pending ?? 0)
    const processed = isCurrentTabInjecting ? Math.min(total, liveBulkProgress.completed) : success + failed
    const pending = Math.max(0, total - processed)
    const rate = total ? Math.round(success * 100 / total) : 0
    const processedRate = total ? Math.round(processed * 100 / total) : 0
    return { success, failed, pending, total, processed, rate, processedRate }
  }, [lastApplied, isCurrentTabInjecting, liveBulkProgress])
'''+ui[end:]
ui,n=re.subn(r'setInterval\(\(\)\s*=>\s*void poll\(\),\s*1500\)', 'setInterval(()=>void poll(),500)',ui,count=1)
if n!=1: raise RuntimeError('Missing bulk polling interval')
# Replace only the live-bulk toolbar progress chip.
start=ui.index('{liveBulkActive && <span className="zflag-inject-progress"')
end=ui.index('</span>}',start)+len('</span>}')
ui=ui[:start]+'''{liveBulkActive && <span className="zflag-inject-progress" role="status" title="Verified native acknowledgments, not guaranteed in-game effects">
              {liveBulkProgress.completed.toLocaleString()} / {liveBulkProgress.total.toLocaleString()} checked · {liveBulkProgress.applied.toLocaleString()} writes · {liveBulkProgress.failed.toLocaleString()} failed
              {liveBulkProgress.completed === 0 ? ` · ${liveBulkProgress.phase || "Scanning first batch"}` : ""}
              {liveBulkProgress.completed >= 64 && liveBulkStartedAt > 0 && liveBulkProgress.total > liveBulkProgress.completed
                ? ` · ETA ~${Math.max(1, Math.ceil(((Date.now() - liveBulkStartedAt) / 1000) * (liveBulkProgress.total - liveBulkProgress.completed) / liveBulkProgress.completed))}s` : ""}
            </span>}'''+ui[end:]
msg='{!lastApplied && <div className="tab-result-empty">{lastTabSnapshot ? "This tab has changed since its last injection — retest for new results." : "No injection results for this tab yet."}</div>}'
ui=once(ui,msg,'''{isCurrentTabInjecting && <div className="tab-result-empty" role="status">{lastApplyStats.processed === 0 ? (liveBulkProgress.phase || "Scanning first batch") : `Live: ${lastApplyStats.processed.toLocaleString()} of ${lastApplyStats.total.toLocaleString()} flags checked; only confirmed native write responses count.`}</div>}
        {!isCurrentTabInjecting && !lastApplied && <div className="tab-result-empty">{lastTabSnapshot ? "This tab has changed since its last injection — retest for new results." : "No injection results for this tab yet."}</div>}''','old stats notice')
track='<div className="apply-progress-track"><span style={{ width: `${lastApplyStats.rate}%` }} /></div>'
ui=once(ui,track,'''<div className="apply-progress-track" title={isCurrentTabInjecting ? "Percent of flags with native acknowledgment" : "Percent of preset with native writes"}><span style={{ width: `${isCurrentTabInjecting ? lastApplyStats.processedRate : lastApplyStats.rate}%` }} /></div>''','progress bar')
needle='<div className="apply-progress-labels"><b>{lastApplyStats.rate}% reported writes</b><span>{lastApplyStats.success} writes</span><span>{lastApplyStats.failed} failed</span>{lastApplyStats.pending > 0 && <span>{lastApplyStats.pending} unattempted</span>}</div>'
ui=once(ui,needle,'''<div className="apply-progress-labels">{isCurrentTabInjecting && <strong>{lastApplyStats.processedRate}% checked</strong>}<b>{lastApplyStats.rate}% reported writes</b><span>{lastApplyStats.success} writes</span><span>{lastApplyStats.failed} failed</span>{lastApplyStats.pending > 0 && <span>{lastApplyStats.pending} pending</span>}</div>''','progress stats')
needle='<span className="stat-rate"><b>{lastApplyStats.rate}%</b> of preset</span>'
ui=once(ui,needle,'''<span className="stat-rate"><b>{lastApplyStats.rate}%</b> reported writes</span>{isCurrentTabInjecting && <span><b>{lastApplyStats.processedRate}%</b> checked</span>}''','bottom stats')
save('src/App.tsx',ui)

for rel in ('package.json','src-tauri/tauri.conf.json','scripts/smoke-test-installed-app.ps1',
  'tests/test_release_integrity.py','tests/test_large_json_safety_248.py','tests/test_ui_pacing_253.py',
  'tests/test_live_ui_pacing_253.py','tests/test_tab_game_profiles_254.py'):
    p=root/rel
    if not p.is_file(): continue
    t=p.read_text(encoding='utf-8')
    if '2.0.55' in t: p.write_text(t.replace('2.0.55','2.0.56'),encoding='utf-8')
    elif rel in ('package.json','src-tauri/tauri.conf.json','tests/test_release_integrity.py'):
        raise RuntimeError('Missing version 2.0.55 in '+rel)

cargo=root/'src-tauri/Cargo.toml'
s=cargo.read_text(encoding='utf-8')
s,n=re.subn(r'(?m)^version = "2\.0\.\d+"$', 'version = "2.0.56"',s,count=1)
if n!=1: raise RuntimeError('Cargo.toml semver not found')
cargo.write_text(s,encoding='utf-8')

(root/'tests/test_streaming_256.py').write_text('''import ast, threading, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class LiveCounterTest(unittest.TestCase):
    def test_green_status(self):
        css=(ROOT/'src/index.css').read_text(encoding='utf-8')
        self.assertIn('.runtime-pill.detected { color: #9fe8c4',css)
        self.assertIn('.status-dot.detected { background: #48d994',css)
    def test_interim_counts_not_committed(self):
        backend=(ROOT/'backend/server.py').read_text(encoding='utf-8')
        fn=next(x for x in ast.parse(backend).body if isinstance(x,ast.FunctionDef) and x.name=='live_bulk_status')
        base={'active':True,'total':100,'completed':32,'applied':12,'failed':20,'pending':68}
        env={'_BULK_LIVE_LOCK':threading.Lock(),'_BULK_LIVE_STATUS':base,'BULK_LIVE_CHUNK':32,
        'injection_status':lambda:{'active':True,'completed':4,'applied':2,'failed':2}}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'<mock>','exec'),env)
        shown=env['live_bulk_status']()
        self.assertEqual((shown['completed'],shown['applied'],shown['failed'],shown['pending']),(36,14,22,64))
        self.assertEqual(base['completed'],32)
    def test_ui_updates_live_without_fake_success(self):
        ui=(ROOT/'src/App.tsx').read_text(encoding='utf-8')
        self.assertIn('isCurrentTabInjecting',ui)
        self.assertIn('lastApplyStats.processedRate',ui)
        self.assertIn('setInterval(()=>void poll(),500)',ui)
    def test_bulk_preserves_limits(self):
        src=(ROOT/'backend/server.py').read_text(encoding='utf-8')
        bulk=(ROOT/'backend/zflag_bulk_safe.py').read_text(encoding='utf-8')
        self.assertIn('BULK_LIVE_CHUNK = 32',src)
        self.assertIn('MAX_FLAGS = 100_000',bulk)
''',encoding='utf-8')
print('Applied v2.0.56 green status and live native checkpoint counters')