"""Parallel emergency French translation shard, using the same source extraction as the primary workflow."""
import argparse,importlib.util,json,pathlib,concurrent.futures,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("zflag_generator",ROOT/"scripts/generate-full-translations.py")
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
parser=argparse.ArgumentParser();parser.add_argument("--shard",type=int,required=True);parser.add_argument("--count",type=int,default=6);parser.add_argument("--workers",type=int,default=12)
a=parser.parse_args()
words,_=mod.collect()
subset=[w for index,w in enumerate(words) if index%a.count==a.shard]
print("FRENCH_SHARD_START",a.shard,len(subset),flush=True)
start=time.monotonic()
with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
 data=dict(pool.map(mod.translate_entry,[(word,"fr") for word in subset]))
p=ROOT/f"i18n/fr-shard-{a.shard}.json"
p.parent.mkdir(exist_ok=True)
p.write_text(json.dumps(data,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf8")
print("FRENCH_SHARD_DONE",a.shard,len(data),round(time.monotonic()-start,1),flush=True)
