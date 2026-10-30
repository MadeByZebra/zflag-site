"""ZFLAG 2.0.64: limit stalled bulk scans and show accurate first-batch elapsed time.
The existing engine and per-flag result verification remain unchanged.
"""
from pathlib import Path
import json
import re
import sys

root = Path(sys.argv[1])
path = root / "backend/server.py"
code = path.read_text(encoding="utf-8")

def change(before, after):
    global code
    count = code.count(before)
    if count != 1:
        raise RuntimeError(f"Expected one matching location, found {count}: {before[:75]}")
    code = code.replace(before, after, 1)

# On bulk runs, supervise the exact native helper created by ZFLAG. Stopping
# must not kill Roblox and must never reuse an old process handle.
helper = '''
def _zflag_run_cancellable(command, timeout):
    child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    began = time.monotonic()
    try:
        while True:
            if _BULK_LIVE_CANCEL.is_set():
                raise subprocess.TimeoutExpired(command, timeout)
            if time.monotonic() - began >= timeout:
                raise subprocess.TimeoutExpired(command, timeout)
            try:
                stdout, stderr = child.communicate(timeout=0.35)
                return subprocess.CompletedProcess(command, child.returncode, stdout, stderr)
            except subprocess.TimeoutExpired:
                continue
    finally:
        if child.poll() is None:
            child.kill()
            try:
                child.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                pass


'''
change('def apply_enhanced(', helper+'def apply_enhanced(')
change('''        result = subprocess.run(
            [str(binary), "--zflag-headless", path],
            capture_output=True, text=True, timeout=native_timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=False,
        )''',
       '''        command = [str(binary), "--zflag-headless", path]
        if source == "live-bulk":
            result = _zflag_run_cancellable(command, native_timeout)
        else:
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=native_timeout,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=False,
            )''')

change('native_timeout = min(600, max(120, len(flags) * 0.25))',
       'native_timeout = 35 if source == "live-bulk" else min(600, max(120, len(flags) * 0.25))')
change('result=apply_enhanced(batch,source)',
       'result=apply_enhanced(batch,"live-bulk")')
change('''            result=apply_enhanced(batch,"live-bulk")''',
       '''            with _BULK_LIVE_LOCK:
                _BULK_LIVE_STATUS["nativeBatchStarted"] = time.monotonic()
            result=apply_enhanced(batch,"live-bulk")''')
change('''            if done != len(batch) or result.get("interrupted") or result.get("outcome")=="unverified":''',
       '''            if _BULK_LIVE_CANCEL.is_set():
                outcome,message="cancelled","Cancelled active native helper; remaining flags unconfirmed"
                break
            if done != len(batch) or result.get("interrupted") or result.get("outcome")=="unverified":''')

change('''    return {"ok":True,"message":"Stopping after the current native batch"}''',
       '''    return {"ok":True,"message":"Stop requested. The current native batch has a 35-second maximum."}''')
change('''    snapshot["recentRows"] = recent[-_BULK_LIVE_OUTPUT_LIMIT:]
    return snapshot


def cancel_live_bulk():''',
       '''    started = snapshot.get("nativeBatchStarted")
    if snapshot.get("active") and isinstance(started, (float, int)):
        elapsed = max(0, int(time.monotonic() - started))
        snapshot["nativeElapsedSeconds"] = elapsed
        if _BULK_LIVE_CANCEL.is_set():
            snapshot["phase"] = "Stopping after current batch (35-second limit)"
        elif snapshot.get("completed", 0) == 0:
            snapshot["phase"] = f"Scanning first batch: {elapsed}s / 35s limit"
    snapshot["recentRows"] = recent[-_BULK_LIVE_OUTPUT_LIMIT:]
    return snapshot


def cancel_live_bulk():''')
# A fresh job must not inherit the prior run's elapsed-time indicator.
change('phase="Preparing first batch")',
       'phase="Preparing first batch",nativeBatchStarted=0)')

# The 35-second timeout uses the existing TimeoutExpired recovery path.
# Preserve its checkpoint-based confirmation of writes.
if "import time" not in code:
    code = code.replace("# Only explicit user-confirmed large live batches use this path.",
                        chr(10).join(("import time", "# Only explicit user-confirmed large live batches use this path.")), 1)
path.write_text(code, encoding="utf-8")
# Clear a stale Stop button if the local backend is no longer responding.
ui_path = root / "src/App.tsx"
ui = ui_path.read_text(encoding="utf-8")
before = "    if (!liveBulkActive) return\n    let cancelled=false\n    const poll=async () => {"
after = "    if (!liveBulkActive) return\n    let cancelled=false\n    let consecutiveErrors=0\n    const poll=async () => {"
assert ui.count(before)==1, "UI bulk poll anchor changed"
ui=ui.replace(before,after,1)
before='''        if (!response.ok) return
        const state=await response.json()'''
after='''        if (!response.ok) throw new Error("Local backend rejected progress request")
        const state=await response.json()
        consecutiveErrors=0'''
assert ui.count(before)==1, "UI bulk status HTTP anchor changed"
ui=ui.replace(before,after,1)
before='''      } catch {/* backend may be temporarily busy */}'''
after='''      } catch {
        consecutiveErrors++
        if (!cancelled && consecutiveErrors >= 3) {
          setLiveBulkActive(false)
          showToast("Injection status unavailable","ZFLAG backend stopped responding. No additional flags are confirmed. Restart ZFLAG before another attempt.","error")
        }
      }'''
assert ui.count(before)==1, "UI bulk request error anchor changed"
ui=ui.replace(before,after,1)
ui_path.write_text(ui,encoding="utf-8")

# The small-screen toolbar may wrap instead of layering over existing text.
css_path = root / "src/index.css"
css_path.write_text(css_path.read_text(encoding="utf-8")+'''
/* v2.0.64: status text and controls occupy separate flex items. */
.zflag-inject-progress {position:static !important; display:inline-block !important;
    flex:1 1 190px !important; max-width:100% !important; min-width:0 !important;
    white-space:normal !important; overflow-wrap:anywhere !important;
    line-height:1.4 !important;}
.inject-engine-label {position:static !important; flex:0 0 auto !important;
    max-width:120px !important; white-space:nowrap !important;}
.zflag-inject-button {position:static !important; flex:0 0 auto !important;}
''', encoding="utf-8")

for rel in ("package.json", "src-tauri/tauri.conf.json"):
    p = root / rel
    obj = json.loads(p.read_text(encoding="utf-8"))
    assert obj["version"] == "2.0.63"
    obj["version"] = "2.0.64"
    p.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
cargo = root / "src-tauri/Cargo.toml"
data = cargo.read_text(encoding="utf-8")
assert 'version = "2.0.63"' in data
data = data.replace('version = "2.0.63"', 'version = "2.0.64"', 1)
cargo.write_text(data, encoding="utf-8")
app = root / "src/App.tsx"
app.write_text(app.read_text(encoding="utf-8").replace("2.0.63", "2.0.64"), encoding="utf-8")
for folder in ("tests", "scripts"):
    for file in (root / folder).rglob("*"):
        if file.suffix.lower() not in (".py", ".ps1", ".ts", ".tsx", ".js", ".json"):
            continue
        try:
            old = file.read_text(encoding="utf-8")
        except UnicodeError:
            continue
        if "2.0.63" in old:
            file.write_text(old.replace("2.0.63", "2.0.64"), encoding="utf-8")
(root / "tests/test_v264_stall.py").write_text('''import ast, json, unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]
class TestStall(unittest.TestCase):
 def test_backend_compiles(self):
  ast.parse((R/"backend/server.py").read_text(encoding="utf-8"))
 def test_bounded_first_batch(self):
  s=(R/"backend/server.py").read_text(encoding="utf-8")
  self.assertIn('native_timeout = 35 if source == "live-bulk"',s)
  self.assertIn('result=apply_enhanced(batch,"live-bulk")',s)
  self.assertIn("Scanning first batch:",s)
 def test_version(self):
  self.assertEqual(json.loads((R/"package.json").read_text(encoding="utf-8"))["version"],"2.0.64")
''',encoding="utf-8")
print("v2.0.64 bounded first batch and visible elapsed status")
