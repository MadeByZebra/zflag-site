"""v2.0.55: preserve trustworthy per-flag failure details from the native engine.

No native memory scanning or writing code changes. Live process access is not
bypassed. Changes return-code classification, diagnostics, version and tests.
"""
from pathlib import Path
import sys
root = Path(sys.argv[1])
backend = root / 'backend/server.py'
s = backend.read_text(encoding='utf-8')
needle = '''        interrupted_with_evidence = result.returncode == 2 and output.get("interrupted") is True and isinstance(details, list) and len(details) > 0
        if result.returncode != 0 and not legacy_partial and not interrupted_with_evidence:'''
replacement = '''        interrupted_with_evidence = result.returncode == 2 and output.get("interrupted") is True and isinstance(details, list) and len(details) > 0
        # The native CLI returns exit code 1 when every flag fails. If it gave
        # complete, identity-validated failure rows, this is a definitive
        # per-flag failure result, not an unexplained process crash. Preserve
        # those rows so each JSON tab shows actual names and reasons.
        verified_all_failed = (
            result.returncode == 1 and applied == 0 and errors == len(flags)
            and isinstance(details, list) and len(details) == len(flags)
            and output.get("ok") is False
            and all(isinstance(row, dict) and row.get("ok") is False for row in details)
        )
        if result.returncode != 0 and not legacy_partial and not interrupted_with_evidence and not verified_all_failed:'''
if s.count(needle) != 1:
    raise RuntimeError(f'Native outcome anchor count: {s.count(needle)}')
s = s.replace(needle, replacement, 1)
# A legacy CLI can return exit 1 while validated rows prove mixed outcomes.
legacy = 'legacy_partial = result.returncode == 1 and applied > 0 and errors > 0 and output.get("ok") is False'
corrected = 'legacy_partial = result.returncode == 1 and applied > 0 and errors > 0 and isinstance(details, list) and len(details) == len(flags)'
if s.count(legacy) != 1:
    raise RuntimeError('Legacy partial-result anchor missing')
s = s.replace(legacy, corrected, 1)
needle2='''        output["outcome"] = "interrupted" if interrupted else "applied" if applied and not errors else "partial" if applied else "failed"
        if interrupted:'''
repl2='''        output["outcome"] = "interrupted" if interrupted else "applied" if applied and not errors else "partial" if applied else "failed"
        if verified_all_failed:
            output["error"] = "Native engine rejected every flag; inspect individual error reasons."
            output["warning"] = "No confirmed writes. This does not mean Roblox is offline."
        if interrupted:'''
if s.count(needle2)!=1: raise RuntimeError(f'Native status anchor count: {s.count(needle2)}')
s = s.replace(needle2, repl2, 1)
backend.write_text(s, encoding='utf-8')

for rel in ('package.json','src-tauri/tauri.conf.json','scripts/smoke-test-installed-app.ps1',
            'tests/test_release_integrity.py','tests/test_large_json_safety_248.py',
            'tests/test_live_ui_pacing_253.py'):
    path = root / rel
    data = path.read_text(encoding='utf-8')
    if '2.0.54' in data:
        path.write_text(data.replace('2.0.54','2.0.55'),encoding='utf-8')
    elif rel in ('package.json','src-tauri/tauri.conf.json','tests/test_release_integrity.py'):
        raise RuntimeError('Expected v2.0.54 reference missing: ' + rel)

(root / 'tests/test_native_failure_diagnostics_255.py').write_text('''"""Regression tests of actual apply_enhanced failure handling with synthetic CLI results."""
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / 'backend/server.py'


def emulate_native(returncode, rows, flags=None, reported=None):
    flags = flags or {"FFlagExampleA": True, "FIntExampleB": 10}
    ok_count = sum(row['ok'] is True for row in rows)
    fail_count = len(rows)-ok_count
    payload={"ok": ok_count>0,"applied":ok_count,"errors":fail_count,
             "pending":len(flags)-len(rows),"results":rows}
    if reported:
        payload.update(reported)
    source=SERVER.read_text(encoding='utf-8')
    tree=ast.parse(source)
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='apply_enhanced')
    fake_run=lambda *args,**kwargs: SimpleNamespace(returncode=returncode, stdout=json.dumps(payload))
    test_exe=ROOT / 'backend' / 'server.py'
    ns={"__name__":"test_backend",
        "MAX_FLAGS":50000,"BULK_THRESHOLD":128,
        "stage_player_config":lambda f:{"error":"wrong bulk path"},
        "find_enhanced_injector":lambda:test_exe,
        "_ENHANCED_APPLY_LOCK":threading.Lock(),
        "_INJECTION_STATUS_LOCK":threading.Lock(),
        "_INJECTION_STATUS":{},
        "tempfile":tempfile,"json":json,"os":os,"sys":sys,"Path":Path,
        "subprocess":SimpleNamespace(run=fake_run, CREATE_NO_WINDOW=0, TimeoutExpired=subprocess.TimeoutExpired),
        "runtime":SimpleNamespace(log=lambda *args:None),
        "find_pid":lambda *_:1234,"TARGET":"RobloxPlayerBeta.exe",
        "incomplete_native_result":lambda p,f,why:{"ok":False,"outcome":"unverified","applied":0,"errors":0,"pending":len(f),"results":[]},
    }
    exec(compile(ast.Module(body=[function],type_ignores=[]),str(SERVER),'exec'),ns)
    return ns['apply_enhanced'](flags)


class NativeResultRegression(unittest.TestCase):
    def setUp(self):
        self.rows=[{"name":"FFlagExampleA","ok":False,"message":"Flag not found or not registered"},
                   {"name":"FIntExampleB","ok":False,"message":"Flag is read-only and cannot be modified"}]
    def test_all_failed_have_real_per_flag_reasons(self):
        res=emulate_native(1,self.rows)
        self.assertEqual(res['outcome'],'failed')
        self.assertEqual(res['errors'],2)
        self.assertEqual(res['pending'],0)
        self.assertEqual(res['results'],self.rows)
        self.assertIn('rejected every flag',res['error'])
    def test_mixed_results_are_partial_not_total_failure(self):
        rows=[dict(self.rows[0],ok=True,message='Success'),self.rows[1]]
        res=emulate_native(1,rows)
        self.assertEqual(res['outcome'],'partial')
        self.assertEqual(res['applied'],1)
        self.assertEqual(res['errors'],1)
    def test_mismatched_identity_never_reported_successful(self):
        rows=[dict(self.rows[0],name='AnotherFlag',ok=True),self.rows[1]]
        res=emulate_native(0,rows)
        self.assertEqual(res['outcome'],'unverified')
        self.assertEqual(res['applied'],0)
    def test_nonzero_exit_without_results_stays_unverified(self):
        res=emulate_native(1,[],reported={"ok":False,"applied":0,"errors":0,"error":"Roblox is not running or process access was denied"})
        self.assertEqual(res['outcome'],'unverified')
        self.assertEqual(res['results'],[])

if __name__=='__main__':
    unittest.main()
''', encoding='utf-8')
print('v2.0.55 native failure classification patched; all native write paths unchanged')