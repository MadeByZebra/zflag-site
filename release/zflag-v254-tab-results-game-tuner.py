"""ZFLAG v2.0.54: truthful per-tab results and nondestructive game tuner.
Run after ZFLAG v2.0.53 patches. Uses only read-only local Roblox logs for game ID.
"""
from pathlib import Path
import sys
root=Path(sys.argv[1])

def put(rel, old, new):
    p=root/rel
    s=p.read_text(encoding='utf-8')
    count=s.count(old)
    if count!=1:
        raise RuntimeError(f'{rel}: expected one anchor, found {count}: {old[:120]!r}')
    p.write_text(s.replace(old,new,1),encoding='utf-8')

# Statistics are scoped by stable tab ID and exact parsed data, not whichever tab applied last.
put('src/App.tsx','import { FlagLibrary } from "./FlagLibrary"', 'import { FlagLibrary } from "./FlagLibrary"\nimport { buildTunedConfig, parsePlaceId, type TuneGoal } from "./gameTuner"')
put('src/App.tsx','''  const lastApplied = applyHistory[0]
  const lastApplyStats = useMemo(() => {
    const success = lastApplied?.applied ?? 0
    const failed = lastApplied?.errors ?? 0
    const total = success + failed
    const rate = total ? Math.round((success / total) * 100) : 0
    return { success, failed, total, rate }
  }, [lastApplied?.id, lastApplied?.applied, lastApplied?.errors])''','''  const lastTabSnapshot = useMemo(() => applyHistory.find((item) => item.tabId === activeTab?.id), [applyHistory, activeTab?.id])
  const snapshotMatchesTab = useMemo(() => {
    if (!lastTabSnapshot || !parsed.ok) return false
    try { return JSON.stringify(JSON.parse(lastTabSnapshot.content)) === JSON.stringify(parsed.value) }
    catch { return false }
  }, [lastTabSnapshot, parsed])
  const lastApplied = snapshotMatchesTab && !(liveBulkActive && liveBulkOwnerRef.current?.tabId === activeTab?.id) ? lastTabSnapshot : undefined
  const lastApplyStats = useMemo(() => {
    const success = lastApplied?.applied ?? 0
    const failed = lastApplied?.errors ?? 0
    const pending = lastApplied?.pending ?? 0
    const total = success + failed + pending
    const rate = total ? Math.round((success / total) * 100) : 0
    return { success, failed, pending, total, rate }
  }, [lastApplied])''')
put('src/App.tsx','''    const current = applyHistory[0]?.results ?? []
    const previous = applyHistory[1]?.results ?? []''','''    const historyForTab = applyHistory.filter((item) => item.tabId === activeTab?.id)
    const current = lastApplied?.results ?? []
    const previous = historyForTab.find((item) => item.id !== lastApplied?.id)?.results ?? []''')
put('src/App.tsx','''  }, [applyHistory])
  const tabApplyStats = useMemo(() => {
    const map = new Map<string, { applied: number; errors: number }>()
    for (const snapshot of applyHistory) {
      if (snapshot.tabId && !map.has(snapshot.tabId)) map.set(snapshot.tabId, { applied: snapshot.applied, errors: snapshot.errors })
    }
    return map
  }, [applyHistory])''','''  }, [applyHistory, activeTab?.id, lastApplied])
  const tabApplyStats = useMemo(() => {
    const map = new Map<string, { applied: number; errors: number; pending: number; stale: boolean }>()
    for (const snapshot of applyHistory) {
      if (!snapshot.tabId || map.has(snapshot.tabId)) continue
      const tab = tabs.find((candidate) => candidate.id === snapshot.tabId)
      if (!tab) continue
      let stale = true
      try { stale = JSON.stringify(JSON.parse(snapshot.content)) !== JSON.stringify(JSON.parse(tab.content)) }
      catch { /* edited/invalid JSON needs another test */ }
      map.set(snapshot.tabId, { applied: snapshot.applied, errors: snapshot.errors,
        pending: snapshot.pending ?? 0, stale })
    }
    return map
  }, [applyHistory, tabs])''')
put('src/App.tsx','''const lastAppliedParsed = useMemo(() => safeParse<Record<string, unknown>>(lastApplied?.content ?? null, {}), [lastApplied?.id])''','''const lastAppliedParsed = useMemo(() => safeParse<Record<string, unknown>>(lastTabSnapshot?.content ?? null, {}), [lastTabSnapshot?.id])''')
put('src/App.tsx','''              {stats && <span className="tab-apply-stats"><i>✓{stats.applied}</i><em>✕{stats.errors}</em></span>}''','''              {stats && <span className="tab-apply-stats" title={stats.stale ? "File changed since the last injection — results need retesting" : "Reported native writes, failed attempts and unattempted entries"}>
                {stats.stale ? <small>Retest</small> : <><i>✓{stats.applied}</i><em>✕{stats.errors}</em>{stats.pending > 0 && <small>?{stats.pending}</small>}</>}
              </span>}''')
put('src/App.tsx','''        {lastApplyStats.total > 0 && lastApplyStats.total === flagCount && !liveBulkActive && <div className="apply-progress-row">''','''        {!lastApplied && <div className="tab-result-empty">{lastTabSnapshot ? "This tab has changed since its last injection — retest for new results." : "No injection results for this tab yet."}</div>}
        {lastApplyStats.total > 0 && <div className="apply-progress-row">''')
put('src/App.tsx','''<b>{lastApplyStats.rate}% success</b><span>{lastApplyStats.success} applied</span><span>{lastApplyStats.failed} failed</span>''','''<b>{lastApplyStats.rate}% reported writes</b><span>{lastApplyStats.success} writes</span><span>{lastApplyStats.failed} failed</span>{lastApplyStats.pending > 0 && <span>{lastApplyStats.pending} unattempted</span>}''')
put('src/App.tsx','''<span className="stat-success"><b>{lastApplyStats.success}</b> success</span>
                <span className="stat-error"><b>{lastApplyStats.failed}</b> errors</span>
                <span><b>{lastApplyStats.total}</b> total</span>
                <span className="stat-rate"><b>{lastApplyStats.rate}%</b> rate</span>''','''<span className="stat-success"><b>{lastApplyStats.success}</b> reported writes</span>
                <span className="stat-error"><b>{lastApplyStats.failed}</b> failed</span>
                <span><b>{lastApplyStats.pending}</b> unattempted</span>
                <span className="stat-rate"><b>{lastApplyStats.rate}%</b> of preset</span>''')
put('src/App.tsx','''<span className="activity-result-count">{groupedActivity.length} groups</span>''','''<span className="activity-result-count" title="Backend logs are global, not assigned to any particular JSON file">Backend-wide log · {groupedActivity.length} groups</span>''')
put('src/App.tsx','''<div><span>Last apply</span><strong>{lastApplyStats.success} / {lastApplyStats.total}</strong></div>''','''<div><span>Current tab's last injection</span><strong>{lastApplied ? `${lastApplyStats.success} reported / ${lastApplyStats.total}` : "Not tested"}</strong></div>''')

# Preserve a full per-tab snapshot even if the user switches documents while a live bulk job runs.
put('src/App.tsx','''  const [liveBulkActive, setLiveBulkActive] = useState(false)''','''  const [liveBulkActive, setLiveBulkActive] = useState(false)
  const liveBulkOwnerRef = useRef<{ tabId: string; name: string; content: string } | null>(null)''')
put('src/App.tsx','''      setLiveBulkStartedAt(Date.now())
      setLiveBulkActive(true)''','''      liveBulkOwnerRef.current = activeTab ? { tabId: activeTab.id, name: activeTab.name, content: text } : null
      setLiveBulkStartedAt(Date.now())
      setLiveBulkActive(true)''')
put('src/App.tsx','''      showToast("Injection not started"''','''      liveBulkOwnerRef.current = null
      showToast("Injection not started"''')
put('src/App.tsx','''        if (!state.active) {
          setLiveBulkActive(false)''','''        if (!state.active) {
          const owner = liveBulkOwnerRef.current
          if (owner) {
            const applied = Math.max(0, Number(state.applied) || 0)
            const errors = Math.max(0, Number(state.failed) || 0)
            const pending = Math.max(0, Number(state.pending) || 0)
            const results: ApplyResultEntry[] = Array.isArray(state.failureSamples)
              ? state.failureSamples.slice(0, 100).filter((entry: unknown) => entry && typeof entry === "object")
                  .map((entry: { name?: string; message?: string }) => ({ name: String(entry.name || ""), ok: false, message: String(entry.message || "native failure") }))
              : []
            const snapshot: ApplySnapshot = { id: uid("apply"), tabId: owner.tabId, name: owner.name,
              content: owner.content, appliedAt: Date.now(), applied, errors, pending,
              interrupted: state.outcome !== "completed" || pending > 0, source: "live-bulk", results }
            setApplyHistory((current) => [snapshot, ...current].slice(0, 50))
            liveBulkOwnerRef.current = null
          }
          setLiveBulkActive(false)''')
put('src/App.tsx','''            <span className="inject-engine-label" title="Runtime engine">''','''            {liveBulkActive && liveBulkOwnerRef.current?.tabId !== activeTab?.id && <span className="zflag-inject-progress">Injecting another tab: {liveBulkOwnerRef.current?.name}</span>}
            <span className="inject-engine-label" title="Runtime engine · change in Settings → General">''')
put('src/App.tsx','''{lastApplyStats.total > 0 && <div className="apply-progress-row">''','''{lastApplyStats.total > 0 && <div className="apply-progress-row">''') if False else None

# Reset validation when editing/switching tabs. It must not show results from another file.
put('src/App.tsx','''  const [preflight, setPreflight] = useState<PreflightResult | null>(null)''','''  const [preflight, setPreflight] = useState<PreflightResult | null>(null)
  const preflightTabId = useRef<string | null>(null)''')
put('src/App.tsx','''  const preflightMap = useMemo(() => new Map((preflight?.entries ?? []).map((entry) => [entry.name, entry])), [preflight])''','''  const activePreflight = preflightTabId.current === activeTab?.id ? preflight : null
  const preflightMap = useMemo(() => new Map((activePreflight?.entries ?? []).map((entry) => [entry.name, entry])), [activePreflight])''')
put('src/App.tsx','''    const entries = preflight?.entries ?? []''','''    const entries = activePreflight?.entries ?? []''')
put('src/App.tsx','''  }, [preflight, preflightPrefix, favoriteFlags])''','''  }, [activePreflight, preflightPrefix, favoriteFlags])''')
# Preserve original code using preflight for current tab until tab switch.
put('src/App.tsx','''  const [gameTunerNeverExists, setGameTunerNeverExists]''','''none''') if False else None

# Keep preflight data scoped to one tab and clear it when that tab's contents change.
put('src/App.tsx', '      setPreflight(result)', '      preflightTabId.current = activeTab?.id ?? null\n      setPreflight(result)')
put('src/App.tsx', '  const lastTabSnapshot = useMemo(', '  useEffect(() => { setPreflight(null); setPreflightOpen(false) }, [activeTabId, text])\n  const lastTabSnapshot = useMemo(')

# Game tuner: no deletions. All modifications previewed in a new tab, no automatic apply.
put('src/App.tsx','''  const [activityFilter, setActivityFilter] = useState<ActivityFilter>("all")''','''  const [activityFilter, setActivityFilter] = useState<ActivityFilter>("all")
  const [gameTunerOpen, setGameTunerOpen] = useState(false)
  const [gameIdInput, setGameIdInput] = useState("")
  const [gameIdentityHint, setGameIdentityHint] = useState("")
  const [tuneGoal, setTuneGoal] = useState<TuneGoal>("balanced")
  const [observedFps, setObservedFps] = useState("")
  const [targetFps, setTargetFps] = useState("60")''')
put('src/App.tsx','''  const flagCount = useMemo(() => parsed.ok ? Object.keys(parsed.value).length : 0, [parsed])''','''  const flagCount = useMemo(() => parsed.ok ? Object.keys(parsed.value).length : 0, [parsed])
  const gameTunePlan = useMemo(() => buildTunedConfig(parsed.ok ? parsed.value : {}, tuneGoal, Number(observedFps) || null, Number(targetFps) || 60), [parsed, tuneGoal, observedFps, targetFps])
  const selectedPlaceId = parsePlaceId(gameIdInput)''')
put('src/App.tsx','''  function renderPresets() {''','''  async function detectCurrentGame() {
    try {
      const response = await fetch(`${settings.apiUrl}/game/identity`, { cache: "no-store", signal: AbortSignal.timeout(5000) })
      const result = await response.json()
      if (!response.ok || !result.detected || !result.placeId) throw new Error(result.note || "Game ID not available in recent Roblox logs")
      setGameIdInput(String(result.placeId))
      setGameIdentityHint("Best-effort ID from a recent Roblox log; confirm this matches your current game.")
      showToast("Possible game detected", `Place ID ${result.placeId}; verify before tuning`, "info")
    } catch (err) {
      setGameIdentityHint("Could not reliably identify the game automatically. Paste its Roblox game link or Place ID.")
      showToast("Game ID unavailable", err instanceof Error ? err.message : "Paste the game URL or Place ID", "warning")
    }
  }

  function createTunedCopy() {
    if (!parsed.ok || !activeTab) { showToast("Fix JSON first", parsed.error, "warning"); return }
    if (!selectedPlaceId) { showToast("Game ID needed", "Enter or detect a Roblox place ID so this profile can be named", "warning"); return }
    if (!gameTunePlan.changes.length) { showToast("No compatible edits", "No known graphics flags can safely be recommended from this file. No flags were removed.", "info"); return }
    if (Object.keys(gameTunePlan.flags).length !== flagCount) { showToast("Safety check failed", "All original flag names must be preserved", "error"); return }
    const title = `${activeTab.name.replace(/\\.json$/i, "")}-game-${selectedPlaceId}-${tuneGoal}.json`
    newTab(JSON.stringify(gameTunePlan.flags, null, 2), title)
    showToast("Game-tuned copy created", `${flagCount.toLocaleString()} keys preserved, ${gameTunePlan.changes.length} value suggestions. Original tab unchanged.`, "success")
  }

  function renderPresets() {''')
put('src/App.tsx','''            <button type="button" onClick={() => setSaveDialog({ mode: "preset", value: activeTab?.name.replace(/\\.json$/i, "") ?? "My preset" })}><WandSparkles className="size-3.5" /> Preset</button>''','''            <button type="button" onClick={() => setGameTunerOpen((open) => !open)} aria-expanded={gameTunerOpen}><WandSparkles className="size-3.5" /> Tune for game</button>
            <button type="button" onClick={() => setSaveDialog({ mode: "preset", value: activeTab?.name.replace(/\\.json$/i, "") ?? "My preset" })}><WandSparkles className="size-3.5" /> Preset</button>''')
put('src/App.tsx','''        <div className="diff-strip">''','''        {gameTunerOpen && <section className="game-tuner-panel" aria-label="Game-specific profile tuner">
          <div className="game-tuner-title"><strong>Game profile tuner</strong><span>Preserves every original FastFlag. Creates a separate preview tab; never auto-injects.</span></div>
          <div className="game-tuner-fields">
            <label>Roblox game URL or Place ID<input value={gameIdInput} onChange={(e) => { setGameIdInput(e.target.value); setGameIdentityHint("") }} placeholder="https://www.roblox.com/games/1234567/..." /></label>
            <button type="button" onClick={() => void detectCurrentGame()}>Detect active game (best effort)</button>
            <label>Goal<select value={tuneGoal} onChange={(e) => setTuneGoal(e.target.value as TuneGoal)}><option value="fps">Higher FPS</option><option value="balanced">Balanced</option><option value="visual">Visual quality</option></select></label>
            <label>Observed FPS<input type="number" min="1" max="1000" value={observedFps} onChange={(e) => setObservedFps(e.target.value)} placeholder="Measure with Roblox stats" /></label>
            <label>Target FPS<input type="number" min="15" max="1000" value={targetFps} onChange={(e) => setTargetFps(e.target.value)} /></label>
          </div>
          <div className="game-tuner-summary"><span>{selectedPlaceId ? `Place ID ${selectedPlaceId}` : "Game ID not entered"}</span><span>{flagCount.toLocaleString()} original flags retained</span><span>{gameTunePlan.changes.length} value changes proposed</span></div>
          {!!gameIdentityHint && <p>{gameIdentityHint}</p>}
          <p>Roblox logs may not contain the active game. ZFLAG does not read the game's private contents or automatically measure FPS. Compare FPS and stability before and after changing these settings.</p>
          {gameTunePlan.changes.length > 0 && <div className="game-tuner-changes">{gameTunePlan.changes.map((item) => <div key={item.name}><code>{item.name}</code><span>{String(item.from)} → {String(item.to)}</span></div>)}</div>}
          <button type="button" disabled={!selectedPlaceId || !parsed.ok || !gameTunePlan.changes.length} onClick={createTunedCopy}>Create tuned copy — keep all {flagCount.toLocaleString()} flags</button>
        </section>}
        <div className="diff-strip">''')

# Read-only best-effort log extraction of placeId. No raw log content exposed.
put('backend/server.py','''from zflag_bulk_safe import MAX_FLAGS, BULK_THRESHOLD, stage_player_config, prepare_bulk''','''from zflag_bulk_safe import MAX_FLAGS, BULK_THRESHOLD, stage_player_config, prepare_bulk
from game_identity import detect_game_from_logs''')
put('backend/server.py','''        if parsed.path == "/bulk-live/status":''','''        if parsed.path == "/game/identity":
            self._json(200, detect_game_from_logs())
            return
        if parsed.path == "/bulk-live/status":''')
for rel in ('package.json','src-tauri/tauri.conf.json','scripts/smoke-test-installed-app.ps1',
            'tests/test_release_integrity.py', 'tests/test_large_json_safety_248.py', 'tests/test_ui_pacing_253.py', 'tests/test_live_ui_pacing_253.py'):
    p=root/rel
    if not p.is_file(): continue
    text=p.read_text(encoding='utf-8')
    if '2.0.53' in text: p.write_text(text.replace('2.0.53','2.0.54'),encoding='utf-8')
    elif rel in ('package.json','src-tauri/tauri.conf.json','tests/test_release_integrity.py'):
        raise RuntimeError('Missing baseline 2.0.53 in '+rel)

# Keep the game tuner styled in the existing dark Bklit-inspired theme.
with (root/'src/index.css').open('a',encoding='utf-8') as css:
    css.write("""
/* v2.0.54: quiet, reversible per-game tuning panel */
.tab-result-empty { padding: 7px 14px; font-size: 11px; color: var(--muted-foreground, #999); border-bottom: 1px solid rgba(255,255,255,.06); }
.game-tuner-panel { margin: 10px 12px; padding: 14px; border: 1px solid rgba(255,255,255,.12); border-radius: 11px; background: rgba(19,21,25,.78); display: grid; gap: 10px; }
.game-tuner-title { display:flex; gap: 9px; align-items:baseline; flex-wrap:wrap; }
.game-tuner-title strong { font-size: 13px; color: #eee; }
.game-tuner-title span,.game-tuner-panel p { font-size: 11px; color:#a3a6ad; margin:0; }
.game-tuner-fields { display: grid; grid-template-columns: minmax(180px,2fr) auto repeat(3,minmax(85px,1fr)); align-items:end; gap: 8px; }
.game-tuner-fields label { display:grid; gap:5px; min-width:0; color:#a5a6ab; font-size:10px; }
.game-tuner-fields input,.game-tuner-fields select { width:100%; min-width:0; border:1px solid rgba(255,255,255,.15); background:#111317; color:#eee; border-radius:6px; padding:8px; font-size:12px; }
.game-tuner-panel button { background:#21252c; color:#eee; border:1px solid rgba(255,255,255,.15); border-radius:6px; padding:8px 11px; font-size:11px; }
.game-tuner-panel button:disabled { opacity:.45; cursor:not-allowed; }
.game-tuner-summary { display:flex; flex-wrap:wrap; gap:11px; font-size:11px; color:#d1d6df; }
.game-tuner-changes { max-height:130px; overflow:auto; display:grid; gap:5px; }
.game-tuner-changes>div { display:flex; justify-content:space-between; gap:10px; color:#bcbfc5; font-size:11px; }
.game-tuner-changes code { color:#e3e5e7; font-size:11px; overflow-wrap:anywhere; }
@media (max-width: 1100px) { .game-tuner-fields { grid-template-columns: repeat(2,minmax(0,1fr)); } }
@media (max-width: 560px) { .game-tuner-fields { grid-template-columns:1fr; } }
""")

(root/'src/gameTuner.ts').write_text('''export type TuneGoal = "fps" | "balanced" | "visual"
export type TuneChange = { name: string; from: unknown; to: unknown }

export function parsePlaceId(input: string): string | null {
  const trimmed = input.trim()
  const match = /(?:^|\\/games\\/|\\?placeId=)(\\d{4,20})(?:$|[\\/?#&])/i.exec(trimmed)
  return match ? match[1] : null
}

// Known Roblox local graphics overrides only; not a blanket promise that these
// work on every Roblox version or improve FPS in every game. Never add/remove keys.
const GRAPHICS_PROFILES: Record<TuneGoal, Record<string, number | boolean>> = {
  fps: { DFIntDebugFRMQualityLevelOverride: 2, DFIntTextureQualityOverride: 0,
    FIntDebugForceMSAASamples: 1, FIntFRMMaxGrassDistance: 0, FIntFRMMinGrassDistance: 0 },
  balanced: { DFIntDebugFRMQualityLevelOverride: 5, DFIntTextureQualityOverride: 1,
    FIntDebugForceMSAASamples: 2, FIntFRMMaxGrassDistance: 80, FIntFRMMinGrassDistance: 40 },
  visual: { DFIntDebugFRMQualityLevelOverride: 8, DFIntTextureQualityOverride: 2,
    FIntDebugForceMSAASamples: 4, FIntFRMMaxGrassDistance: 400, FIntFRMMinGrassDistance: 160 },
}

export function buildTunedConfig(
  original: Record<string, unknown>, goal: TuneGoal,
  observedFps: number | null, targetFps: number,
): { flags: Record<string, unknown>; changes: TuneChange[]; rationale: string } {
  const flags = { ...original }
  const changes: TuneChange[] = []
  // If significantly under target FPS, advise the FPS profile, but never
  // silently switch the user's selected goal.
  const belowTarget = observedFps !== null && Number.isFinite(observedFps) && observedFps > 0
    && Number.isFinite(targetFps) && targetFps > 0 && observedFps < 0.85 * targetFps
  for (const [key, candidate] of Object.entries(GRAPHICS_PROFILES[goal])) {
    if (!Object.prototype.hasOwnProperty.call(flags, key)) continue
    // Changing existing numeric overrides only. Preserve representation type.
    const before = flags[key]
    if (typeof before !== 'number' && typeof before !== 'string') continue
    if (typeof before === 'string' && !/^-?\\d+$/.test(before)) continue
    const next = typeof before === 'string' ? String(candidate) : candidate
    if (before !== next) {
      flags[key] = next
      changes.push({ name: key, from: before, to: next })
    }
  }
  return { flags, changes, rationale: belowTarget ? "Measured FPS is below target; consider Higher FPS and compare performance." : "Compare in-game FPS and stability before choosing a profile." }
}
''',encoding='utf-8')

(root/'backend/game_identity.py').write_text('''"""Read only a minimal numeric place ID from recent Roblox logs, never raw log text."""
from __future__ import annotations
import os
from pathlib import Path
import re
import time

_PLACE = re.compile(rb'(?i)\\bplace(?:_|\\s*)id\\b[\\s\":=]+(\\d{4,20})\\b')

def detect_game_from_logs(*, log_dir: Path | None = None, now: float | None = None) -> dict:
    if log_dir is None:
        local = os.environ.get('LOCALAPPDATA')
        if not local:
            return {'ok': True, 'detected': False, 'note': 'Roblox log location unavailable'}
        log_dir = Path(local) / 'Roblox' / 'logs'
    now = now if now is not None else time.time()
    if not log_dir.is_dir():
        return {'ok': True, 'detected': False, 'note': 'No local Roblox logs found'}
    try:
        candidates = sorted(
            (p for p in log_dir.glob('*.log') if p.is_file() and 0 <= now - p.stat().st_mtime < 1800),
            key=lambda p: p.stat().st_mtime, reverse=True)[:4]
        for path in candidates:
            with path.open('rb') as fh:
                fh.seek(0, 2)
                fh.seek(max(0, fh.tell() - 262144))
                data = fh.read(262144)
            hits = _PLACE.findall(data)
            if hits:
                return {'ok': True, 'detected': True, 'placeId': hits[-1].decode('ascii'),
                        'source': 'recent Roblox log', 'note': 'Best effort, may be stale. Confirm against the game page.'}
    except (OSError, ValueError):
        pass
    return {'ok': True, 'detected': False, 'note': 'Current Roblox place ID was not found in recent logs. Paste its game URL.'}
''',encoding='utf-8')

(root/'tests/test_tab_game_profiles_254.py').write_text('''import json
import tempfile
import unittest
from pathlib import Path
from sys import path as sys_path
ROOT=Path(__file__).resolve().parents[1]
sys_path.insert(0,str(ROOT/'backend'))
from game_identity import detect_game_from_logs
class PerTabAndGameProfiles(unittest.TestCase):
    def test_results_scoped_by_tab_and_content(self):
        src=(ROOT/'src/App.tsx').read_text(encoding='utf-8')
        self.assertIn('item.tabId === activeTab?.id',src)
        self.assertIn('snapshotMatchesTab',src)
        self.assertIn('liveBulkOwnerRef.current',src)
        self.assertIn('setApplyHistory((current) => [snapshot, ...current]',src)
        self.assertIn('not tested',src.lower())
    def test_preservation_and_no_auto_apply(self):
        js=(ROOT/'src/gameTuner.ts').read_text(encoding='utf-8')
        ui=(ROOT/'src/App.tsx').read_text(encoding='utf-8')
        self.assertIn('const flags = { ...original }',js)
        self.assertIn('newTab(JSON.stringify(gameTunePlan.flags',ui)
        self.assertIn('Object.keys(gameTunePlan.flags).length !== flagCount',ui)
        self.assertNotIn('applyFlags(',js)
    def test_log_parses_numeric_id_only(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'Player.log'
            f.write_text('join placeId: 12345678; some private data not returned')
            result=detect_game_from_logs(log_dir=Path(td))
            self.assertEqual(result['placeId'],'12345678')
            self.assertNotIn('private',json.dumps(result))
''',encoding='utf-8')
print('Applied v2.0.54: per-tab injection accounting, preservation-safe game profiles, and best-effort place ID detection')