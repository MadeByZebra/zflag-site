"""ZFLAG 2.0.50: explicit, paced live bulk injection in Windows release source."""
from pathlib import Path
import sys

root=Path(sys.argv[1])
def put(path, old, new):
    p=root/path
    s=p.read_text(encoding="utf-8")
    assert old in s, "Missing patch anchor: "+str(path)+" "+old[:90]
    p.write_text(s.replace(old,new,1),encoding="utf-8")

put("backend/server.py", "class Runtime:\n", '''
# Only explicit user-confirmed large live batches use this path.
# The Enhanced native engine sees a maximum of 32 entries per subprocess.
_BULK_LIVE_LOCK = threading.Lock()
_BULK_LIVE_CANCEL = threading.Event()
_BULK_LIVE_STATUS = {"active":False,"total":0,"completed":0,"applied":0,"failed":0,"pending":0,"outcome":"idle","message":""}
BULK_LIVE_CHUNK = 32

def live_bulk_status():
    with _BULK_LIVE_LOCK:
        return dict(_BULK_LIVE_STATUS)

def cancel_live_bulk():
    with _BULK_LIVE_LOCK:
        if not _BULK_LIVE_STATUS["active"]:
            return {"ok":False,"error":"No live injection is running"}
        _BULK_LIVE_CANCEL.set()
    return {"ok":True,"message":"Stopping after the current native batch"}

def _live_bulk_worker(flags, source, pid):
    accepted = rejected = processed = 0
    outcome, message = "completed", ""
    failed_samples = []
    try:
        entries = list(flags.items())
        for first in range(0,len(entries),BULK_LIVE_CHUNK):
            if _BULK_LIVE_CANCEL.is_set():
                outcome,message="cancelled","Cancelled before the next batch"
                break
            if find_pid(TARGET) != pid:
                outcome,message="interrupted","Roblox closed or restarted; stopped live injection"
                break
            batch=dict(entries[first:first+BULK_LIVE_CHUNK])
            result=apply_enhanced(batch,source)
            rows=result.get("results",[])
            if not isinstance(rows,list):
                rows=[]
            done=len(rows)
            ok=sum(row.get("ok") is True for row in rows if isinstance(row,dict))
            processed+=done
            accepted+=ok
            rejected+=done-ok
            for row in rows:
                if isinstance(row,dict) and row.get("ok") is False and len(failed_samples)<100:
                    failed_samples.append({"name":str(row.get("name","")),"message":str(row.get("message",""))})
            with _BULK_LIVE_LOCK:
                _BULK_LIVE_STATUS.update(completed=processed,applied=accepted,failed=rejected,pending=len(flags)-processed,failureSamples=failed_samples[:])
            if done != len(batch) or result.get("interrupted") or result.get("outcome")=="unverified":
                outcome="interrupted"
                message=str(result.get("warning") or result.get("error") or "Native injection incomplete")
                break
            if first == 0 and ok == 0:
                outcome,message="unsupported","First 32 flags had no confirmed writes; stopped expensive scans"
                break
            if _BULK_LIVE_CANCEL.wait(.5):
                outcome,message="cancelled","Stopped before next batch"
                break
    except Exception as e:
        outcome,message="interrupted","Backend error: "+str(e)
    finally:
        with _BULK_LIVE_LOCK:
            _BULK_LIVE_STATUS.update(active=False,completed=processed,applied=accepted,failed=rejected,pending=len(flags)-processed,outcome=outcome,message=message)

def start_live_bulk(flags, source):
    if source!="manual":
        return {"ok":False,"error":"Live bulk requires an explicit manual request"}
    if not isinstance(flags,dict) or not (BULK_THRESHOLD<len(flags)<=MAX_FLAGS):
        return {"ok":False,"error":"Invalid bulk flag count"}
    if find_enhanced_injector() is None:
        return {"ok":False,"error":"Enhanced executable missing"}
    pid=find_pid(TARGET)
    if pid is None:
        return {"ok":False,"error":"Roblox must be running"}
    with _BULK_LIVE_LOCK:
        if _BULK_LIVE_STATUS["active"] or _ENHANCED_APPLY_LOCK.locked():
            return {"ok":False,"error":"Another live injection is running"}
        _BULK_LIVE_CANCEL.clear()
        _BULK_LIVE_STATUS.update(active=True,total=len(flags),completed=0,applied=0,failed=0,pending=len(flags),outcome="running",message="",failureSamples=[])
    threading.Thread(target=_live_bulk_worker,args=(flags,source,pid),daemon=True).start()
    return {"ok":True,"outcome":"started","total":len(flags),"liveInjection":True}


class Runtime:
''')
put("backend/server.py",
    '        if parsed.path == "/injection/status":\n',
    '        if parsed.path == "/bulk-live/status":\n            self._json(200, live_bulk_status())\n            return\n        if parsed.path == "/injection/status":\n')
put("backend/server.py",
    '        if self.path == "/bulk/preview":\n',
    '''        if self.path in ("/bulk-live/start", "/bulk-live/cancel"):
            if self.headers.get("Origin","") not in {"","tauri://localhost","http://tauri.localhost","https://tauri.localhost",f"http://{HOST}:{PORT}",f"http://localhost:{PORT}"}:
                self._json(403,{"ok":False,"error":"Request not from ZFLAG"})
                return
            if self.path == "/bulk-live/cancel":
                result=cancel_live_bulk()
            elif not isinstance(payload,dict) or payload.get("confirmed") is not True:
                result={"ok":False,"error":"Confirmation required"}
            else:
                result=start_live_bulk(payload.get("flags"),str(payload.get("source","")))
            self._json((202 if result.get("ok") else 409),result)
            return
        if self.path == "/bulk/preview":
''')
put("backend/server.py",
    '        if self.path == "/apply":\n',
    '''        if self.path == "/apply":
            if live_bulk_status()["active"]:
                self._json(409,{"ok":False,"error":"Stop the live bulk job before applying another preset"})
                return
''')
put("src/App.tsx",
    '  const bulkSafeModeActive = flagCount > 128',
    '''  const bulkSafeModeActive = flagCount > 128
  const [liveBulkActive, setLiveBulkActive] = useState(false)
  const [liveBulkProgress, setLiveBulkProgress] = useState({completed:0,total:0,applied:0,failed:0})
''')
put("src/App.tsx",
    '  async function applyFlags(source = "manual", flagsOverride?: Record<string, unknown>, labelOverride?: string) {',
    '''  async function injectLiveBulk() {
    if (!parsed.ok || flagCount <= 128 || liveBulkActive || busy) return
    if (!status.enhancedAvailable) {
      showToast("Enhanced engine unavailable", "Reinstall a build with the Enhanced injector.", "warning")
      return
    }
    if (!window.confirm("Inject " + flagCount.toLocaleString() + " FastFlags into running Roblox?\\\\n\\\\nEXPERIMENTAL: even small batches or individual flags may crash Roblox. Progress only means native setters returned. You can stop between batches.\\\\n\\\\nCancel to use Stage safe config.")) return
    setBusy(true)
    try {
      const response = await fetch(settings.apiUrl + "/bulk-live/start", {
        method:"POST", headers:{"Content-Type":"application/json"},
        body:JSON.stringify({flags:parsed.value,source:"manual",confirmed:true}),
        signal:AbortSignal.timeout(20000)
      })
      const result=await response.json()
      if (!response.ok || !result.ok) throw new Error(result.error || "Could not start live injection")
      setLiveBulkProgress({completed:0,total:flagCount,applied:0,failed:0})
      setLiveBulkActive(true)
      showToast("Live injection started", "Paced Enhanced batches are running. Stop is available.", "info")
    } catch (error) {
      showToast("Injection not started",error instanceof Error ? error.message : String(error),"error")
    } finally {
      setBusy(false)
    }
  }
  async function stopLiveBulk() {
    try {
      const response=await fetch(settings.apiUrl+"/bulk-live/cancel",{
        method:"POST",headers:{"Content-Type":"application/json"},body:"{}",signal:AbortSignal.timeout(5000)
      })
      const result=await response.json()
      showToast(response.ok ? "Stopping injection" : "Stop not confirmed",String(result.message || result.error || ""),"warning")
    } catch {
      showToast("Stop request unavailable","Backend did not respond","warning")
    }
  }
  useEffect(() => {
    if (!liveBulkActive) return
    let cancelled=false
    const poll=async () => {
      try {
        const response=await fetch(settings.apiUrl+"/bulk-live/status",{cache:"no-store",signal:AbortSignal.timeout(3500)})
        if (!response.ok) return
        const state=await response.json()
        if (cancelled || !Number(state.total)) return
        setLiveBulkProgress({completed:Number(state.completed)||0,total:Number(state.total)||0,applied:Number(state.applied)||0,failed:Number(state.failed)||0})
        if (!state.active) {
          setLiveBulkActive(false)
          showToast(state.outcome==="completed"?"Injection finished":"Injection stopped",
            String(state.applied||0)+" native writes, "+String(state.failed||0)+" rejected, "+String(state.pending||0)+" unattempted. "+String(state.message||""),
            state.outcome==="completed"?"success":"warning")
        }
      } catch {/* backend may be temporarily busy */}
    }
    void poll()
    const timer=window.setInterval(()=>void poll(),1500)
    return ()=>{cancelled=true;window.clearInterval(timer)}
  },[liveBulkActive,settings.apiUrl])

  async function applyFlags(source = "manual", flagsOverride?: Record<string, unknown>, labelOverride?: string) {
''')
# Only the toolbar changes; AutoApply and agent requests remain safe-staging.
p=root/"src/App.tsx"
s=p.read_text(encoding="utf-8")
start=s.index('            <span className="inject-engine-label" title="Runtime engine · change in Settings → General">')
end=s.index('          </div>\n        </div>\n        {bulkSafeModeActive',start)
s=s[:start]+'''            {liveBulkActive && <span className="zflag-inject-progress">{liveBulkProgress.completed.toLocaleString()} / {liveBulkProgress.total.toLocaleString()} · {liveBulkProgress.applied.toLocaleString()} writes · {liveBulkProgress.failed.toLocaleString()} failed</span>}
            <span className="inject-engine-label" title="Runtime engine">{bulkSafeModeActive?"ENHANCED BULK":settings.injectionEngine==="enhanced"?"ENHANCED":"OFFSETS"}</span>
            {bulkSafeModeActive && <button type="button" disabled={busy || liveBulkActive || !parsed.ok} title="Stage allowlisted flags for next launch" onClick={()=>void applyFlags("manual")}><FileJson className="size-3.5"/> Stage safe config</button>}
            {liveBulkActive ? <Button className="zflag-inject-button zflag-control-primary" size="sm" onClick={()=>void stopLiveBulk()}><Square className="size-3.5"/> Stop injection</Button> : <Button className="zflag-inject-button zflag-control-primary" size="sm" disabled={busy || !parsed.ok || (bulkSafeModeActive ? !status.enhancedAvailable : settings.injectionEngine==="enhanced" ? !status.enhancedAvailable : !status.connected || !status.ready)} onClick={()=>bulkSafeModeActive?void injectLiveBulk():void applyFlags("manual")}><Syringe className="size-3.5"/> Inject</Button>}
'''+s[end:]
s=s.replace('Safe bulk mode · {flagCount.toLocaleString()} flags loaded','Large preset · {flagCount.toLocaleString()} flags loaded')
s=s.replace('ZFLAG will only stage Roblox-approved flags for the next launch. Unknown flags stay in your editor; no live memory writes or in-game freezes from mass injection.','Inject sends paced Enhanced batches to running Roblox; even one flag may crash the game. Stage safe config is the alternative for next launch.')
p.write_text(s,encoding="utf-8")
for rel in ("package.json","src-tauri/tauri.conf.json","scripts/smoke-test-installed-app.ps1","tests/test_release_integrity.py","tests/test_large_json_safety_248.py"):
    p=root/rel
    s=p.read_text(encoding="utf-8")
    if rel != "scripts/smoke-test-installed-app.ps1":
        assert "2.0.49" in s, str(p)
    p.write_text(s.replace("2.0.49","2.0.50"),encoding="utf-8")
assert 'Stage safe config' in (root/"src/App.tsx").read_text(encoding="utf-8")
print("Patched ZFLAG 2.0.50 source with live bulk injection and opt-in UI")
