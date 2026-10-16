# ZFLAG — official website and Windows installer

This repository contains the [ZFLAG desktop website](index.html), its Render static-site configuration, and its **published Windows installer**.

## Download for Windows 10/11 (x64)

**[Download ZFLAG_Setup.exe — v2.0.51](https://github.com/MadeByZebra/zflag-site/releases/download/v2.0.51/ZFLAG_Setup.exe)**

- One standalone **.exe installer** for end users: download → install → open.
- No BAT, CMD, PowerShell, ZIP extraction, Python, Rust, Node.js, or Visual Studio required for people installing it.
- Setup replaces old ZFLAG-named desktop/Start Menu shortcuts in the installing Windows user's profile.
- Saved FastFlag configuration files are not intentionally removed by the shortcut cleanup.
- NSIS installation, local backend startup, and reinstall over a RUNNING ZFLAG GUI/backend passed automated Windows smoke tests.
- Windows SmartScreen may warn because the installer is **unsigned**.
- Actual in-game Roblox FastFlag injection **was not tested in CI**. Roblox updates may change what flags are supported.

SHA-256: `c7aa4fb334f77a297f368f32e6bad555fc18f85d93c8f86cb7c8543cb1059224`.

Build run: [Windows CI #38970541650](https://github.com/MadeByZebra/zflag-site/actions/runs/38970541650). Release: [v2.0.47](https://github.com/MadeByZebra/zflag-site/releases/tag/v2.0.47).

## Website and hosting

The website source is `index.html`. Its **Download** controls use the explicit verified GitHub release asset above. `render.yaml` configures Render hosting. Existing older .exe files in the repo are retained for rollback and are no longer referenced by current Download buttons.

For an existing connected Render service with auto-deploy enabled, pushing to `main` redeploys the site. Otherwise trigger a Render deployment of the latest `main` commit.

## Maintainer build

`.github/workflows/build-zflag-windows.yml` builds the Windows installer from the verified `zflag-desktop-source.b64` archive. The workflow builds the native C++ engine, Python sidecar, React frontend, Tauri NSIS installer, tests Windows installation and bundled backend startup, and publishes `ZFLAG_Setup.exe` with a checksum.

Source/build scripts are **maintainer-only** and are not part of the installer workflow exposed to downloaders.

ZFLAG v2.0.47 additionally passes a Windows regression test that installs again while its own GUI and backend are still running, then verifies the locked backend was replaced and restarted.

The v2.0.47 release uses the owner's blue metallic Z artwork across the desktop app, installer, shortcut and website icon. Desktop fixes include an opaque Windows WebView2 surface, less expensive CSS effects and safer polling/apply request behavior. Automated Windows installation passed; live Roblox memory injection and user-specific GPU flickering remain untested.

ZFLAG v2.0.47: owner's actual silver Z icon (without the previous artificial blue-glow treatment), unified matte/dark UI controls across Inject/Settings/Library/Agent, stronger native engine availability status, guard against backend restart during injections, accurate partial-result reporting, and activity chart improvements. 23/23 source tests, frontend/native builds, Windows NSIS install and running-backend reinstall tests passed. Live Roblox injection and end-user GPU/WebView2 flicker were not tested in CI.

ZFLAG v2.0.47: verified per-flag native result counts classify a mixed FastFlag batch as partial success, not a total 'Inject failed' error. The editor still displays which flags failed. Matched matte Inject/Editor/Agent/Library/Settings controls. Windows CI passed 29 source regressions, native and frontend builds, and installed-app/upgrade smoke tests. In-game effect and GPU-specific rendering issues are not verified by CI.

ZFLAG 2.0.47: The native engine writes flushed per-flag result checkpoints. After a timeout or lost final native report, the backend can recover validated native write acknowledgements, report the number that failed, and mark unprocessed flags unconfirmed. The browser's wait budget scales with batch size rather than ending at the old 90-second cutoff. Windows build: 34 tests passing, successful frontend/native compilation and install/upgrade smoke tests. Actual in-game effect and user-specific graphics issues remain unverified.

ZFLAG 2.0.47: Inject, Home injection shortcut, and Apply Supported controls now use a clear syringe icon instead of a generic Play triangle. 36 source tests passed, frontend/native engines built, installer and live-backend upgrade tests passed. Existing injection result logic preserved; live Roblox injection remains outside CI verification.

ZFLAG v2.0.47: Settings → General now has a one-click built-in updater that checks the latest stable official GitHub release, downloads and verifies its SHA-256, installs silently via a detached helper, then reopens ZFLAG. Existing local settings/flag data remain intact. The Editor toolbar flex-wraps rather than clipping the Inject control in narrow windows. Windows runner: 46 passing tests, frontend/native compilation, updater endpoint security check, fresh install, and reinstall while backend was running. A real cross-release update and GPU rendering at a user's display size have not been independently tested.



