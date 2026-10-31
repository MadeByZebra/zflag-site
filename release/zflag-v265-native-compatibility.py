"""ZFLAG 2.0.65: accurate native compatibility reporting, fail-fast and single instance.
Does not alter memory offsets, native setters, client restrictions, or allowlists.
"""
from pathlib import Path
import json,sys
root=Path(sys.argv[1])
back=root/"backend/server.py"
s=back.read_text(encoding="utf-8")
def once(old,new,label):
 global s
 n=s.count(old)
 if n!=1: raise RuntimeError(f"{label}: expected one anchor, got {n}")
 s=s.replace(old,new,1)
helpers='''
_NATIVE_COMPAT_LOCK=threading.Lock()
_NATIVE_COMPAT={"pid":None,"state":"untested","reason":""}
def native_compatibility(pid):
    with _NATIVE_COMPAT_LOCK:
        if pid is not None and pid == _NATIVE_COMPAT["pid"]:
            return dict(_NATIVE_COMPAT)
    return {"pid":pid,"state":"untested",
            "reason":"Native FastFlag container has not been verified for this Roblox process."}

def note_native_container_failure(pid, rows):
    if not pid or not isinstance(rows,list) or not rows: return False
    if not all(isinstance(row,dict) and row.get("ok") is False and
               "fastflag container not found in memory" in str(row.get("message","")).lower()
               for row in rows): return False
    with _NATIVE_COMPAT_LOCK:
        _NATIVE_COMPAT.update(pid=pid,state="incompatible",
            reason="Enhanced engine cannot find the native FastFlag container in this Roblox process. "
                   "Use Stage safe config for supported startup flags.")
    return True

'''
once('def live_bulk_status():',helpers+'def live_bulk_status():','compatibility functions')
once('''        runtime.log(f"Enhanced engine: {applied} applied, {errors} failed''',
     '''        if isinstance(details,list):
            failure_reporter=globals().get("note_native_container_failure")
            pid_lookup=globals().get("find_pid")
            process_name=globals().get("TARGET")
            if callable(failure_reporter) and callable(pid_lookup) and isinstance(process_name,str):
                failure_reporter(pid_lookup(process_name),details)
        runtime.log(f"Enhanced engine: {applied} applied, {errors} failed''','native evidence recording')
once('''            if first == 0 and ok == 0:
                outcome,message="unsupported","First 32 flags had no confirmed writes; stopped expensive scans"
                break''',
     '''            if first == 0 and ok == 0:
                incompatible=note_native_container_failure(pid,rows)
                outcome="native_incompatible" if incompatible else "unsupported"
                message=("Native FastFlag container not found for this Roblox process. Use Stage safe config."
                         if incompatible else "First 32 flags had no confirmed writes; stopped expensive scans")
                break''','bulk first-batch result')
needle='''    pid=find_pid(TARGET)
    if pid is None:
        return {"ok":False,"error":"Roblox must be running"}'''
once(needle,needle+'''
    evidence=native_compatibility(pid)
    if evidence["state"]=="incompatible":
        return {"ok":False,"outcome":"native_incompatible","error":evidence["reason"],
                "completed":0,"applied":0,"failed":0,"pending":len(flags)}
''','prevent repeat scans')
once('''                "backendPid": os.getpid(),''',
     '''                "nativeCompatibility":native_compatibility(self.pid if self.process_detected else None),
                "backendPid": os.getpid(),''','native status')
old='''def main() -> None:
    print(f"FFlag Studio backend listening on http://{HOST}:{PORT}")
    print("Keep this window open while using the UI.")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()'''
new='''def main() -> None:
    mutex=None
    if sys.platform=="win32":
        create=ctypes.windll.kernel32.CreateMutexW
        create.restype=ctypes.c_void_p
        create.argtypes=[ctypes.c_void_p,ctypes.c_bool,ctypes.c_wchar_p]
        mutex=create(None,False,r"Local\ZFLAG_Backend_18765")
        if not mutex: raise OSError("Could not initialize backend instance lock")
        if ctypes.windll.kernel32.GetLastError()==183:
            print("ZFLAG backend already running; not starting a duplicate.")
            ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(mutex))
            return
    try:
        print(f"FFlag Studio backend listening on http://{HOST}:{PORT}")
        ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
    finally:
        if mutex: ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(mutex))'''
once(old,new,'single backend')
s=s.replace('"backendVersion": "6.4.52"','"backendVersion": "6.4.65"')
back.write_text(s,encoding="utf-8")
ui=root/"src/App.tsx"
u=ui.read_text(encoding="utf-8")
def ui_once(old,new,label):
 global u
 n=u.count(old)
 if n!=1: raise RuntimeError(f"UI {label}: expected one anchor, got {n}")
 u=u.replace(old,new,1)
ui_once('  enhancedAvailable?: boolean',
        '  nativeCompatibility?: { pid: number | null; state: string; reason?: string }\n  enhancedAvailable?: boolean',
        'status type')
ui_once('Roblox ready · PID','Roblox process · PID','status label')
ui_once('status.connected ? "Memory ready"','status.connected ? "Process accessible"','process label')
ui_once('''    if (!status.enhancedAvailable) {
      showToast("Enhanced engine unavailable",''',
        '''    if (status.nativeCompatibility?.state === "incompatible") {
      showToast("Native container unavailable",status.nativeCompatibility.reason || "Use Stage safe config.","warning")
      return
    }
    if (!status.enhancedAvailable) {
      showToast("Enhanced engine unavailable",''','block repeated attempt')
ui_once('''        <div className="engine-status-banner">''',
        '''        {status.nativeCompatibility?.state === "incompatible" && <div className="engine-status-banner" role="alert">
          <CircleAlert className="size-4" />
          <span><strong>Native injection unavailable for this Roblox process</strong><small>{status.nativeCompatibility.reason} The process-access indicator does not prove Enhanced native injection can work.</small></span>
        </div>}
        <div className="engine-status-banner">''','visible explanation')
ui.write_text(u.replace('2.0.64','2.0.65'),encoding="utf-8")
for rel in ("package.json","src-tauri/tauri.conf.json"):
 p=root/rel
 obj=json.loads(p.read_text(encoding="utf-8"))
 assert obj["version"]=="2.0.64"
 obj["version"]="2.0.65"
 p.write_text(json.dumps(obj,indent=2)+"\n",encoding="utf-8")
cargo=root/"src-tauri/Cargo.toml"
t=cargo.read_text(encoding="utf-8")
assert 'version = "2.0.64"' in t
cargo.write_text(t.replace('version = "2.0.64"','version = "2.0.65"',1),encoding="utf-8")
for folder in ("tests","scripts"):
 for p in (root/folder).rglob("*"):
  if p.suffix.lower() not in (".py",".ps1",".ts",".tsx",".js",".json"):continue
  try:t=p.read_text(encoding="utf-8")
  except UnicodeError:continue
  if "2.0.64" in t:p.write_text(t.replace("2.0.64","2.0.65"),encoding="utf-8")
(root/"tests/test_v265_native_compat.py").write_text('''import ast,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class NativeCompatibility(unittest.TestCase):
 def test_server_syntax(self):
  ast.parse((ROOT/"backend/server.py").read_text(encoding="utf-8"))
 def test_scoped_status_and_guard(self):
  s=(ROOT/"backend/server.py").read_text(encoding="utf-8")
  for m in ('note_native_container_failure(pid,rows)','native_compatibility(self.pid if self.process_detected else None)',
            'CreateMutexW','native_incompatible','_NATIVE_COMPAT_LOCK'):
   self.assertIn(m,s)
 def test_frontend(self):
  s=(ROOT/"src/App.tsx").read_text(encoding="utf-8")
  self.assertIn('status.nativeCompatibility?.state === "incompatible"',s)
  self.assertIn('Native injection unavailable for this Roblox process',s)
 def test_version(self):
  self.assertEqual(json.loads((ROOT/"package.json").read_text(encoding="utf-8"))["version"],"2.0.65")
''',encoding="utf-8")
print("v2.0.65: scoped native compatibility, truthful UI, single Windows backend.")
