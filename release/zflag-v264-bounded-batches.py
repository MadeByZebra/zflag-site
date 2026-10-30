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

change('native_timeout = min(600, max(120, len(flags) * 0.25))',
       'native_timeout = 35 if source == "live-bulk" else min(600, max(120, len(flags) * 0.25))')
change('result=apply_enhanced(batch,source)',
       'result=apply_enhanced(batch,"live-bulk")')
change('''            result=apply_enhanced(batch,"live-bulk")''',
       '''            with _BULK_LIVE_LOCK:
                _BULK_LIVE_STATUS["nativeBatchStarted"] = time.monotonic()
            result=apply_enhanced(batch,"live-bulk")''')
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
# The 35-second timeout uses the existing TimeoutExpired recovery path.
# Preserve its checkpoint-based confirmation of writes.
path.write_text(code, encoding="utf-8")
for rel in ("package.json", "src-tauri/tauri.conf.json"):
    p = root / rel
    obj = json.loads(p.read_text(encoding="utf-8"))
    assert obj["version"] == "2.0.63"
    obj["version"] = "2.0.64"
    p.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
cargo = root / "src-tauri/Cargo.toml"
data = cargo.read_text(encoding="utf-8")
data, n = re.subn(r'(?m)^version = "2\\.0\\.63"$', 'version = "2.0.64"', data, count=1)
assert n == 1
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
