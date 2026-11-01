"""ZFLAG Supported Config - a standalone, allowlist-only Roblox config utility.

This utility does NOT access Roblox process memory, inject, attach, or bypass
client restrictions. It only writes Roblox's local ClientAppSettings.json file.
Roblox may change its published allowlist at any time.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

APP_NAME = "ZFLAG Supported Config"
APP_VERSION = "1.0.0"
OFFICIAL_SOURCE = "https://devforum.roblox.com/t/allowlist-for-local-client-configuration-via-fast-flags/3966569"

ALLOWLIST = {
    "Geometry": (
        "DFIntCSGLevelOfDetailSwitchingDistance",
        "DFIntCSGLevelOfDetailSwitchingDistanceL12",
        "DFIntCSGLevelOfDetailSwitchingDistanceL23",
        "DFIntCSGLevelOfDetailSwitchingDistanceL34",
    ),
    "Rendering": (
        "FFlagHandleAltEnterFullscreenManually",
        "DFFlagTextureQualityOverrideEnabled",
        "DFIntTextureQualityOverride",
        "FIntDebugForceMSAASamples",
        "DFFlagDisableDPIScale",
        "FFlagDebugGraphicsPreferD3D11",
        "FFlagDebugSkyGray",
        "DFFlagDebugPauseVoxelizer",
        "DFIntDebugFRMQualityLevelOverride",
        "FIntFRMMaxGrassDistance",
        "FIntFRMMinGrassDistance",
        "FFlagDebugGraphicsPreferVulkan",
        "FFlagDebugGraphicsPreferOpenGL",
    ),
    "UI": ("FIntGrassMovementReducedMotionFactor",),
}
ALLOWED = frozenset(name for group in ALLOWLIST.values() for name in group)
TRUE_STRINGS = frozenset(("true", "1", "yes", "on"))
FALSE_STRINGS = frozenset(("false", "0", "no", "off"))
WINDOWS_EXE = "RobloxPlayerBeta.exe"


def normalize_value(flag: str, value: Any) -> str:
    """Return Roblox-compatible string value or raise ValueError."""
    if flag not in ALLOWED:
        raise ValueError("Not on the published local-configuration allowlist: " + flag)
    if flag.startswith(("FFlag", "DFFlag", "SFFlag")):
        if isinstance(value, bool):
            return "True" if value else "False"
        if isinstance(value, int) and value in (0, 1):
            return "True" if value else "False"
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in TRUE_STRINGS:
                return "True"
            if normalized in FALSE_STRINGS:
                return "False"
        raise ValueError(flag + " must have a boolean True/False value")
    if flag.startswith(("FInt", "DFInt", "SFInt")):
        if isinstance(value, bool):
            raise ValueError(flag + " requires a signed integer, not a boolean")
        if isinstance(value, int):
            num = value
        elif isinstance(value, str) and re.fullmatch(r"[+-]?\d{1,12}", value.strip()):
            num = int(value.strip(), 10)
        else:
            raise ValueError(flag + " requires a signed decimal integer")
        if not (-2147483648 <= num <= 2147483647):
            raise ValueError(flag + " is outside the 32-bit integer range")
        return str(num)
    raise ValueError("Unsupported flag data type for " + flag)


def normalize_preset(data: Any) -> tuple[dict[str, str], dict[str, int]]:
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object of FastFlag names and values")
    maybe_flags = data.get("flags")
    if isinstance(maybe_flags, dict):
        data = maybe_flags
    accepted: dict[str, str] = {}
    unsupported = invalid = 0
    for key, value in data.items():
        if not isinstance(key, str) or key not in ALLOWED:
            unsupported += 1
            continue
        try:
            accepted[key] = normalize_value(key, value)
        except ValueError:
            invalid += 1
    return accepted, {"accepted": len(accepted), "unsupported": unsupported, "invalid": invalid}


def roblox_versions_dir(localappdata: Path | None = None) -> Path:
    if localappdata is None:
        env = os.environ.get("LOCALAPPDATA", "")
        localappdata = Path(env) if env else Path.home() / "AppData" / "Local"
    return localappdata / "Roblox" / "Versions"


def discover_roblox(localappdata: Path | None = None) -> list[Path]:
    root = roblox_versions_dir(localappdata)
    if not root.is_dir():
        return []
    found = []
    for folder in root.iterdir():
        if folder.is_dir() and folder.name.startswith("version-"):
            exe = folder / WINDOWS_EXE
            if exe.is_file():
                found.append(exe)
    return sorted(found, key=lambda p: p.stat().st_mtime, reverse=True)


def config_target(roblox_exe: Path, localappdata: Path | None = None) -> Path:
    exe = Path(roblox_exe).resolve()
    root = roblox_versions_dir(localappdata).resolve()
    if exe.name.lower() != WINDOWS_EXE.lower() or not exe.is_file():
        raise ValueError("Select a valid RobloxPlayerBeta.exe installation")
    if exe.parent.parent != root or not exe.parent.name.startswith("version-"):
        raise ValueError("This build only stages settings in the normal Roblox Versions folder")
    return exe.parent / "ClientSettings" / "ClientAppSettings.json"


def get_existing(target: Path) -> dict[str, Any]:
    if not target.is_file():
        return {}
    try:
        value = json.loads(target.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Existing settings are unreadable; preserve or repair them before staging") from exc
    if not isinstance(value, dict):
        raise ValueError("Existing ClientAppSettings.json is not a JSON object")
    return value


def backup_settings(target: Path) -> Path | None:
    if not target.is_file():
        return None
    directory = target.parent / ".zflag-backups"
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    destination = directory / ("ClientAppSettings-" + timestamp + ".json")
    shutil.copy2(target, destination)
    if destination.read_bytes() != target.read_bytes():
        raise OSError("Backup verification failed; nothing was overwritten")
    return destination


def write_verified(target: Path, settings: dict[str, str]) -> Path | None:
    if not settings:
        raise ValueError("No allowlisted flags to stage. Add or import at least one.")
    normalized, stats = normalize_preset(settings)
    if normalized != settings or stats["accepted"] != len(settings):
        raise ValueError("Preset includes a non-allowlisted or malformed flag")
    target.parent.mkdir(parents=True, exist_ok=True)
    # Do not overwrite corrupt or non-JSON files until the owner repairs them.
    get_existing(target)
    backup = backup_settings(target)
    staged = json.dumps(settings, indent=2, sort_keys=True) + "\n"
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=target.parent,
                                         prefix=".zflag-stage-", suffix=".json", delete=False) as file:
            temp_file = Path(file.name)
            file.write(staged)
            file.flush()
            os.fsync(file.fileno())
        if json.loads(temp_file.read_text(encoding="utf-8")) != settings:
            raise OSError("Pre-commit verification failed")
        os.replace(temp_file, target)
        temp_file = None
        if json.loads(target.read_text(encoding="utf-8")) != settings:
            raise OSError("Post-write verification failed")
    finally:
        if temp_file and temp_file.exists():
            temp_file.unlink()
    return backup


def restore_backup(target: Path, backup: Path) -> Path | None:
    base = (target.parent / ".zflag-backups").resolve()
    source = Path(backup).resolve()
    if source.parent != base or not source.name.startswith("ClientAppSettings-"):
        raise ValueError("Choose a backup from this installation's .zflag-backups folder")
    if not isinstance(json.loads(source.read_text(encoding="utf-8")), dict):
        raise ValueError("Backup does not contain a JSON object")
    prior = backup_settings(target)
    with tempfile.NamedTemporaryFile("wb", dir=target.parent,
                                     prefix=".zflag-restore-", suffix=".json", delete=False) as temp:
        temporary = Path(temp.name)
        temp.write(source.read_bytes())
        temp.flush()
        os.fsync(temp.fileno())
    try:
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()
    if target.read_bytes() != source.read_bytes():
        raise OSError("Restore verification failed")
    return prior


def open_gui() -> None:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    import webbrowser

    background, surface, border = "#090b0e", "#15191e", "#343b42"
    fg, muted, accent = "#edf0f3", "#a0aab7", "#82b7e4"
    root = tk.Tk()
    root.title(APP_NAME + "  ·  " + APP_VERSION)
    root.geometry("960x690")
    root.minsize(770, 560)
    root.configure(bg=background)
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", background=background, foreground=fg, font=("Segoe UI", 10))
    style.configure("TFrame", background=background)
    style.configure("TLabel", background=background, foreground=fg)
    style.configure("TButton", background=surface, foreground=fg, borderwidth=1, padding=(12, 9))
    style.map("TButton", background=[("active", border)])
    style.configure("Treeview", background=surface, fieldbackground=surface, foreground=fg, rowheight=28)
    style.configure("Treeview.Heading", background="#232930", foreground=fg)
    style.map("Treeview", background=[("selected", "#2b526d")])
    style.configure("TCombobox", fieldbackground=surface, background=surface, foreground="#101010")
    style.configure("TEntry", fieldbackground="#f7f9fb", foreground="#111111")

    selected: dict[str, str] = {}
    versions = discover_roblox()
    exe_var = tk.StringVar(value=str(versions[0]) if versions else "")
    name_var = tk.StringVar(value=next(iter(sorted(ALLOWED))))
    value_var = tk.StringVar(value="True")
    info_var = tk.StringVar(value="Select a Roblox version, then add or import allowlisted flags.")
    stats_var = tk.StringVar(value="0 staged flags")
    title = ttk.Label(root, text="ZFLAG  /  SUPPORTED CONFIG", font=("Segoe UI Semibold", 22))
    title.pack(anchor="w", padx=30, pady=(24, 3))
    ttk.Label(root, text="Roblox allowlisted startup settings · no memory injection · local-only",
              foreground=muted).pack(anchor="w", padx=30, pady=(0, 14))

    main = ttk.Frame(root)
    main.pack(fill="both", expand=True, padx=30, pady=8)

    ttk.Label(main, text="ROBOLOX INSTALLATION", font=("Segoe UI Semibold", 10),
              foreground=accent).pack(anchor="w", pady=(3, 8))
    version_frame = ttk.Frame(main)
    version_frame.pack(fill="x")
    path_combo = ttk.Combobox(version_frame, textvariable=exe_var, values=[str(e) for e in versions],
                             state="readonly" if versions else "normal")
    path_combo.pack(side="left", fill="x", expand=True, padx=(0, 8))

    def refresh_versions():
        nonlocal versions
        versions = discover_roblox()
        path_combo.configure(values=[str(x) for x in versions],
                             state="readonly" if versions else "normal")
        if versions:
            exe_var.set(str(versions[0]))
            status("Detected " + str(len(versions)) + " Roblox installation(s).")
        else:
            exe_var.set("")
            status("No normal Roblox Player installation found in LocalAppData.")

    ttk.Button(version_frame, text="Refresh", command=refresh_versions).pack(side="left")
    ttk.Label(main, text="Published Roblox allowlist is subject to change. Only flags on the initial official list are included.",
              foreground=muted, wraplength=840).pack(anchor="w", pady=(7, 20))

    ttk.Label(main, text="EDIT ALLOWLISTED SETTINGS", font=("Segoe UI Semibold", 10),
              foreground=accent).pack(anchor="w", pady=(0, 9))
    editor = ttk.Frame(main)
    editor.pack(fill="x")
    ttk.Combobox(editor, textvariable=name_var, values=sorted(ALLOWED), state="readonly",
                 width=53).pack(side="left", padx=(0, 10))
    ttk.Entry(editor, textvariable=value_var, width=15).pack(side="left", padx=(0, 10))
    def status(msg: str):
        info_var.set(msg)

    tree_frame = ttk.Frame(main)
    tree_frame.pack(fill="both", expand=True, pady=(16, 0))
    tree = ttk.Treeview(tree_frame, columns=("name", "value"), show="headings", height=11,
                        selectmode="browse")
    tree.heading("name", text="Allowed FastFlag")
    tree.heading("value", text="Value")
    tree.column("name", width=550, stretch=True)
    tree.column("value", width=150, stretch=False)
    tree.pack(side="left", fill="both", expand=True)
    scrollbar = ttk.Scrollbar(tree_frame, command=tree.yview)
    scrollbar.pack(side="right", fill="y")
    tree.configure(yscrollcommand=scrollbar.set)
    def render():
        tree.delete(*tree.get_children())
        for key, value in sorted(selected.items()):
            tree.insert("", "end", iid=key, values=(key, value))
        stats_var.set(str(len(selected)) + " allowed flag(s) selected")
    def add():
        try:
            key = name_var.get()
            selected[key] = normalize_value(key, value_var.get())
            render()
            status(key + " updated. Settings are NOT applied until you click Stage.")
        except ValueError as exc:
            messagebox.showerror("Invalid FastFlag value", str(exc), parent=root)
    def remove():
        for key in tree.selection():
            selected.pop(key, None)
        render()
        status("Removed selection from the staging list.")
    def row_select(_):
        keys = tree.selection()
        if keys:
            name_var.set(keys[0])
            value_var.set(selected[keys[0]])
    tree.bind("<<TreeviewSelect>>", row_select)
    ttk.Button(editor, text="Add / Update", command=add).pack(side="left")
    ttk.Button(editor, text="Remove selected", command=remove).pack(side="left", padx=(6, 0))

    action_bar = ttk.Frame(main)
    action_bar.pack(fill="x", pady=(13, 7))
    def current_target() -> Path:
        if not exe_var.get():
            raise ValueError("RobloxPlayerBeta.exe not found. Install the regular Windows Roblox Player.")
        return config_target(Path(exe_var.get()))

    def import_json():
        source = filedialog.askopenfilename(parent=root, title="Import ZFLAG JSON preset",
                                            filetypes=(("JSON files", "*.json"), ("All files", "*.*")))
        if not source:
            return
        try:
            data = json.loads(Path(source).read_text(encoding="utf-8-sig"))
            accepted, counts = normalize_preset(data)
            if not accepted:
                raise ValueError("No flags on the published allowlist were found in this file.")
            selected.update(accepted)
            render()
            status("Imported " + str(counts["accepted"]) + " allowed; skipped " +
                   str(counts["unsupported"]) + " other names and " +
                   str(counts["invalid"]) + " invalid values.")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            messagebox.showerror("Import failed", str(exc), parent=root)

    def preview():
        try:
            target = current_target()
            existing = get_existing(target)
            old_allowed, counts = normalize_preset(existing)
            sample = json.dumps(selected, indent=2, sort_keys=True)
            messagebox.showinfo("Preview · NOT injected",
                                "File: " + str(target) + "\n\nSelected flags: " + str(len(selected)) +
                                "\nExisting settings: " + str(len(existing)) +
                                "\nOld allowlisted settings: " + str(len(old_allowed)) +
                                "\nOld non-allowlisted/invalid settings: " +
                                str(counts["unsupported"] + counts["invalid"]) +
                                "\n\nThe staged file REPLACES the current file after a verified backup.\n\n" +
                                sample[:2600], parent=root)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Preview unavailable", str(exc), parent=root)

    def stage():
        try:
            target = current_target()
            existing = get_existing(target)
            if not selected:
                raise ValueError("Add or import an allowlisted flag before staging.")
            if not messagebox.askyesno("Confirm supported-config staging",
                    "Save " + str(len(selected)) + " allowlisted flags to:\n" + str(target) +
                    "\n\nThis REPLACES the existing ClientAppSettings.json (" + str(len(existing)) +
                    " entries). An exact backup is created if a file already exists.\n\n"
                    "Close Roblox first; restart it afterward. This does NOT inject memory or guarantee in-game effects.",
                    parent=root):
                return
            backup = write_verified(target, selected)
            status("Verified " + str(len(selected)) + " saved settings. Restart Roblox for effect.")
            messagebox.showinfo("Settings saved and verified",
                "The Roblox startup configuration was written and read back successfully.\n\n" +
                str(target) + "\n\n" +
                ("Backup: " + str(backup) if backup else "There was no previous file to back up.") +
                "\n\nRestart Roblox. Roblox may ignore or change allowlisted flags in future releases.",
                parent=root)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            messagebox.showerror("Staging failed (not injected)", str(exc), parent=root)

    def restore():
        try:
            target = current_target()
            folder = target.parent / ".zflag-backups"
            backups = sorted(folder.glob("ClientAppSettings-*.json")) if folder.is_dir() else []
            if not backups:
                raise ValueError("No backups exist for this installation yet.")
            source = filedialog.askopenfilename(parent=root, initialdir=str(folder),
                                                title="Restore a ZFLAG settings backup",
                                                filetypes=(("JSON backups", "*.json"),))
            if not source:
                return
            if not messagebox.askyesno("Restore old settings",
                   "Restore the selected previous ClientAppSettings.json?\n\nCurrent settings will be backed up first.",
                   parent=root):
                return
            restore_backup(target, Path(source))
            status("Restored and verified previous settings. Restart Roblox.")
            messagebox.showinfo("Restored", "Old settings restored and verified. Restart Roblox.",
                                parent=root)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            messagebox.showerror("Restore failed", str(exc), parent=root)

    ttk.Button(action_bar, text="Import ZFLAG JSON", command=import_json).pack(side="left", padx=(0, 8))
    ttk.Button(action_bar, text="Preview", command=preview).pack(side="left", padx=(0, 8))
    ttk.Button(action_bar, text="Stage supported config", command=stage).pack(side="left", padx=(0, 8))
    ttk.Button(action_bar, text="Restore backup", command=restore).pack(side="left")
    ttk.Label(main, textvariable=stats_var, foreground=muted).pack(anchor="w", pady=(4, 6))
    ttk.Separator(main).pack(fill="x", pady=(8, 10))
    ttk.Label(main, textvariable=info_var, foreground=accent, wraplength=860).pack(anchor="w")
    link = ttk.Label(main, text="Roblox's official FastFlag local-configuration allowlist ↗",
                     foreground=muted, cursor="hand2")
    link.pack(anchor="w", pady=(12, 0))
    link.bind("<Button-1>", lambda _: webbrowser.open(OFFICIAL_SOURCE))
    root.mainloop()


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        # Smoke-test the packaged EXE without launching Tkinter/Roblox.
        sample, counters = normalize_preset({"FFlagHandleAltEnterFullscreenManually": True,
                                              "DFIntTextureQualityOverride": 2,
                                              "DFIntServerTickRate": 999})
        ok = sample == {"FFlagHandleAltEnterFullscreenManually": "True",
                        "DFIntTextureQualityOverride": "2"} and counters["unsupported"] == 1
        if len(sys.argv) > 2:
            Path(sys.argv[2]).write_text("OK\n" if ok else "FAILED\n", encoding="utf-8")
        if not ok:
            raise SystemExit(1)
        return
    open_gui()


if __name__ == "__main__":
    main()
