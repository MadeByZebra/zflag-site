"""ZFLAG 2.0.61 — audit-clean library catalog.
Run AFTER v2.0.60 type validation and navigation patch.
81 metadata notes should be descriptions, not editable flags.
9 malformed source names are retained in an excluded-record reference.
"""
from pathlib import Path
import json,re,sys
ROOT=Path(sys.argv[1])
path=ROOT/'src/data/flag-library.json'
catalog=json.loads(path.read_text(encoding='utf-8'))
assert len(catalog)==15965,f"Unexpected base archive size {len(catalog)}"
note_re=re.compile(r'^_(?:comment|note|description)$|^_?[A-Za-z0-9_]+_(?:note|comment|description)$',re.I)
name_re=re.compile(r'^[A-Za-z][A-Za-z0-9_]+$')
valid=[];notes={};malformed=[]
for entry in catalog:
 name=entry['name']
 if note_re.fullmatch(name):
  base=re.sub(r'_(?:note|comment|description)$','',name.lstrip('_'),flags=re.I)
  notes[base]=entry.get('value','')
  continue
 if not name_re.fullmatch(name):
  malformed.append(entry)
  continue
 valid.append(entry)
assert len(valid)==15875,(len(valid),len(notes),len(malformed))
assert len(notes)==81 and len(malformed)==9,(len(notes),len(malformed))
for entry in valid:
 if entry['name'] in notes:
  note=str(notes[entry['name']]).strip()
  entry['description']+=" ARCHIVED CAUTION: "+note+" (unverified historical note)"
path.write_text(json.dumps(valid,ensure_ascii=False,separators=(',',':'))+"\n",encoding='utf-8')
ref=ROOT/'src/data/flag-library-archive-metadata.json'
ref.write_text(json.dumps({"explanation":"Archival notes and malformed names are source records, not actual editable FastFlags. The source JSON archives are preserved separately.","notes":notes,"malformed":malformed},ensure_ascii=False,indent=2)+"\n",encoding='utf-8')
lib=ROOT/'src/FlagLibrary.tsx'
s=lib.read_text(encoding='utf-8')
assert '15,965 imported flag names' in s
s=s.replace('15,965 imported flag names','15,875 valid-format flag identifiers',1)
s=s.replace('Search every recovered flag, examine archived values and browse curated premades.','Search valid-format archived flag identifiers, examine their historical values and browse curated premades.').replace('This library is an archive, not a bypass or claim that every flag works.','81 archive notes and 9 malformed source names were excluded from selectable flags. This library is not a claim that every archived flag works.')
lib.write_text(s,encoding='utf-8')
for test in (ROOT/'tests').rglob('*.py'):
 source=test.read_text(encoding='utf-8')
 if '15965' in source or '15,965' in source:
  test.write_text(source.replace('15965','15875').replace('15,965','15,875'),encoding='utf-8')
# One new invariant prevents accidentally converting metadata back into flags.
test=ROOT/'tests/test_v261_archive_integrity.py'
test.write_text('''from pathlib import Path
import json,re,unittest
ROOT=Path(__file__).resolve().parents[1]
class MetadataIntegrity(unittest.TestCase):
 def test_catalog_contains_only_valid_flag_names(self):
  flags=json.loads((ROOT/'src/data/flag-library.json').read_text(encoding='utf-8'))
  self.assertEqual(len(flags),15875)
  self.assertTrue(all(re.fullmatch(r'[A-Za-z][A-Za-z0-9_]+',f["name"]) for f in flags))
  self.assertFalse(any(f["name"].endswith("_note") or f["name"]=="_comment" for f in flags))
  self.assertTrue(any("ARCHIVED CAUTION" in f.get("description","") for f in flags))
 def test_metadata_retained(self):
  data=json.loads((ROOT/'src/data/flag-library-archive-metadata.json').read_text(encoding='utf-8'))
  self.assertEqual(len(data["notes"]),81)
  self.assertEqual(len(data["malformed"]),9)
  self.assertIn("DFFlagDisableFastLogTelemetry",data["notes"])
 def test_value_ui(self):
  ui=(ROOT/'src/FlagLibrary.tsx').read_text(encoding='utf-8')
  self.assertIn("ACTUAL VALUE",ui)
  self.assertIn("15,875 valid-format",ui)
''',encoding='utf-8')
for rel in ('package.json','src-tauri/tauri.conf.json'):
 p=ROOT/rel;data=json.loads(p.read_text(encoding='utf-8'))
 assert data.get("version")=="2.0.60",(rel,data.get("version"))
 data["version"]="2.0.61";p.write_text(json.dumps(data,indent=2)+"\n",encoding='utf-8')
cargo=ROOT/'src-tauri/Cargo.toml'
text=cargo.read_text(encoding='utf-8')
text,n=re.subn(r'(?m)^version = "2\.0\.60"$','version = "2.0.61"',text,count=1)
assert n==1,"Cargo version not patched"
cargo.write_text(text,encoding='utf-8')
app=ROOT/'src/App.tsx'
app.write_text(app.read_text(encoding='utf-8').replace('2.0.60','2.0.61'),encoding='utf-8')
for directory in (ROOT/'tests',ROOT/'scripts'):
 for p in directory.rglob('*'):
  if not p.is_file() or p.suffix.lower() not in ('.py','.ps1','.ts','.tsx','.js','.json'):continue
  try:source=p.read_text(encoding='utf-8')
  except UnicodeError:continue
  if '2.0.60' in source:p.write_text(source.replace('2.0.60','2.0.61'),encoding='utf-8')
print("ZFLAG 2.0.61: 15,875 valid-format entries; 81 source notes as description; 9 invalid identifiers preserved separately; typed values and centered nav retained.")
