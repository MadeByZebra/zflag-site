# ZFLAG branded Windows bootstrapper — design and implementation plan

## Creative direction
A compact, polished Windows desktop loader rather than a browser-style setup builder, default PowerShell window, or generic NSIS wizard.

- **Window:** 735 × 545 px WPF, nonresizable, centered; 22 px rounded corners; subtle dark outer shadow.
- **Colors:** base dark blue-black #111722 -> #0B1018; surface #171D28; borders #313A4C; text #E7EDF7; muted #919CAC; pale ice-blue accent #DBE8FF.
- **Branding:** ZFLAG's actual white Z mark, dark rounded-square logo tile, and matching taskbar/install EXE icon.
- **Top row:** logo + ZFLAG / INSTALLER wordmark, discreet version label, minimize and close controls. Title bar is draggable.
- **Main heading:** "Your setup, reimagined." + one sentence. Device chip above and ZFLAG product tile underneath.
- **Progress region:** smooth pale-blue 9 px bar with status ("Checking installation package", "Extracting ZFLAG", "Installing backend", "Creating Windows shortcuts") and true byte-based percentage.
- **Bottom row:** optional desktop shortcut, default per-user install location, Cancel, primary Install ZFLAG.
- **Success state:** "You're all set." plus Launch ZFLAG, Open folder, Finish.
- **Failure state:** clear error message (not developer console); retry button; hover for detailed exception.
- **Uninstall state:** identical branding; clear removal scope and confirmation; keeps Roblox installations and user configs.

## Delivered implementation
| Source file | Responsibility |
| --- | --- |
| `ZFLAGBootstrapper.csproj` | .NET 8 single-file self-contained Windows WPF executable with embedded ZIP/icon. |
| `Program.cs` | Real interactive branded installer/uninstaller windows, cancel/close, progress and launch actions. |
| `InstallEngine.cs` | Per-user installation; atomic staging and backup; embedded ZIP validation; rollback; shortcuts; Windows Installed Apps uninstall entry. |
| `README.md` | Developer and test instructions, supported modes, safety limitations. |
| `.github/workflows/build-zflag-custom-bootstrapper.yml` | GitHub Windows build using vetted v2.0.30 stability executables; icon generation; embedded payload; binary/launch QA; artifact. |
| `.github/workflows/test-zflag-custom-installer-ui.yml` | Windows smoke test for full UI initialization and uninstaller window. |

## Install transaction
1. Open the EXE: no user-side node/npm/rust/python/PowerShell required.
2. Verify built-in payload contains the full app and both sidecars.
3. Check for an already-open ZFLAG app to avoid swapping files in use.
4. Extract to a same-volume staging folder, tracking actual decompressed bytes.
5. Verify executable sizes; copy self as branded uninstaller.
6. Atomically swap into `%LOCALAPPDATA%\ZFLAG Studio Preview`, retaining backup until completion.
7. Register uninstall under the *current user* and create Start menu/optional desktop shortcuts.
8. Show success. User chooses whether to launch.
9. On extraction failure, delete staging; on swap failure, restore the backed-up preview.
10. On uninstall, remove only this preview, not previous ZFLAG/Roblox installs. A locked uninstaller helper may require reboot to finish deletion.

## Quality gates
- Embedded ZIP integrity and required executables.
- App extraction to a clean, isolated directory.
- Five-second Windows ZFLAG startup smoke test.
- Separate smoke checks for the setup and uninstall WPF window.
- Real end-user install behavior, antivirus feedback, and game performance **still require user testing**.
- Windows installer is **unsigned**. A production release should receive Authenticode signing before broad distribution.
- The native memory scanner stays disabled in this preview because Roblox hangs/crashes were reported.
- **Do not publish this as a website update until the user verifies the preview.**

## Post-test release steps (not performed)
1. Obtain user acceptance on installer appearance, install behavior, app startup and safe Roblox detection.
2. Resolve and validate native injection performance separately, if supported and safe; don't bypass unsupported-client protections.
3. Freeze a release version and sign the installer.
4. Build a Windows release candidate, test install/uninstall/reinstall on clean and upgrade systems.
5. Only then update the ZFLAG site download URL and release notes.
