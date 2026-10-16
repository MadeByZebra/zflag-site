"""ZFLAG v2.0.52: distinguish Roblox process discovery from attach/injection readiness.

Run after the already-verified 2.0.50 feature + 2.0.51 installer patches.
Does not attempt to bypass Roblox process protections or change native setters.
"""
from pathlib import Path
import sys

root=Path(sys.argv[1])

def edit(rel, old, new):
    path=root/rel
    content=path.read_text(encoding='utf-8')
    if old not in content:
        raise RuntimeError(f'Missing expected anchor in {rel}: {old[:100]!r}')
    path.write_text(content.replace(old,new,1),encoding='utf-8')

edit('backend/server.py', '''        self.pid: Optional[int] = None
        self.ready = False''', '''        self.pid: Optional[int] = None
        self.process_detected = False
        self.connection_issue: Optional[str] = "RobloxPlayerBeta.exe is not running"
        self.alternate_client: Optional[str] = None
        self.access_error: Optional[int] = None
        self.ready = False''')

begin='''    def acquire_process(self) -> bool:
        with self.lock:
            pid = find_pid(TARGET)
'''
end='''    def refresh_offsets(self) -> bool:
'''
source=(root/'backend/server.py').read_text(encoding='utf-8')
a=source.index(begin); b=source.index(end,a)
updated='''    def acquire_process(self) -> bool:
        """Keep process discovery independent of write-capable memory access.

        A game window can exist even when module enumeration or OpenProcess
        fails. An Enhanced injector might attach independently, so this status
        must never incorrectly say Roblox is offline when the PID is visible.
        """
        with self.lock:
            pid = find_pid(TARGET)
            self.process_detected = pid is not None
            self.alternate_client = None
            self.access_error = None
            if pid is None:
                for other in ("RobloxStudioBeta.exe", "Windows10Universal.exe", "RobloxPlayerLauncher.exe"):
                    if find_pid(other) is not None:
                        self.alternate_client = other
                        break
                self.connection_issue = (
                    f"Detected {self.alternate_client}, not the RobloxPlayerBeta.exe game process"
                    if self.alternate_client else "RobloxPlayerBeta.exe not found in the Windows process list"
                )
                self.pid = None
                self.base = 0
                if self.handle:
                    _k32.CloseHandle(self.handle)
                self.handle = 0
                return False
            if self.pid == pid and self.handle and self.base:
                self.connection_issue = None
                return True
            # An old PID/handle must never be reused for a new Roblox session.
            if self.handle:
                _k32.CloseHandle(self.handle)
            self.handle = 0
            self.base = 0
            self.pid = pid  # PID is known even when process memory is inaccessible.
            base = get_module_base(pid, TARGET)
            if not base:
                self.access_error = ctypes.get_last_error() or None
                self.connection_issue = (
                    f"Roblox PID {pid} detected, but its module could not be inspected"
                    + (f" (Windows error {self.access_error})" if self.access_error else "")
                )
                return False
            access = PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION | PROCESS_QUERY_INFORMATION
            handle = _k32.OpenProcess(access, False, pid)
            if not handle:
                self.access_error = ctypes.get_last_error() or None
                self.connection_issue = (
                    f"Roblox PID {pid} detected, but memory access was refused"
                    + (f" (Windows error {self.access_error})" if self.access_error else "")
                )
                return False
            self.base = int(base)
            self.handle = int(handle)
            self.connection_issue = None
            self.log(f"Roblox process acquired (PID {pid})", "success")
            return True

'''
source=source[:a]+updated+source[b:]
(root/'backend/server.py').write_text(source,encoding='utf-8')

edit('backend/server.py','''                "connected": connected,
                "enhancedAvailable":''','''                "connected": connected,
                "processDetected": self.process_detected,
                "connectionIssue": self.connection_issue,
                "alternateClient": self.alternate_client,
                "accessError": self.access_error,
                "enhancedAvailable":''')

# Confirm process existence independently of the native executable, and keep
# original native failure text visible when it explains why a write was denied.
edit('backend/server.py','''            return {"ok": False, "outcome": "unverified", "error": "Native injector exited abnormally (code %d)" % result.returncode, "applied": 0, "errors": 0, "pending": len(flags), "results": []}''','''            explanation = str(output.get("error") or "Native injector exited abnormally")
            if "Roblox is not running or process access was denied" in explanation and find_pid(TARGET) is not None:
                explanation = "Roblox is running, but the Enhanced engine cannot open its process. Check Windows permissions and Roblox client compatibility."
            return {"ok": False, "outcome": "native_rejected", "error": explanation,
                    "applied": 0, "errors": 0, "pending": len(flags), "results": []}''')

edit('backend/server.py', '''                "backendVersion": "6.3",''', '''                "backendVersion": "6.4.52",''')
# Empty status uses backend version for stale-backend diagnostics.
edit('backend/server.py', '''                "backendVersion": "6.3",''', '''                "backendVersion": "6.4.52",''')

edit('src/App.tsx', '''  connected: boolean
  enhancedAvailable?: boolean''', '''  connected: boolean
  processDetected?: boolean
  connectionIssue?: string | null
  alternateClient?: string | null
  accessError?: number | null
  enhancedAvailable?: boolean''')
edit('src/App.tsx', '''  connected: false,
  pid: null,''', '''  connected: false,
  processDetected: false,
  connectionIssue: null,
  alternateClient: null,
  pid: null,''')
edit('src/App.tsx', '''    value.connected ? 1 : 0,
    value.enhancedAvailable ? 1 : 0,''', '''    value.connected ? 1 : 0,
    value.processDetected ? 1 : 0,
    value.connectionIssue ?? "",
    value.alternateClient ?? "",
    value.accessError ?? "",
    value.enhancedAvailable ? 1 : 0,''')

edit('src/App.tsx', '''            {status.connected ? `PID ${status.pid}` : "Roblox offline"}''', '''            {!backendReachable ? "ZFLAG backend offline" : status.processDetected ? (status.connected ? `Roblox ready · PID ${status.pid}` : `Roblox detected · PID ${status.pid}`) : status.alternateClient ? "Different Roblox client" : "Roblox not found"}''')
edit('src/App.tsx','''          <Badge className={cn("runtime-pill", status.connected && "connected")}>''','''          <Badge title={status.connectionIssue ?? undefined} className={cn("runtime-pill", status.connected && "connected")}>''')
edit('src/App.tsx','''<span>Process</span><strong>{status.connected ? "Connected" : "Offline"}</strong><small>{status.pid ? `PID ${status.pid}` : "Launch Roblox to connect"}</small>''','''<span>Process</span><strong>{status.connected ? "Memory ready" : status.processDetected ? "Roblox detected" : "Not found"}</strong><small>{status.connectionIssue ?? (status.pid ? `PID ${status.pid}` : "Open a Roblox game")}</small>''')
edit('src/App.tsx','''<div><span>Roblox</span><strong>{status.connected ? `PID ${status.pid}` : "Offline"}</strong></div>''','''<div><span>Roblox process</span><strong>{status.processDetected ? `Detected · PID ${status.pid}` : status.alternateClient ?? "Not found"}</strong></div>
                  <div><span>Process memory</span><strong>{status.connected ? "Accessible" : status.connectionIssue ?? "Not available"}</strong></div>''')

edit('src/App.tsx', '''    if (!status.enhancedAvailable) {
      showToast("Enhanced engine unavailable",''', '''    if (!status.processDetected) {
      showToast("Roblox not detected", status.connectionIssue ?? "Start a Roblox game and refresh connection.", "warning")
      return
    }
    if (!status.enhancedAvailable) {
      showToast("Enhanced engine unavailable",''')
# Disable live injection in GUI if we have no visible target, but preserve the
# Enhanced engine's ability to run even when offset-engine memory access fails.
edit('src/App.tsx', '''(bulkSafeModeActive ? !status.enhancedAvailable : settings.injectionEngine==="enhanced" ? !status.enhancedAvailable : !status.connected || !status.ready)''', '''(bulkSafeModeActive ? (!status.processDetected || !status.enhancedAvailable) : settings.injectionEngine==="enhanced" ? (!status.processDetected || !status.enhancedAvailable) : !status.connected || !status.ready)''')
edit('src/App.tsx', '''        <div className="engine-status-banner">''', '''        {backendReachable && !!status.connectionIssue && <div className="engine-status-banner" role="status"><CircleAlert className="size-4"/><span><strong>{status.processDetected ? "Roblox is open, but memory access is limited" : "Roblox detection"}</strong><small>{status.connectionIssue}</small></span><button type="button" onClick={()=>void refreshStatus(settings.apiUrl,false)}>Retry detection</button></div>}
        <div className="engine-status-banner">''')
edit('src/App.tsx','''<p>The native engine uses the working C++ injector source you supplied. Choose Enhanced, then Save settings. Original mode and all existing UI features remain available. Preflight and rollback are specific to the offset-based engine.</p>''','''<p>The Enhanced engine uses its own Roblox attachment. "Roblox detected" only confirms Windows can see the game process, not that injection will succeed. {status.connectionIssue ? `Diagnostic: ${status.connectionIssue}. ` : ""}Choose Enhanced and Save settings. Preflight and rollback apply to the original engine.</p>''')
edit('src/App.tsx', '''Manage presets. Large files use safe bulk staging instead of live injection.''','''Manage presets, run Enhanced injection in batches, or stage startup configs.''')

# Confirm dialog uses real line breaks and hides previous-preset metrics.
app_file=root/'src/App.tsx'
app=app_file.read_text(encoding='utf-8')
start=app.index('    if (!window.confirm("Inject " + flagCount.toLocaleString()')
end=app.index('\n    setBusy(true)',start)
app=app[:start]+'''    if (!window.confirm(`Inject ${flagCount.toLocaleString()} FastFlags into Roblox?

EXPERIMENTAL: a flag can freeze or crash the game.

ZFLAG attempts small batches and reports native writes. OK starts the attempt; Cancel does nothing.

Use Stage safe config if you prefer startup settings instead.`)) return'''+app[end:]
app=app.replace('{lastApplyStats.total > 0 && <div className="apply-progress-row">','{lastApplyStats.total > 0 && lastApplyStats.total === flagCount && !liveBulkActive && <div className="apply-progress-row">',1)
app_file.write_text(app,encoding='utf-8')

# Versions in the release source after the v2.0.51 patch. Leave old download
# fixtures alone; the GitHub workflow updates public website after smoke test.
for rel in ("package.json", "src-tauri/tauri.conf.json", "scripts/smoke-test-installed-app.ps1", "tests/test_release_integrity.py", "tests/test_large_json_safety_248.py"):
    p=root/rel
    s=p.read_text(encoding="utf-8")
    if "2.0.51" in s:
        p.write_text(s.replace("2.0.51", "2.0.52"),encoding="utf-8")
    elif rel in ("package.json", "src-tauri/tauri.conf.json", "tests/test_release_integrity.py"):
        raise RuntimeError("Missing current version in " + rel)
# Keep install tests on the new semantic version where applicable.
p=root/"tests/test_connection_status_252.py"
p.write_text('''import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
class RobloxConnectionRegression(unittest.TestCase):
    def test_process_presence_and_memory_access_separated(self):
        server=(ROOT/'backend/server.py').read_text(encoding='utf-8')
        for value in ('"processDetected": self.process_detected', '"connectionIssue": self.connection_issue', 'self.pid = pid  # PID is known even when process memory is inaccessible.', '"outcome": "native_rejected"'):
            self.assertIn(value,server)
    def test_status_ui_never_labels_found_process_offline(self):
        ui=(ROOT/'src/App.tsx').read_text(encoding='utf-8')
        self.assertIn('Roblox detected · PID',ui)
        self.assertIn('status.processDetected',ui)
        self.assertIn('Retry detection',ui)
    def test_enhanced_and_original_have_different_gates(self):
        ui=(ROOT/'src/App.tsx').read_text(encoding='utf-8')
        self.assertIn('!status.connected || !status.ready',ui)
        self.assertIn('!status.processDetected || !status.enhancedAvailable',ui)
    def test_installer_shutdown_hook_retained(self):
        hook=(ROOT/'src-tauri/installer/zflag-shortcuts.nsh').read_text(encoding='utf-8')
        self.assertIn('!macro NSIS_HOOK_PREINSTALL',hook)
        self.assertIn('taskkill.exe',hook)

if __name__ == '__main__': unittest.main()
''',encoding='utf-8')
print('Applied ZFLAG 2.0.52 process-detection/status fix and injection error diagnostics')