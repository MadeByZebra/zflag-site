"""Read-only audit of ZFLAG bundled source and external upstream release metadata.

No binaries are executed and nothing is installed or injected.
"""
from __future__ import annotations
import base64
import hashlib
import io
import json
import pathlib
import re
import zipfile
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE = ROOT / "zflag-desktop-source.b64"
EXPECTED = "6ed33023f232918b0fc3d3191c3a8264a99ff2bed95b30755b19f223f155fd9e"

def status(label: str, value: object) -> None:
    print(f"{label}: {value}")

blob = base64.b64decode(SOURCE.read_text(encoding="utf-8").strip(), validate=True)
status("Bundled source SHA-256", hashlib.sha256(blob).hexdigest())
with zipfile.ZipFile(io.BytesIO(blob)) as z:
    names = z.namelist()
    status("Bundled source entries", len(names))
    server = next((p for p in names if p.endswith("backend/server.py")), None)
    native = [p for p in names if p.endswith("fastflag_injector_gui_enhanced.cpp")]
    status("Bundled backend", server)
    status("Bundled native C++ engine", native[:2])
    if server:
        data = z.read(server).decode("utf-8", "replace")
        for term in (
            "fastflag container not found",
            "native_incompatible",
            "apply_flags",
            "enhanced",
            "ClientAppSettings",
            "find_pid",
        ):
            locations = [i + 1 for i, line in enumerate(data.splitlines())
                         if term.casefold() in line.casefold()]
            status("Backend pattern " + term, locations[:25])
    for native_path in native[:1]:
        code = z.read(native_path).decode("utf-8", "replace").splitlines()
        for term in ("fastflag container", "container not found",
                     "OpenProcess", "WriteProcessMemory", "ReadProcessMemory"):
            indexes = [i for i, line in enumerate(code)
                       if term.casefold() in line.casefold()]
            status("Native code pattern " + term, [i + 1 for i in indexes[:15]])
            for i in indexes[:4]:
                context = " | ".join(x.strip()[:175] for x in code[max(0, i-2):min(len(code), i+3)])
                status("C++ context", context[:560])
status("Known package SHA matches", hashlib.sha256(blob).hexdigest() == EXPECTED)
try:
    with urllib.request.urlopen(
        urllib.request.Request(
            "https://api.github.com/repos/davelovestars/oldinjector-version-working/git/trees/omg?recursive=1",
            headers={"User-Agent": "ZFLAG-ReadOnly-Audit/1.0", "Accept": "application/vnd.github+json"}
        ), timeout=12,
    ) as response:
        tree = json.load(response)["tree"]
    status("Upstream tag paths", [row["path"] for row in tree])
    status("Upstream tag contains C++/Python/Rust source", any(
        row["path"].lower().endswith((".cpp", ".c", ".h", ".py", ".rs", ".cs"))
        for row in tree))
except Exception as exc:
    status("Upstream tag metadata", "Unable to query GitHub; local audit still valid: " + str(exc)[:160])
