# ZFLAG custom Windows installer (preview)

This is the real, source-controlled .NET 8 WPF bootstrapper: no PowerShell window, developer prerequisites, node, npm, Rust or Python on end-user machines. The Windows Actions build embeds the previously Windows-tested **ZFLAG v2.0.30 stability app**, whose cross-process memory injection is deliberately disabled following Roblox freezes.

**Two independent build modes:**
- `--verify`: verify the 3 required executable payloads and exit (CI).
- `--qa-install "C:\path\to\isolated\test"`: extract and verify the application to a CI-only folder, skipping all shell/registry changes.
- Normal launch: branded GUI; install to `%LOCALAPPDATA%\ZFLAG Studio Preview`, create Start shortcut and optional desktop shortcut, register per-user uninstall.
- `--uninstall`: branded GUI to uninstall the preview; preserves users' Roblox and ZFLAG preferences. Any locked uninstall helper is scheduled for cleanup on reboot.

**Version isolation:** This is a new side-by-side preview identity that does not invoke any previous NSIS uninstall entry. Do not point the public site to the test build until the owner has confirmed the application is working.

Payloads are sourced from verified GitHub Actions output, not downloaded by end-user installer. Untrusted paths inside a ZIP are rejected. No external scripts are launched by the installer.
