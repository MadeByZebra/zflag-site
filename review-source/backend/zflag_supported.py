"""Roblox local FastFlag configuration, deliberately without process-memory edits."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import re
import tempfile
import time

# Roblox Developer Forum: Allowlist for local client configuration via Fast Flags.
# Allowlist may change independently of ZFLAG; update it when Roblox publishes revisions.
ALLOWED = frozenset("""
DFIntCSGLevelOfDetailSwitchingDistance DFIntCSGLevelOfDetailSwitchingDistanceL12
DFIntCSGLevelOfDetailSwitchingDistanceL23 DFIntCSGLevelOfDetailSwitchingDistanceL34
FFlagHandleAltEnterFullscreenManually DFFlagTextureQualityOverrideEnabled
DFIntTextureQualityOverride FIntDebugForceMSAASamples DFFlagDisableDPIScale
FFlagDebugGraphicsPreferD3D11 FFlagDebugSkyGray DFFlagDebugPauseVoxelizer
DFIntDebugFRMQualityLevelOverride FIntFRMMaxGrassDistance FIntFRMMinGrassDistance
FFlagDebugGraphicsPreferVulkan FFlagDebugGraphicsPreferOpenGL
FIntGrassMovementReducedMotionFactor
""".split())
REFERENCE = "https://devforum.roblox.com/t/allowlist-for-local-client-configuration-via-fast-flags/3966569/"

def normalize(name, value):
    if name not in ALLOWED:
        return False, None, "Not on Roblox's published local FastFlag allowlist"
    if name.startswith(("FFlag", "DFFlag")):
        if isinstance(value, bool):
            return True, "True" if value else "False", "Ready for local configuration"
        if isinstance(value, str) and value.strip().lower() in ("true", "false"):
            return True, value.strip().lower().capitalize(), "Ready for local configuration"
        return False, None, "Expected True or False"
    if isinstance(value, bool) or not re.fullmatch(r"-?\d{1,12}", str(value).strip()):
        return False, None, "Expected an integer"
    number=int(str(value).strip())
    if not (-2147483648<=number<=2147483647):
        return False, None, "Outside signed 32-bit integer range"
    return True, str(number), "Ready for local configuration"

def preflight(flags):
    if not isinstance(flags, dict) or not flags:
        return {"ok": False, "error": "Import a JSON object containing flags first"}
    entries=[]; supported=unsupported=invalid=0
    for name,value in flags.items():
        good,normalized,reason=normalize(name,value)
        if name not in ALLOWED: unsupported+=1; status="unsupported"
        elif good: supported+=1;status="supported"
        else: invalid+=1;status="invalid"
        entries.append({"name":name,"value":value,"normalized":normalized,
                        "type":"Bool" if name.startswith(("FFlag","DFFlag")) else "Int",
                        "supported":name in ALLOWED,"valid":good,"status":status,
                        "message":reason,"offset":None})
    return {"ok": True,"total":len(entries),"supported":supported,
            "unsupported":unsupported,"invalid":invalid,"entries":entries,
            "source":REFERENCE,"clientVersion":None}

def _running_exe_path(pid):
    if not pid or os.name!="nt": return None
    k=ctypes.WinDLL("kernel32",use_last_error=True)
    k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    k.OpenProcess.restype=wintypes.HANDLE
    k.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
    k.QueryFullProcessImageNameW.restype=wintypes.BOOL
    k.CloseHandle.argtypes=[wintypes.HANDLE]
    k.CloseHandle.restype=wintypes.BOOL
    h=k.OpenProcess(0x1000,False,int(pid))
    if not h: return None
    try:
        size=wintypes.DWORD(32768);buf=ctypes.create_unicode_buffer(32768)
        if k.QueryFullProcessImageNameW(h,0,buf,ctypes.byref(size)):
            p=Path(buf.value)
            if p.name.lower()=="robloxplayerbeta.exe" and p.is_file():return p
    finally:k.CloseHandle(h)
    return None

def target_install(pid=None):
    running=_running_exe_path(pid)
    if running:return running.parent
    local=os.environ.get("LOCALAPPDATA")
    if not local:return None
    versions=Path(local)/"Roblox"/"Versions"
    if not versions.is_dir():return None
    matches=list(versions.glob("version-*/RobloxPlayerBeta.exe"))
    if not matches:return None
    # Fallback to latest locally installed Windows Player executable.
    return max(matches,key=lambda p:p.stat().st_mtime).parent

def target_json(pid=None):
    install=target_install(pid)
    return install/"ClientSettings"/"ClientAppSettings.json" if install else None

def atomic_save(path, content):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=".zflag-",suffix=".tmp",dir=str(path.parent))
    try:
        with os.fdopen(fd,"wb") as out:
            out.write(content);out.flush();os.fsync(out.fileno())
        os.replace(tmp,str(path))
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def save_eligible(flags,pid=None):
    checked=preflight(flags)
    if not checked.get("ok"):return {"ok":False,"error":checked["error"]}
    target=target_json(pid)
    if target is None:return {"ok":False,"error":"Roblox Player installation not found in LocalAppData\\Roblox\\Versions"}
    eligible={e["name"]:e["normalized"] for e in checked["entries"] if e["valid"]}
    if not eligible:return {"ok":False,"error":"No locally configurable flags in this preset. Roblox ignores the others.","applied":0}
    old=target.read_bytes() if target.exists() else None
    data=(json.dumps(eligible,indent=2,ensure_ascii=False)+"\n").encode("utf-8")
    backup_dir=Path(os.environ.get("LOCALAPPDATA",str(target.parent)))/"ZFLAG"/"Backups"
    backup_dir.mkdir(parents=True,exist_ok=True)
    backup=backup_dir/(f"ClientAppSettings-{int(time.time()*1000)}.json.bak")
    if old is not None:atomic_save(backup,old)
    atomic_save(target,data)
    rows=[{"name":e["name"],"ok":bool(e["valid"]),"value":e["value"],
           "message":"Saved; restart Roblox for effect" if e["valid"] else e["message"],
           "status":"saved" if e["valid"] else e["status"]} for e in checked["entries"]]
    # Put skipped entries first so the UI can explain huge presets without
    # hiding their failure reasons behind hundreds of successful rows.
    skipped=[row for row in rows if not row["ok"]]
    saved=[row for row in rows if row["ok"]]
    visible=(skipped+saved)[:1200]
    return {"ok":True,"applied":len(eligible),"errors":checked["unsupported"]+checked["invalid"],
            "unsupported":checked["unsupported"],"invalid":checked["invalid"],
            "results":visible,"resultsTruncated":max(0,len(rows)-len(visible)),
            "restartRequired":True,"configPath":str(target),
            "rollback":{"target":str(target),"backup":str(backup) if old is not None else None},
            "message":f"Saved {len(eligible):,} allowed flags; skipped {checked['unsupported']:,} not allowlisted and {checked['invalid']:,} invalid. Restart Roblox."}


def reset_local_settings(pid=None):
    """Back up and remove local overrides. Never access or modify Roblox process memory.

    The original configuration is saved before deletion; it can be restored manually.
    Roblox must be closed and relaunched for this to take effect.
    """
    target = target_json(pid)
    if target is None:
        return {"ok": False, "error": "Roblox Player installation was not found"}
    if target.is_symlink() or target.parent.is_symlink():
        return {"ok": False, "error": "Refusing to follow a linked Roblox configuration path"}
    if not target.exists():
        return {"ok": True, "removed": False, "message": "No local overrides found. Roblox settings are already at defaults."}
    if not target.is_file():
        return {"ok": False, "error": "Roblox config path is not a regular file"}
    raw = target.read_bytes()
    backup_dir = Path(os.environ.get("LOCALAPPDATA", str(target.parent)))/"ZFLAG"/"Backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir/(f"Reset-ClientAppSettings-{time.time_ns()}.json.bak")
    atomic_save(backup, raw)
    target.unlink()
    return {"ok": True, "removed": True, "backup": str(backup),
            "message": "Custom Roblox local overrides were backed up and reset. Restart Roblox to load defaults."}

def restore(entry):
    path=Path(entry["target"])
    backup=entry.get("backup")
    if backup:
        raw=Path(backup).read_bytes();atomic_save(path,raw)
    elif path.exists():
        path.unlink()
    return True
