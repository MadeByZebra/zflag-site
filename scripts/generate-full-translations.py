#!/usr/bin/env python3
"""Generate full ZFLAG website source-text dictionaries for offline browser localization."""
import re, json, argparse, html, pathlib, concurrent.futures, threading, time, random
from html.parser import HTMLParser
from urllib.parse import urlencode
from urllib.request import Request, urlopen
ROOT=pathlib.Path(__file__).resolve().parents[1]
PAGES=("index.html","docs/index.html","library/index.html")
SKIP={"style","script","svg","path","code","pre","kbd","textarea","noscript","math"}
TECH=re.compile(r"^(?:D?FFlag|D?FInt|D?FString|SFFlag|SInt|SString|FLog|DFLog)[a-zA-Z0-9_]+$|^\{[^}]+\}$|^[\d.,/\\+%\- ]+$",re.I)
API="https://translate.googleapis.com/translate_a/single"
class Extract(HTMLParser):
 def __init__(self):
  super().__init__(convert_charrefs=True);self.stack=[];self.words=[]
 def handle_starttag(self,tag,attrs):
  self.stack.append(tag)
  attrs=dict(attrs)
  if not any(t in SKIP for t in self.stack):
   for key in ("placeholder","aria-label","title","alt"):
    if attrs.get(key):self.words.append(attrs[key])
 def handle_startendtag(self,tag,attrs):
  if not any(t in SKIP for t in self.stack):
   for key,value in attrs:
    if key in ("placeholder","aria-label","title","alt") and value:self.words.append(value)
 def handle_endtag(self,tag):
  if tag in self.stack:
   idx=len(self.stack)-1-self.stack[::-1].index(tag)
   self.stack=self.stack[:idx]
 def handle_data(self,data):
  if not any(t in SKIP for t in self.stack):self.words.append(data)
def normalize(value):
 value=html.unescape(str(value)).replace("\u00a0"," ")
 return " ".join(value.split()).strip()
def worthy(value):
 if not value or len(value)>3200:return False
 if not re.search(r"[A-Za-z]",value):return False
 if TECH.fullmatch(value):return False
 if re.fullmatch(r"[\W\d_]+",value):return False
 if value.startswith(("https://","http://","./","../","#","data:","aria-","--","@","[","{")):return False
 if value in ("true","false","on","off","EN","JSON","FPS","FInt","FFlag","ZFLAG","roblox"):return False
 if re.search(r"^(?:rgb|rgba|hsl|url|calc|var|translate[XYZ]?|linear-gradient|drop-shadow)\(",value):return False
 if re.search(r"[{};=]{3,}",value):return False
 return True
def collect():
 terms=set()
 for path in PAGES:
  raw=(ROOT/path).read_text(encoding="utf8")
  extractor=Extract();extractor.feed(raw)
  for value in extractor.words:
   value=normalize(value)
   if worthy(value):terms.add(value)
  # Additional user-facing strings created when flags, presets, dialogs,
  # notifications and code sample viewers are rendered dynamically.
  patterns=(
   r'(?:textContent|innerText|placeholder|aria-label|title|desc|name|source|category)\s*[:=]\s*"((?:[^"\\]|\\.)*)"',
   r'(?:textContent|innerText|placeholder|title|desc|name|source|category)\s*[:=]\s*\'((?:[^\'\\]|\\.)*)\'',
   r'(?<![\w.])(?:confirm|alert|toast)\s*\(\s*"((?:[^"\\]|\\.)*)"',
   r'(?<![\w.])(?:confirm|alert|toast)\s*\(\s*\'((?:[^\'\\]|\\.)*)\'',
   r'>\s*([^<>]{5,800})\s*<',
  )
  for pattern in patterns:
   for match in re.finditer(pattern,raw):
    v=normalize(match.group(1).replace("\\'","'").replace('\\"','"'))
    if worthy(v) and not v.startswith((".","(",":","%","$","<")):terms.add(v)
 # Long archive notes (these are descriptions, not actual FastFlag values)
 for filename in ("library/imports/ZFLAG_ALL_FLAGS_6_NEW_UPLOADS_MERGED.json","library/imports/ALL_FFLAGS_EVERYTHING_COMBINED.json"):
  obj=json.loads((ROOT/filename).read_text(encoding="utf-8"))
  for k,v in obj.items():
   if re.search(r"_(?:note|comment|description)$",k,re.I) and isinstance(v,str):
    if worthy(normalize(v)):terms.add(normalize(v))
 # Dynamic library content: preserve the identifier and values as tokens.
 terms.update([
  "Name suggests “ZZZFLAGNAMEZZZ” controls ZZZPURPOSEZZZ. This interpretation is inferred; its real purpose, supported values and effect have not been independently documented.",
  "This interpretation is inferred; its real purpose, supported values and effect have not been independently documented.",
  "frame timing or scheduler behavior","graphics/rendering behavior",
  "visual materials, lighting or texture processing","network transport, communication or replication",
  "memory, cache or buffer management","simulation, collision or motion behavior",
  "interface or input behavior","audio, voice or spatial sound behavior",
  "diagnostics, reporting or telemetry","asset loading or content transfer",
  "an internal feature or experimental behavior",
  "Published allowlist","Advanced · not allowlisted","Archive / unverified",
  "Allowlisted names · no live test","Legacy · likely ignored","ACTUAL JSON VALUE",
  "Invalid archived value:","Unverified archived value.","+ Add to config","Copy flag",
  "Download","Remove","REFERENCE:","SOURCE:","Expected true or false",
  "Expected an integer","Integer exceeds safe precision","Expected a finite number",
  "Type unverified; confirm the JSON value before use.","ARCHIVED NOTE (unverified):",
  "No supported value range is verified.","Archive caution:","Added","to configuration",
  "No matching premade configurations.","No matching flags.","Loading…",
  "Showing first 150 of ZZZCOUNTZZZ entries. The exported JSON contains every entry.",
  "Clear your entire configuration draft?","No matching results",
  "Search flags, descriptions, values…","Search premade configs…","Search not needed here",
  "Copied to clipboard","Clipboard blocked — use Download JSON",
  "Copied","Select text above","Copy section link","Link copied",
  "This is a website preview only. Nothing is applied to Roblox.",
  "Historical archive names and values are shown verbatim.",
 ])
 # Filter punctuation labels and code expressions; include only real English text
 return sorted(x for x in terms if worthy(x)),len(terms)
def save_source():
 words,_=collect()
 path=ROOT/"i18n/en-source.json";path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(words,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
 print("SOURCE_EXTRACTED",len(words),"chars",sum(map(len,words)),flush=True)
 return words
_tls=threading.local()
def google(text,lang):
 req=Request(API+"?"+urlencode({"client":"gtx","sl":"en","tl":lang,"dt":"t","q":text}),headers={"User-Agent":"Mozilla/5.0 (compatible; ZFLAG-Locale-Pack/1.0)"})
 with urlopen(req,timeout=25) as res:payload=json.load(res)
 return "".join(seg[0] or "" for seg in payload[0])
def translate_entry(args):
 text,lang=args
 if text in ("ZFLAG","JSON"):return text,text
 for attempt in range(5):
  try:
   translated=normalize(google(text,lang))
   if translated:return text,translated
  except Exception as exc:
   if attempt==4:print("TRANSLATION_FAILED",lang,text[:70],str(exc)[:120],flush=True)
  time.sleep((attempt+1)*1.3 + random.random()*0.7)
 return text,text # unmapped failure detected by coverage job
def run():
 parser=argparse.ArgumentParser()
 parser.add_argument("--lang",required=True)
 parser.add_argument("--workers",type=int,default=7)
 args=parser.parse_args()
 words=save_source()
 if args.lang=="en":return
 lang=args.lang
 out=ROOT/f"i18n/{lang}.json"
 result={}
 print("TRANSLATE",lang,"items",len(words),flush=True)
 start=time.monotonic()
 # Subset of basic English tokens is intentionally left technical.
 with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
  for index,(original,translated) in enumerate(pool.map(translate_entry,[(item,lang) for item in words])):
   result[original]=translated
   if index%120==0:print("TRANSLATED_PROGRESS",lang,index,"/",len(words),round(time.monotonic()-start,1),flush=True)
 out.write_text(json.dumps(result,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf8")
 unchanged=sum(1 for a,b in result.items() if a==b)
 print("TRANSLATED_DONE",lang,len(result),"identical",unchanged,"seconds",round(time.monotonic()-start,1),"bytes",out.stat().st_size,flush=True)
if __name__=="__main__":run()
