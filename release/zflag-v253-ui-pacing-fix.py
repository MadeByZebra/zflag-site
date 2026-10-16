"""ZFLAG v2.0.53 polish for an explicit manual Inject action.
Run after v2.0.52 fixes. No memory protection bypass and no native algorithm changes.
"""
from pathlib import Path
import sys
root = Path(sys.argv[1])

def change(filename, old, new):
    path = root / filename
    s = path.read_text(encoding="utf-8")
    if s.count(old) != 1:
        raise RuntimeError(f"Patch anchor changed: {filename} / {old[:70]!r} / matches={s.count(old)}")
    path.write_text(s.replace(old, new, 1), encoding="utf-8")

file = root / "src/App.tsx"
src = file.read_text(encoding="utf-8")
fn = src.index("  async function injectLiveBulk() {")
start = src.find("    if (!window.confirm(", fn)
if start < 0:
    start = src.index("    const confirmed = window.confirm(", fn)
end = src.index("    setBusy(true)", start)
if end - start > 1250:
    raise RuntimeError("Unexpected manual confirmation block")
src = src[:start] + (
    "    // The user explicitly pressed Inject; the editor already displays the\n"
    "    // large-preset warning. Do not open an intrusive WebView confirmation.\n"
) + src[end:]
file.write_text(src, encoding="utf-8")

change("src/App.tsx",
    'className={cn("runtime-pill", status.connected && "connected")}',
    'className={cn("runtime-pill", status.connected ? "connected" : status.processDetected ? "detected" : "")}')
change("src/App.tsx",
    '<span className={cn("status-dot", status.connected && "online")} />',
    '<span className={cn("status-dot", status.connected ? "online" : status.processDetected ? "detected" : "")} />')
change("src/App.tsx",
    "  const [liveBulkActive, setLiveBulkActive] = useState(false)",
    "  const [liveBulkActive, setLiveBulkActive] = useState(false)\n"
    "  const [liveBulkStartedAt, setLiveBulkStartedAt] = useState(0)")
change("src/App.tsx", "      setLiveBulkActive(true)",
    "      setLiveBulkStartedAt(Date.now())\n      setLiveBulkActive(true)")

file = root / "src/App.tsx"
src = file.read_text(encoding="utf-8")
start = src.index('{liveBulkActive && <span className="zflag-inject-progress"')
end = src.index("</span>}", start) + len("</span>}")
src = src[:start] + """{liveBulkActive && <span className="zflag-inject-progress" role="status" title="Progress through small, separate native batches">
              {liveBulkProgress.completed.toLocaleString()} / {liveBulkProgress.total.toLocaleString()} · {liveBulkProgress.applied.toLocaleString()} writes · {liveBulkProgress.failed.toLocaleString()} failed
              {liveBulkProgress.completed >= 64 && liveBulkStartedAt > 0 && liveBulkProgress.total > liveBulkProgress.completed
                ? " · ETA ~" + Math.max(1, Math.ceil(((Date.now() - liveBulkStartedAt) / 1000) * (liveBulkProgress.total - liveBulkProgress.completed) / liveBulkProgress.completed)) + "s"
                : ""}
            </span>}""" + src[end:]
file.write_text(src, encoding="utf-8")

change("src/index.css",
    ".runtime-pill.connected { color: #b7e8d2 !important; }",
    """/* Amber means Roblox is detected, but the original memory engine is not ready. */
.runtime-pill.connected { color: #b7e8d2 !important; border-color: rgba(73,216,152,.22) !important; background: rgba(51,173,126,.055) !important; }
.runtime-pill.detected { color: #f2c781 !important; border-color: rgba(226,171,74,.25) !important; background: rgba(226,171,74,.075) !important; }
.runtime-pill .status-dot.detected { background: #f2b957 !important; box-shadow: 0 0 0 4px rgba(242,185,87,.10) !important; }
""")
change("backend/server.py",
    "if _BULK_LIVE_CANCEL.wait(0.5):",
    """# Keep a pause for Roblox recovery and Stop requests. Native scan time
            # already provides additional spacing, so reduce only the idle gap.
            if _BULK_LIVE_CANCEL.wait(0.25):""")

for rel in ("package.json", "src-tauri/tauri.conf.json",
            "scripts/smoke-test-installed-app.ps1", "tests/test_release_integrity.py",
            "tests/test_large_json_safety_248.py"):
    p = root / rel
    src = p.read_text(encoding="utf-8")
    if "2.0.52" in src:
        p.write_text(src.replace("2.0.52", "2.0.53"), encoding="utf-8")
    elif rel in ("package.json", "src-tauri/tauri.conf.json", "tests/test_release_integrity.py"):
        raise RuntimeError("Missing current version " + rel)

(root / "tests/test_ui_pacing_253.py").write_text("""import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class UI253(unittest.TestCase):
    def test_colored_detected_and_ready_states(self):
        ui=(ROOT/'src/App.tsx').read_text(encoding='utf-8')
        css=(ROOT/'src/index.css').read_text(encoding='utf-8')
        self.assertIn('status.processDetected ? "detected"',ui)
        self.assertIn('.runtime-pill.detected',css)
        self.assertIn('.status-dot.detected',css)
    def test_explicit_inject_without_browser_popup(self):
        ui=(ROOT/'src/App.tsx').read_text(encoding='utf-8')
        fn=ui[ui.index('  async function injectLiveBulk() {'):ui.index('  async function stopLiveBulk() {')]
        self.assertNotIn('window.confirm',fn)
        self.assertIn('confirmed: true',fn)
        self.assertIn('liveBulkStartedAt',fn)
    def test_native_batch_safety_preserved(self):
        server=(ROOT/'backend/server.py').read_text(encoding='utf-8')
        self.assertIn('BULK_LIVE_CHUNK = 32',server)
        self.assertIn('if find_pid(TARGET) != expected_pid:',server)
        self.assertIn('_BULK_LIVE_CANCEL.wait(0.25)',server)
    def test_semver(self):
        import json
        self.assertEqual(json.loads((ROOT/'package.json').read_text(encoding='utf-8'))['version'],'2.0.53')
""", encoding="utf-8")
print("Applied ZFLAG v2.0.53 UI and pacing patch")
