"""
FFlag Studio local backend
-------------------------
Runs a localhost-only JSON API for the shadcn React frontend.
The process/offset/write behavior mirrors the original Tkinter script; the UI
has been moved to the frontend.

Start:  python server.py
API:    http://127.0.0.1:18765
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wintypes
import json
import mimetypes
import os
import re
import struct
import subprocess
import sys
import threading
import tempfile
import time
import urllib.request
import urllib.error
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional

from zflag_supported import ALLOWED, REFERENCE, preflight as local_preflight, save_eligible, restore, target_install

TARGET = "RobloxPlayerBeta.exe"
HOST = "127.0.0.1"
PORT = 18766

PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
PROCESS_QUERY_INFORMATION = 0x0400
TH32CS_SNAPPROCESS = 0x00000002
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010
PAGE_READWRITE = 0x04
PAGE_EXECUTE_READWRITE = 0x40
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

if sys.platform != "win32":
    raise SystemExit("This backend is Windows x64 only.")


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", ctypes.c_wchar * 260),
    ]


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("th32ModuleID", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("GlblcntUsage", wintypes.DWORD),
        ("ProccntUsage", wintypes.DWORD),
        ("modBaseAddr", ctypes.POINTER(wintypes.BYTE)),
        ("modBaseSize", wintypes.DWORD),
        ("hModule", wintypes.HMODULE),
        ("szModule", ctypes.c_wchar * 256),
        ("szExePath", ctypes.c_wchar * 260),
    ]


_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
_ntdll = ctypes.WinDLL("ntdll", use_last_error=True)

_k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
_k32.OpenProcess.restype = wintypes.HANDLE
_k32.CloseHandle.argtypes = [wintypes.HANDLE]
_k32.CloseHandle.restype = wintypes.BOOL
_k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
_k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
_k32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
_k32.Process32FirstW.restype = wintypes.BOOL
_k32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
_k32.Process32NextW.restype = wintypes.BOOL
_k32.Module32FirstW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
_k32.Module32FirstW.restype = wintypes.BOOL
_k32.Module32NextW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
_k32.Module32NextW.restype = wintypes.BOOL
_k32.WriteProcessMemory.argtypes = [
    wintypes.HANDLE,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]
_k32.WriteProcessMemory.restype = wintypes.BOOL
_k32.ReadProcessMemory.argtypes = [
    wintypes.HANDLE,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]
_k32.ReadProcessMemory.restype = wintypes.BOOL
_k32.VirtualProtectEx.argtypes = [
    wintypes.HANDLE,
    ctypes.c_void_p,
    ctypes.c_size_t,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
]
_k32.VirtualProtectEx.restype = wintypes.BOOL
_ntdll.NtWriteVirtualMemory.argtypes = [
    wintypes.HANDLE,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]
_ntdll.NtWriteVirtualMemory.restype = ctypes.c_long


def list_roblox_processes() -> list[dict[str, object]]:
    """Enumerate only process names/PIDs. Never request handles to game memory."""
    snap = _k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == INVALID_HANDLE_VALUE:
        return []
    found: list[dict[str, object]] = []
    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
    try:
        if _k32.Process32FirstW(snap, ctypes.byref(entry)):
            while True:
                name = str(entry.szExeFile)
                if "roblox" in name.lower():
                    found.append({"name": name, "pid": int(entry.th32ProcessID)})
                if not _k32.Process32NextW(snap, ctypes.byref(entry)):
                    break
    finally:
        _k32.CloseHandle(snap)
    return found[:24]


def find_pid(exe: str) -> Optional[int]:
    snap = _k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == INVALID_HANDLE_VALUE:
        return None
    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
    pid = None
    if _k32.Process32FirstW(snap, ctypes.byref(entry)):
        while True:
            if entry.szExeFile.lower() == exe.lower():
                pid = int(entry.th32ProcessID)
                break
            if not _k32.Process32NextW(snap, ctypes.byref(entry)):
                break
    _k32.CloseHandle(snap)
    return pid


def get_module_base(pid: int, mod: str) -> Optional[int]:
    snap = _k32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    if snap == INVALID_HANDLE_VALUE:
        return None
    entry = MODULEENTRY32W()
    entry.dwSize = ctypes.sizeof(MODULEENTRY32W)
    base = None
    if _k32.Module32FirstW(snap, ctypes.byref(entry)):
        while True:
            if entry.szModule.lower() == mod.lower():
                base = ctypes.cast(entry.modBaseAddr, ctypes.c_void_p).value
                break
            if not _k32.Module32NextW(snap, ctypes.byref(entry)):
                break
    _k32.CloseHandle(snap)
    return base


def _read_raw(handle: int, addr: int, size: int) -> Optional[bytes]:
    if not handle or not addr or size <= 0 or size > 4096:
        return None
    buf = ctypes.create_string_buffer(size)
    read = ctypes.c_size_t(0)
    ok = _k32.ReadProcessMemory(
        handle, ctypes.c_void_p(addr), ctypes.byref(buf), size, ctypes.byref(read)
    )
    if ok and read.value == size:
        return bytes(buf.raw[:size])
    return None


def _write_raw(handle: int, addr: int, data: bytes) -> bool:
    size = len(data)
    buf = ctypes.create_string_buffer(data)
    written = ctypes.c_size_t(0)
    status = _ntdll.NtWriteVirtualMemory(
        handle,
        ctypes.c_void_p(addr),
        ctypes.byref(buf),
        ctypes.c_size_t(size),
        ctypes.byref(written),
    )
    if status == 0 and written.value == size:
        return True

    for prot in (PAGE_READWRITE, PAGE_EXECUTE_READWRITE):
        old = wintypes.DWORD(0)
        if not _k32.VirtualProtectEx(handle, ctypes.c_void_p(addr), size, prot, ctypes.byref(old)):
            continue
        written2 = ctypes.c_size_t(0)
        ok = _k32.WriteProcessMemory(
            handle, ctypes.c_void_p(addr), ctypes.byref(buf), size, ctypes.byref(written2)
        )
        restore = wintypes.DWORD(0)
        _k32.VirtualProtectEx(handle, ctypes.c_void_p(addr), size, old.value, ctypes.byref(restore))
        if ok and written2.value == size:
            return True
    return False


_URLS = [
    "https://dev.imtheo.lol/Offsets/FFlags.hpp",
    "https://offsets.imtheo.lol/FFlags.hpp",
    "https://raw.githubusercontent.com/NtReadVirtualMemory/Roblox-Offsets-Website/main/FFlags.hpp",
    "https://raw.githubusercontent.com/souloveryall/offsets.hpp/main/Offsets.hpp",
    "https://raw.githubusercontent.com/4anti/Roblox-Fastflag-Manager/main/data/FFlags.hpp",
]


def _fetch_one(url: str) -> Optional[bytes]:
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "FFlagStudio/5.0"})
        with urllib.request.urlopen(request, timeout=12) as response:
            body = response.read(6 * 1024 * 1024 + 1)
            if response.status == 200 and len(body) <= 6 * 1024 * 1024:
                return body
    except Exception:
        pass

    try:
        proc = subprocess.run(
            [
                "curl.exe",
                "-s",
                "-L",
                "--max-filesize",
                "6000000",
                "-A",
                "FFlagStudio/5.0",
                url,
            ],
            capture_output=True,
            timeout=17,
            creationflags=0x08000000,
        )
        if proc.returncode == 0 and proc.stdout:
            return proc.stdout
    except Exception:
        pass
    return None


_RX_INLINE = re.compile(rb"inline\s+constexpr\s+uintptr_t\s+(\w+)\s*=\s*(0x[0-9A-Fa-f]+)", re.M)
_RX_VER = re.compile(rb'ClientVersion\s*=\s*"([^"]+)"')
_RX_FLAGLIST = re.compile(rb"namespace\s+FFlagList\s*\{([^}]+)\}", re.S)
_RVA_MIN, _RVA_MAX = 0x40_0000, 0x1000_0000
_PREFIXES = sorted(
    [
        "DFFlag",
        "SFFlag",
        "GFFlag",
        "FFlag",
        "DFInt",
        "SFInt",
        "GFInt",
        "FInt",
        "DFLog",
        "FLog",
        "DFString",
        "SFString",
        "FString",
    ],
    key=len,
    reverse=True,
)


class Offsets:
    def __init__(self):
        self.version: Optional[str] = None
        self.pointer: Optional[int] = None
        self.to_flag: Optional[int] = None
        self.to_value: Optional[int] = None
        self.flags: dict[str, int] = {}


def parse_hpp(body: bytes) -> Offsets:
    out = Offsets()
    m = _RX_VER.search(body)
    if m:
        out.version = m.group(1).decode(errors="replace")
    m = _RX_FLAGLIST.search(body)
    if m:
        for nm, hx in _RX_INLINE.findall(m.group(1)):
            key, value = nm.decode(), int(hx, 16)
            if key == "Pointer":
                out.pointer = value
            elif key == "ToFlag":
                out.to_flag = value
            elif key == "ToValue":
                out.to_value = value
    for nm_b, hx_b in _RX_INLINE.findall(body):
        try:
            name = nm_b.decode("ascii")
            rva = int(hx_b, 16)
        except Exception:
            continue
        if rva < _RVA_MIN or rva > _RVA_MAX:
            continue
        if name in ("Pointer", "ToFlag", "ToValue", "ValueGetSet", "FlagToValue"):
            continue
        out.flags[name] = rva
    return out


def strip_prefix(name: str) -> str:
    for prefix in _PREFIXES:
        if name.startswith(prefix):
            return name[len(prefix) :]
    return name


def type_from_name(name: str) -> str:
    for prefix in ("FFlag", "DFFlag", "SFFlag", "GFFlag"):
        if name.startswith(prefix):
            return "bool"
    for prefix in ("FInt", "DFInt", "SFInt", "GFInt", "FLog", "DFLog"):
        if name.startswith(prefix):
            return "int"
    for prefix in ("FString", "DFString", "SFString"):
        if name.startswith(prefix):
            return "string"
    return "unknown"


SSO_CAP = 15


def flag_storage_size(ftype: str) -> int:
    if ftype == "bool":
        return 1
    if ftype == "int":
        return 4
    if ftype == "string":
        return 32
    return 0


def validate_flag_value(ftype: str, raw_value: object) -> tuple[bool, str, str]:
    if ftype == "bool":
        if isinstance(raw_value, bool):
            return True, "bool", "true" if raw_value else "false"
        value = str(raw_value).strip().lower()
        if value in {"true", "1", "yes", "on"}:
            return True, "bool", "true"
        if value in {"false", "0", "no", "off"}:
            return True, "bool", "false"
        return False, f"invalid bool: {raw_value!r}", value
    if ftype == "int":
        try:
            value = int(str(raw_value).strip())
        except Exception:
            return False, f"invalid int: {raw_value!r}", str(raw_value)
        if value < -2147483648 or value > 2147483647:
            return False, "int outside signed 32-bit range", str(value)
        return True, "int", str(value)
    if ftype == "string":
        value = str(raw_value)
        try:
            encoded = value.encode("utf-8")
        except Exception:
            return False, "invalid UTF-8 string", value
        if len(encoded) > SSO_CAP:
            return False, f"string too long ({len(encoded)}>{SSO_CAP})", value
        return True, "string", value
    return False, f"unknown type {ftype!r}", str(raw_value)


def read_flag_raw(handle: int, abs_addr: int, ftype: str) -> Optional[bytes]:
    size = flag_storage_size(ftype)
    return _read_raw(handle, abs_addr, size) if size else None


def write_flag(handle: int, abs_addr: int, ftype: str, value: str) -> tuple[bool, str]:
    if ftype == "bool":
        v = 1 if value.strip().lower() in ("true", "1", "yes", "on") else 0
        ok = _write_raw(handle, abs_addr, struct.pack("<B", v))
        return ok, "bool written" if ok else "write failed"
    if ftype == "int":
        try:
            v = max(-2147483648, min(2147483647, int(value)))
            ok = _write_raw(handle, abs_addr, struct.pack("<i", v))
            return ok, "int written" if ok else "write failed"
        except ValueError:
            return False, f"bad int: {value!r}"
    if ftype == "string":
        try:
            raw = value.encode("utf-8")
        except Exception:
            return False, "bad string"
        n = len(raw)
        if n > SSO_CAP:
            return False, f"string too long ({n}>{SSO_CAP})"
        obj = raw + b"\x00" * (16 - n) + struct.pack("<Q", n) + struct.pack("<Q", SSO_CAP)
        ok = _write_raw(handle, abs_addr, obj)
        return ok, "string written" if ok else "write failed"
    return False, f"unknown type {ftype!r}"


def _app_dist_root() -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(str(getattr(sys, "_MEIPASS")), "dist")
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dist"))


def _browser_bundle_check() -> dict[str, object]:
    root = os.path.abspath(_app_dist_root())
    index_path = os.path.join(root, "index.html")
    if not os.path.isfile(index_path):
        return {
            "ok": False,
            "browserUi": False,
            "browserUrl": f"http://{HOST}:{PORT}/app/",
            "error": "Browser UI index.html is not bundled",
            "missingAssets": [],
        }

    try:
        html = Path(index_path).read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return {
            "ok": False,
            "browserUi": False,
            "browserUrl": f"http://{HOST}:{PORT}/app/",
            "error": f"Could not read browser UI: {exc}",
            "missingAssets": [],
        }

    refs = re.findall(r"(?:src|href)=[\"']([^\"']+)[\"']", html, flags=re.IGNORECASE)
    missing: list[str] = []
    checked: list[str] = []

    for ref in refs:
        clean = ref.split("?", 1)[0].split("#", 1)[0].strip()
        if not clean or clean.startswith(("http://", "https://", "data:", "blob:", "#")):
            continue

        rel = clean.lstrip("./").lstrip("/")
        if not rel:
            continue

        candidate = os.path.abspath(os.path.join(root, rel.replace("/", os.sep)))
        if not candidate.startswith(root + os.sep):
            continue

        checked.append(rel)
        if not os.path.isfile(candidate):
            missing.append(rel)

    return {
        "ok": len(missing) == 0,
        "browserUi": len(missing) == 0,
        "browserUrl": f"http://{HOST}:{PORT}/app/",
        "indexBytes": os.path.getsize(index_path),
        "checkedAssets": checked,
        "missingAssets": missing,
        "error": None if not missing else "Browser UI is missing bundled assets: " + ", ".join(missing[:5]),
    }


def _open_url(url: str) -> bool:
    try:
        if sys.platform == "win32":
            os.startfile(url)  # type: ignore[attr-defined]
            return True
        return bool(webbrowser.open(url))
    except Exception:
        try:
            return bool(webbrowser.open(url))
        except Exception:
            return False


class Runtime:
    def __init__(self):
        self.lock = threading.RLock()
        self.offsets: Optional[Offsets] = None
        self.base = 0
        self.handle = 0
        self.pid: Optional[int] = None
        self.ready = False
        self.fetching = False
        self.started_at = time.time()
        self._last_probe_at = 0.0
        self._cached_pid = None
        self.native_lock = threading.Lock()
        self.offset_source: Optional[str] = None
        self.offset_source_host: Optional[str] = None
        self.offset_fetched_at: Optional[float] = None
        self.offset_bytes = 0
        self.offset_validation = "not loaded"
        self.rollback_stack: list[dict[str, object]] = []
        self.logs: list[dict[str, object]] = []
        self.log("Backend started", "info")

    def log(self, message: str, level: str = "info") -> None:
        with self.lock:
            self.logs.append(
                {
                    "id": int(time.time() * 1000),
                    "time": time.strftime("%H:%M:%S"),
                    "level": level,
                    "message": message,
                }
            )
            self.logs = self.logs[-250:]

    def acquire_process(self) -> bool:
        # A read-only, rate-limited Windows process-list lookup. Never open or
        # scan Roblox memory from the status/health polling path.
        now = time.monotonic()
        with self.lock:
            if now - self._last_probe_at < 8.0:
                return self._cached_pid is not None
            self._last_probe_at = now
        pid = find_pid(TARGET)
        with self.lock:
            old = self.pid
            self._cached_pid = pid
            self.pid = pid
            self.handle = 0
            self.base = 0
        if pid and pid != old:
            self.log(f"Roblox Player detected (PID {pid}); no game memory was accessed", "success")
        return pid is not None

    def native_probe(self) -> dict[str, object]:
        # Instant non-invasive process check, independent of the cached UI status.
        try:
            names = list_roblox_processes()
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            self.log(f"Windows process enumeration failed: {type(exc).__name__}: {exc}", "error")
            return {"ok": False, "found": False, "pid": None,
                    "error": f"Windows process detection failed safely ({type(exc).__name__}). No Roblox memory was accessed."}
        player = next((p for p in names if str(p["name"]).lower() == TARGET.lower()), None)
        pid = int(player["pid"]) if player else None
        with self.lock:
            self.pid = pid
            self._cached_pid = pid
            self._last_probe_at = time.monotonic()
        if pid is None:
            alternatives = ", ".join(f"{x['name']} (PID {x['pid']})" for x in names)
            detail = f"Detected these Roblox-related processes instead: {alternatives}. " if names else "No Roblox-related processes were visible. "
            return {"ok": False, "found": False, "pid": None, "processes": names,
                    "error": detail + "ZFLAG currently supports the RobloxPlayerBeta.exe Windows Player process only. Start a game in Roblox Player and retry. No game memory was opened, scanned or modified."}
        return {"ok": True, "found": True, "pid": pid, "processes": names,
                "message": f"Found Roblox Player PID {pid} using Windows process enumeration only. Game memory was not accessed."}

    def refresh_offsets(self) -> bool:
        # Local configuration does not use version-specific memory offsets.
        with self.lock:
            self.offsets=None
            self.ready=True
            self.fetching=False
            self.offset_source=REFERENCE
            self.offset_source_host="Roblox Developer Forum"
            self.offset_fetched_at=time.time()
            self.offset_bytes=0
            self.offset_validation=f"{len(ALLOWED)} published locally configurable flags"
        self.log(f"Loaded {len(ALLOWED)} officially allowed local settings", "success")
        return True

    def clear_logs(self) -> None:
        with self.lock:
            self.logs.clear()
            self.log("Activity cleared", "info")

    def status(self) -> dict[str, object]:
        connected = self.acquire_process()
        with self.lock:
            return {
                "connected": connected,
                "pid": self.pid,
                "base": f"0x{self.base:X}" if self.base else None,
                "ready": self.ready,
                "fetching": self.fetching,
                "flagsLoaded": len(ALLOWED),
                "clientVersion": target_install(self.pid).name if target_install(self.pid) else None,
                "offsetSource": self.offset_source,
                "offsetSourceHost": self.offset_source_host,
                "offsetFetchedAt": self.offset_fetched_at,
                "offsetBytes": self.offset_bytes,
                "offsetValidation": self.offset_validation,
                "backendPid": os.getpid(),
                "backendUptimeSec": max(0, int(time.time() - self.started_at)),
                "rollbackDepth": len(self.rollback_stack),
                "backendVersion": "6.5-stable",
                "browserUiBundled": os.path.isfile(os.path.join(_app_dist_root(), "index.html")),
                "browserUrl": f"http://{HOST}:{PORT}/app/",
                "logs": list(self.logs[-100:]),
            }

    def preflight(self, flags: dict[str, object]) -> dict[str, object]:
        return local_preflight(flags)

    def apply(self, flags: dict[str, object], source: str = "manual") -> dict[str, object]:
        # Save only Roblox-supported local overrides; never write game memory.
        pid=find_pid(TARGET)
        try: result=save_eligible(flags,pid)
        except (OSError, ValueError, TypeError) as exc:
            self.log(f"Local config save failed: {exc}", "error")
            return {"ok":False,"error":f"Failed to save ClientAppSettings.json: {exc}"}
        if result.get("ok"):
            snapshot=result.pop("rollback")
            rollback_id=str(int(time.time()*1000))
            with self.lock:
                self.rollback_stack.append({"id":rollback_id,"snapshot":snapshot})
                self.rollback_stack=self.rollback_stack[-20:]
            result["rollbackId"]=rollback_id
            self.log(f"Saved {result['applied']} local settings; {result['errors']} unsupported/invalid; restart Roblox", "success")
        else:self.log(str(result.get("error","No compatible flags")),"warning")
        return result

    def rollback_last(self) -> dict[str, object]:
        with self.lock:
            if not self.rollback_stack:
                return {"ok":False,"error":"No local configuration backup available"}
            entry=self.rollback_stack[-1]
        try:restore(entry["snapshot"])
        except OSError as exc:return {"ok":False,"error":str(exc)}
        with self.lock:self.rollback_stack.pop()
        self.log("Restored previous local ClientAppSettings.json", "success")
        return {"ok":True,"restored":True}



    def native_apply(self, flags: object, source: str = "native") -> dict[str, object]:
        # Stability mode: never launch the historical cross-process memory scanner.
        # That scanner can read enormous memory regions and change undocumented
        # values, triggering Roblox hangs or crashes on newer client builds.
        if not isinstance(flags, dict) or not flags:
            return {"ok": False, "error": "A nonempty JSON object of flags is required"}
        if len(flags) > 100000:
            return {"ok": False, "error": "Preset exceeds the 100,000 entry limit"}
        if not self.native_lock.acquire(blocking=False):
            return {"ok": False, "error": "An injection check is already running; try again after it completes"}
        try:
            probe = self.native_probe()
            if not probe["ok"]:
                self.log("Inject stopped safely: Roblox Player not detected", "warning")
                return {"ok": False, "error": probe["error"], "mode": "safe-detection",
                        "robloxDetected": False}
            self.log("Live injection blocked in stability build: unsupported memory scanner disabled", "warning")
            return {"ok": False, "mode": "safe-detection", "robloxDetected": True,
                    "pid": probe["pid"],
                    "error": "Roblox Player was detected, but live memory injection is paused in this stability build. The older native scanner can hang or crash Roblox. No Roblox memory was read or written. Use Save Allowed for supported local settings, then restart Roblox."}
        finally:
            self.native_lock.release()


def _clean_agent_base_url(raw: object) -> str:
    base = str(raw or "").strip().rstrip("/")
    if not base:
        raise ValueError("AI base URL is empty")
    if not (base.startswith("http://") or base.startswith("https://")):
        raise ValueError("AI base URL must start with http:// or https://")
    return base


def _agent_messages(payload: dict[str, object]) -> tuple[str, list[dict[str, str]]]:
    system = str(payload.get("system") or "")
    raw_messages = payload.get("messages")
    messages: list[dict[str, str]] = []
    if isinstance(raw_messages, list):
        for item in raw_messages[-20:]:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "user")
            if role not in ("user", "assistant"):
                continue
            content = str(item.get("content") or "")[:24000]
            messages.append({"role": role, "content": content})
    return system, messages


def _json_request(url: str, *, headers: dict[str, str] | None = None, body: object | None = None, timeout: int = 90) -> object:
    request_headers = {"User-Agent": "ZFLAG-Agent/1.5"}
    if headers:
        request_headers.update(headers)
    data = None
    method = "GET"
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        method = "POST"
        request_headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read(6 * 1024 * 1024)
    return json.loads(raw.decode("utf-8"))


def _ollama_models(base_url: str) -> list[str]:
    data = _json_request(base_url.rstrip("/") + "/api/tags", timeout=15)
    models = data.get("models") if isinstance(data, dict) else None
    out: list[str] = []
    if isinstance(models, list):
        for item in models:
            if isinstance(item, dict):
                name = str(item.get("name") or item.get("model") or "").strip()
                if name:
                    out.append(name)
    return out


def agent_models(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        return {"ok": False, "error": "Invalid agent request"}
    provider = str(payload.get("provider") or "ollama").strip().lower()
    api_key = str(payload.get("apiKey") or "").strip()
    try:
        base_url = _clean_agent_base_url(payload.get("baseUrl"))
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}

    try:
        if provider == "ollama":
            models = _ollama_models(base_url)
        elif provider in ("openai", "openrouter", "compatible"):
            headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            data = _json_request(base_url.rstrip("/") + "/models", headers=headers, timeout=25)
            rows = data.get("data") if isinstance(data, dict) else None
            models = [str(item.get("id")) for item in rows if isinstance(item, dict) and item.get("id")] if isinstance(rows, list) else []
        elif provider == "anthropic":
            if not api_key:
                return {"ok": False, "error": "Anthropic API key is required"}
            data = _json_request(base_url.rstrip("/") + "/v1/models", headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"}, timeout=25)
            rows = data.get("data") if isinstance(data, dict) else None
            models = [str(item.get("id")) for item in rows if isinstance(item, dict) and item.get("id")] if isinstance(rows, list) else []
        elif provider == "gemini":
            if not api_key:
                return {"ok": False, "error": "Gemini API key is required"}
            data = _json_request(base_url.rstrip("/") + "/models", headers={"x-goog-api-key": api_key}, timeout=25)
            rows = data.get("models") if isinstance(data, dict) else None
            models = []
            if isinstance(rows, list):
                for item in rows:
                    if not isinstance(item, dict):
                        continue
                    name = str(item.get("name") or "").strip()
                    if name.startswith("models/"):
                        name = name[7:]
                    if name:
                        models.append(name)
        else:
            return {"ok": False, "error": f"Unknown AI provider: {provider}"}
        return {"ok": True, "models": models[:250]}
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read(4096).decode("utf-8", errors="replace").strip()
        except Exception:
            pass
        return {"ok": False, "error": f"Model discovery HTTP {exc.code}" + (f": {detail[:400]}" if detail else "")}
    except urllib.error.URLError as exc:
        return {"ok": False, "error": f"Could not reach AI provider: {exc.reason}"}
    except Exception as exc:
        return {"ok": False, "error": f"Could not load models: {exc}"}


def _openai_response_content(data: object) -> str:
    if not isinstance(data, dict):
        return ""
    direct = data.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct
    output = data.get("output")
    if isinstance(output, list):
        parts: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    parts.append(str(part.get("text")))
        return "\n".join(parts)
    return ""


def agent_chat(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        return {"ok": False, "error": "Invalid agent request"}

    provider = str(payload.get("provider") or "ollama").strip().lower()
    model = str(payload.get("model") or "").strip()
    api_key = str(payload.get("apiKey") or "").strip()
    try:
        base_url = _clean_agent_base_url(payload.get("baseUrl"))
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}

    system, messages = _agent_messages(payload)
    if not model and provider != "ollama":
        return {"ok": False, "error": "Choose an AI model first"}

    headers: dict[str, str] = {}
    body: object
    endpoint: str
    actual_model = model

    try:
        if provider == "ollama":
            installed = _ollama_models(base_url)
            if not installed:
                return {"ok": False, "error": "Ollama is running, but no models are installed. Install one first, for example: ollama pull llama3.2:3b"}
            if not actual_model or actual_model not in installed:
                actual_model = installed[0]
            endpoint = base_url.rstrip("/") + "/api/chat"
            body = {
                "model": actual_model,
                "stream": False,
                "format": "json",
                "keep_alive": "15m",
                "messages": ([{"role": "system", "content": system}] if system else []) + messages,
                "options": {"temperature": 0.25},
            }
            data = _json_request(endpoint, body=body)
            content = str(((data.get("message") or {}) if isinstance(data, dict) else {}).get("content") or "")

        elif provider == "openai":
            if not api_key:
                return {"ok": False, "error": "OpenAI API key is required"}
            endpoint = base_url.rstrip("/") + "/responses"
            headers = {"Authorization": f"Bearer {api_key}"}
            transcript = "\n\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)
            body = {"model": actual_model, "instructions": system, "input": transcript or "Hello"}
            data = _json_request(endpoint, headers=headers, body=body)
            content = _openai_response_content(data)

        elif provider == "anthropic":
            if not api_key:
                return {"ok": False, "error": "Anthropic API key is required"}
            endpoint = base_url.rstrip("/") + "/v1/messages"
            headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
            body = {"model": actual_model, "max_tokens": 4096, "system": system, "messages": messages}
            data = _json_request(endpoint, headers=headers, body=body)
            blocks = data.get("content") if isinstance(data, dict) else None
            content = "\n".join(str(item.get("text")) for item in blocks if isinstance(item, dict) and item.get("type") == "text" and item.get("text")) if isinstance(blocks, list) else ""

        elif provider == "gemini":
            if not api_key:
                return {"ok": False, "error": "Gemini API key is required"}
            encoded_model = urllib.parse.quote(actual_model, safe="-._")
            endpoint = base_url.rstrip("/") + f"/models/{encoded_model}:generateContent"
            headers = {"x-goog-api-key": api_key}
            contents = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]} for m in messages]
            body = {
                "contents": contents or [{"role": "user", "parts": [{"text": "Hello"}]}],
                "systemInstruction": {"parts": [{"text": system}]},
                "generationConfig": {"responseMimeType": "application/json"},
            }
            data = _json_request(endpoint, headers=headers, body=body)
            candidates = data.get("candidates") if isinstance(data, dict) else None
            first = candidates[0] if isinstance(candidates, list) and candidates else {}
            parts = ((first.get("content") or {}).get("parts") if isinstance(first, dict) else None) or []
            content = "\n".join(str(part.get("text")) for part in parts if isinstance(part, dict) and part.get("text"))

        elif provider in ("openrouter", "compatible"):
            if provider == "openrouter" and not api_key:
                return {"ok": False, "error": "OpenRouter API key is required"}
            endpoint = base_url.rstrip("/") + "/chat/completions"
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            body = {"model": actual_model, "messages": ([{"role": "system", "content": system}] if system else []) + messages, "temperature": 0.25}
            data = _json_request(endpoint, headers=headers, body=body)
            choices = data.get("choices") if isinstance(data, dict) else None
            first = choices[0] if isinstance(choices, list) and choices else {}
            content = str(((first.get("message") or {}) if isinstance(first, dict) else {}).get("content") or "")
        else:
            return {"ok": False, "error": f"Unknown AI provider: {provider}"}

        if not content.strip():
            return {"ok": False, "error": "AI provider returned an empty response"}
        return {"ok": True, "content": content, "model": actual_model}
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read(4096).decode("utf-8", errors="replace").strip()
        except Exception:
            pass
        message = f"AI provider HTTP {exc.code}"
        if detail:
            message += f": {detail[:700]}"
        return {"ok": False, "error": message}
    except urllib.error.URLError as exc:
        return {"ok": False, "error": f"Could not reach AI provider: {exc.reason}"}
    except Exception as exc:
        return {"ok": False, "error": f"AI request failed: {exc}"}


# The request handlers and startup worker share exactly one runtime.
# It must exist BEFORE the worker starts; otherwise /status, /native-probe
# and /apply raise NameError and the browser reports a dropped connection.
runtime = Runtime()


def init_worker() -> None:
    try:
        runtime.acquire_process()
        runtime.refresh_offsets()
    except Exception as exc:
        runtime.log(f"Backend initialization failed: {type(exc).__name__}: {exc}", "error")


threading.Thread(target=init_worker, daemon=True).start()


class Handler(BaseHTTPRequestHandler):
    server_version = "FFlagStudio/6.4"

    def _cors(self) -> None:
        origin = self.headers.get("Origin", "")
        allowed = {
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:4173",
            "http://127.0.0.1:4173",
            "http://tauri.localhost",
            "https://tauri.localhost",
            "tauri://localhost",
        }
        if origin in allowed:
            self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def _json(self, status: int, payload: object) -> None:
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _serve_app_file(self) -> bool:
        parsed = urllib.parse.urlparse(self.path)
        if not parsed.path.startswith("/app"):
            return False
        root = os.path.abspath(_app_dist_root())
        relative = parsed.path[4:].lstrip("/") or "index.html"
        candidate = os.path.abspath(os.path.join(root, relative.replace("/", os.sep)))
        if not candidate.startswith(root + os.sep) and candidate != os.path.join(root, "index.html"):
            self.send_error(403)
            return True
        if not os.path.isfile(candidate):
            # SPA routes may fall back to index.html, but missing .js/.css/image/font
            # assets must return 404 rather than HTML with the wrong MIME type.
            has_extension = bool(Path(relative).suffix)
            if has_extension:
                self._json(404, {"ok": False, "error": f"Asset not found: {relative}"})
                return True
            candidate = os.path.join(root, "index.html")
        if not os.path.isfile(candidate):
            self._json(404, {"ok": False, "error": "Browser UI is not bundled in this build"})
            return True
        try:
            data = Path(candidate).read_bytes()
            content_type = mimetypes.guess_type(candidate)[0] or "application/octet-stream"
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-cache" if candidate.endswith("index.html") else "public, max-age=3600")
            self.end_headers()
            self.wfile.write(data)
        except Exception as exc:
            self._json(500, {"ok": False, "error": f"Could not serve browser UI: {exc}"})
        return True

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)

        # Friendly browser entry points. /app without a trailing slash must
        # redirect so Vite's relative ./assets URLs resolve under /app/assets.
        if parsed.path in ("/", "/app"):
            self.send_response(302)
            self._cors()
            self.send_header("Location", "/app/")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return

        if parsed.path == "/status":
            self._json(200, runtime.status())
            return
        if parsed.path == "/health":
            bundle = _browser_bundle_check()
            self._json(200, {
                "ok": True,
                "backendVersion": "6.5-stable",
                "browserUi": bool(bundle.get("browserUi")),
                "browserUrl": f"http://{HOST}:{PORT}/app/",
            })
            return
        if parsed.path == "/browser-check":
            result = _browser_bundle_check()
            self._json(200 if result.get("ok") else 503, result)
            return
        if self._serve_app_file():
            return
        self._json(404, {
            "ok": False,
            "error": "Not found",
            "browserUrl": f"http://{HOST}:{PORT}/app/",
        })

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > 32_000_000:
                self._json(413, {"ok": False, "error": "Payload too large"})
                return
            raw = self.rfile.read(length) if length else b"{}"
            payload = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            self._json(400, {"ok": False, "error": f"Invalid JSON: {exc}"})
            return

        if self.path == "/preflight":
            flags = payload.get("flags") if isinstance(payload, dict) else None
            result = runtime.preflight(flags)
            self._json(200 if result.get("ok") else 400, result)
            return
        if self.path == "/native-probe":
            try:
                result = runtime.native_probe()
                self._json(200, result)
            except Exception as exc:
                runtime.log(f"Native detection error: {type(exc).__name__}: {exc}", "error")
                self._json(500, {"ok": False, "found": False,
                                 "error": f"Detection backend error: {type(exc).__name__}. No Roblox memory was accessed."})
            return
        if self.path == "/native-apply":
            flags = payload.get("flags") if isinstance(payload, dict) else None
            source = str(payload.get("source") or "native") if isinstance(payload, dict) else "native"
            result = runtime.native_apply(flags, source=source[:40])
            self._json(200, result)
            return
        if self.path == "/apply":
            flags = payload.get("flags") if isinstance(payload, dict) else None
            source = str(payload.get("source") or "manual") if isinstance(payload, dict) else "manual"
            result = runtime.apply(flags, source=source[:40])
            # A valid /apply request always returns JSON with the real outcome.
            self._json(200, result)
            return
        if self.path == "/rollback-last":
            result = runtime.rollback_last()
            self._json(200 if result.get("ok") else 409, result)
            return
        if self.path == "/refresh-offsets":
            threading.Thread(target=runtime.refresh_offsets, daemon=True).start()
            self._json(202, {"ok": True, "message": "Local allowlist refreshed"})
            return
        if self.path == "/clear-logs":
            runtime.clear_logs()
            self._json(200, {"ok": True, "message": "Activity cleared"})
            return
        if self.path == "/open-browser":
            url = f"http://{HOST}:{PORT}/app/"
            ok = _open_url(url)
            self._json(200 if ok else 500, {"ok": ok, "url": url, "error": None if ok else "Could not open the default browser"})
            return
        if self.path == "/diagnostics":
            self._json(200, {"ok": True, "status": runtime.status(), "allowlistReference": REFERENCE})
            return
        if self.path == "/shutdown":
            self._json(200, {"ok": True, "message": "Backend shutting down"})
            threading.Timer(0.15, lambda: os._exit(0)).start()
            return
        if self.path == "/agent/test":
            test_payload = dict(payload) if isinstance(payload, dict) else {}
            test_payload["system"] = 'Return ONLY this JSON object: {"reply":"ok","actions":[]}'
            test_payload["messages"] = [{"role": "user", "content": "Connection test. Reply exactly as requested."}]
            result = agent_chat(test_payload)
            self._json(200 if result.get("ok") else 502, result)
            return
        if self.path == "/agent/models":
            result = agent_models(payload)
            self._json(200 if result.get("ok") else 502, result)
            return
        if self.path == "/agent/chat":
            result = agent_chat(payload)
            self._json(200 if result.get("ok") else 502, result)
            return
        self._json(404, {"ok": False, "error": "Not found"})

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    print(f"FFlag Studio backend listening on http://{HOST}:{PORT}")
    print("Keep this window open while using the UI.")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
