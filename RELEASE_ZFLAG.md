# ZFLAG one-click EXE distribution

The public website is designed for **Download → ZFLAG_Setup.exe → Install → Open**. Visitors never run scripts, extract ZIPs, or install developer tools.

## Release source (maintainer action only)

The Windows builder is at [`.github/workflows/build-zflag-windows.yml`](.github/workflows/build-zflag-windows.yml).

The GitHub repository needs an archive called `zflag-desktop-source.zip` in its top level. The ZIP must contain a `ZFLAG-Studio/` directory with the desktop project and release tests. Upload or replace the archive by using GitHub's `Add file → Upload files` interface. GitHub automatically runs the Windows build and tests on upload.

* The build compiles the frontend, original enhanced native C++ FastFlag engine and Python sidecar.
* It packages a self-contained branded NSIS installer and verifies the native command-line error result.
* Windows tests silently install it, check the bundled backend, replace stale ZFLAG shortcuts, verify new desktop/Start Menu shortcuts, and confirm the installed app starts its own backend process.
* Only after tests pass does it publish **ZFLAG_Setup.exe** and a SHA256 checksum as release `v2.0.40`.

The website automatically offers that published release EXE and keeps the older installer available in the meantime.

**Important:** these checks verify packaging, installation and engine wiring. A real Windows Roblox session is still needed to verify that the current game's flags can actually be modified. Do not advertise all imported FastFlags as supported.

## Important boundary

The zip file is *maintainer source* and is not the public download. Users should get only `ZFLAG_Setup.exe` (optional checksum separately). Do not link the source ZIP from the download button.

Unsigned EXE releases may trigger Windows SmartScreen. Code signing is recommended before broad distribution.
