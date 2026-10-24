"""Build an honest ZFLAG 2.0.58 compatibility/update-info release.

The developer's OMG release only includes a third-party compiled GUI EXE.
It is NOT a replacement for ZFLAG's JSON-headless engine. This patch does not
claim to include the developer's unpublished source or any speedup.
"""
from pathlib import Path
import re
import sys

root=Path(sys.argv[1])
app=root/"src/App.tsx"
source=app.read_text(encoding="utf-8")
anchor='              <div className="settings-section"><div className="settings-title">RUN MODE</div>'
assert source.count(anchor)==1,"Settings RUN MODE anchor changed"
section='''              <div className="settings-section">
                <div className="settings-title">UPSTREAM ENGINE COMPATIBILITY</div>
                <div className="connection-card">
                  <span className="status-dot" />
                  <div>
                    <strong>October 24 experimental injector: not integrated</strong>
                    <p>The third-party OMG release contains a compiled Windows GUI only. It has not supplied compatible ZFLAG headless JSON support or source code. Your Enhanced engine and verified per-flag result reporting remain unchanged. The reported 23× speedup is unverified in ZFLAG.</p>
                    <a href="https://github.com/davelovestars/oldinjector-version-working/releases/tag/omg" target="_blank" rel="noopener noreferrer">View third-party release ↗</a>
                  </div>
                </div>
              </div>
'''
source=source.replace(anchor,section+anchor,1)
app.write_text(source,encoding="utf-8")

# Only bump files that are maintained in the staged post-v2.0.57 tree.
must=("package.json","src-tauri/tauri.conf.json","scripts/smoke-test-installed-app.ps1",
      "tests/test_release_integrity.py")
optional=("tests/test_large_json_safety_248.py","tests/test_ui_pacing_253.py",
          "tests/test_tab_game_profiles_254.py","tests/test_streaming_256.py",
          "tests/test_native_output_257.py","tests/test_native_failure_diagnostics_255.py")
for rel in must+optional:
    file=root/rel
    if not file.is_file():
        if rel in must: raise RuntimeError("Required source file missing: "+rel)
        continue
    content=file.read_text(encoding="utf-8")
    if "2.0.57" not in content:
        if rel in must: raise RuntimeError("Expected v2.0.57 anchor absent: "+rel)
        continue
    file.write_text(content.replace("2.0.57","2.0.58"),encoding="utf-8")

cargo=root/"src-tauri/Cargo.toml"
content=cargo.read_text(encoding="utf-8")
content,count=re.subn(r'(?m)^version = "2\.0\.\d+"$','version = "2.0.58"',content,count=1)
if count!=1: raise RuntimeError("Cargo version anchor not found")
cargo.write_text(content,encoding="utf-8")
(root/"tests/test_upstream_status_258.py").write_text('''import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class UpstreamStatusTest(unittest.TestCase):
    def test_official_engine_not_silently_replaced(self):
        ui=(ROOT/'src/App.tsx').read_text(encoding='utf-8')
        self.assertIn('UPSTREAM ENGINE COMPATIBILITY',ui)
        self.assertIn('not integrated',ui)
        self.assertIn('reported 23× speedup is unverified',ui)
        self.assertIn('target="_blank" rel="noopener noreferrer"',ui)
        self.assertIn('verified per-flag result reporting remain unchanged',ui)
        self.assertIn('Enhanced · supplied native FVar engine',ui)
    def test_versions(self):
        for rel in ('package.json','src-tauri/tauri.conf.json'):
            self.assertEqual(json.loads((ROOT/rel).read_text(encoding='utf-8'))['version'],'2.0.58')
''',encoding="utf-8")
print("Applied ZFLAG 2.0.58: transparent third-party release status; native engine unchanged")
