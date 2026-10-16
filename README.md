# ZFLAG — official website and Windows installer

This repository contains the [ZFLAG desktop website](index.html), its Render static-site configuration, and its **published Windows installer**.

## Download for Windows 10/11 (x64)

**[Download ZFLAG_Setup.exe — v2.0.41](https://github.com/MadeByZebra/zflag-site/releases/download/v2.0.41/ZFLAG_Setup.exe)**

- One standalone **.exe installer** for end users: download → install → open.
- No BAT, CMD, PowerShell, ZIP extraction, Python, Rust, Node.js, or Visual Studio required for people installing it.
- Setup replaces old ZFLAG-named desktop/Start Menu shortcuts in the installing Windows user's profile.
- Saved FastFlag configuration files are not intentionally removed by the shortcut cleanup.
- NSIS installation, local backend startup, and reinstall over a RUNNING ZFLAG GUI/backend passed automated Windows smoke tests.
- Windows SmartScreen may warn because the installer is **unsigned**.
- Actual in-game Roblox FastFlag injection **was not tested in CI**. Roblox updates may change what flags are supported.

SHA-256: `f4345518f0e69f1bab529a034f724d99a0926b08fd25ddddde9c64e504559de6`.

Build run: [Windows CI #38861527875](https://github.com/MadeByZebra/zflag-site/actions/runs/38861527875). Release: [v2.0.41](https://github.com/MadeByZebra/zflag-site/releases/tag/v2.0.41).

## Website and hosting

The website source is `index.html`. Its **Download** controls use the explicit verified GitHub release asset above. `render.yaml` configures Render hosting. Existing older .exe files in the repo are retained for rollback and are no longer referenced by current Download buttons.

For an existing connected Render service with auto-deploy enabled, pushing to `main` redeploys the site. Otherwise trigger a Render deployment of the latest `main` commit.

## Maintainer build

`.github/workflows/build-zflag-windows.yml` builds the Windows installer from the verified `zflag-desktop-source.b64` archive. The workflow builds the native C++ engine, Python sidecar, React frontend, Tauri NSIS installer, tests Windows installation and bundled backend startup, and publishes `ZFLAG_Setup.exe` with a checksum.

Source/build scripts are **maintainer-only** and are not part of the installer workflow exposed to downloaders.

ZFLAG v2.0.41 additionally passes a Windows regression test that installs again while its own GUI and backend are still running, then verifies the locked backend was replaced and restarted.
