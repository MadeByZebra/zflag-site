# ZFLAG Native FastFlag Compatibility — November 21, 2026

## Finding: ZFLAG v2.0.65 does not prove current Roblox memory injection

**Known failure path:** The packaged enhanced native C++ engine contains a `FVAR_CONTAINER_NOT_FOUND` diagnostic: `FastFlag container not found in memory` (in `native-enhanced/fastflag_injector_gui_enhanced.cpp`). The shipping v2.0.65 integration deliberately treats that result as `native_incompatible` for a given Roblox process ID and stops repeating expensive scans.

This differs from a failure to detect Roblox, to open a process, or to save local configuration. A green **process detected** indicator is not proof that a FastFlag was written or honored.

**Source audit:** [read-only audit workflow](https://github.com/MadeByZebra/zflag-site/actions/runs/44878841484) succeeded on November 21, 2026. It validated the existing ZFLAG source archive SHA-256 `6ed33023f232918b0fc3d3191c3a8264a99ff2bed95b30755b19f223f155fd9e`, inspected 119 archived entries, and confirmed the original C++ scanner and its missing-container failure.

## The proposed `omg` replacement is NOT editable source

- Upstream tag: https://github.com/davelovestars/oldinjector-version-working/releases/tag/omg
- The tag tree (as checked November 21, 2026) consists of a single `fastflag_injector_gui_enhanced.exe`, **273,920 bytes**. No `.cpp`, `.h`, `.py`, `.rs`, build definition, or LICENSE was present.
- The GitHub release separately contains a **313,856-byte** EXE, with publisher-reported SHA-256 `418a52fe128b6cf3e8fe66142527dbf502512034817e1bec6e0eb21e32ee0249`.
- The two EXEs are **different-size binary artifacts**. Neither has been sandbox-executed, malware-scanned, source-matched, or tested against a live Windows Roblox client here. This audit does not establish either is safe or works.
- Third-party compiled code must not be repackaged as `ZFLAG_Setup.exe` or redistributed for sale without permission and reproducible verification.

## Product-safe path to functionality

1. In ZFLAG v2.0.65, watch the **native compatibility** readout after a controlled test on the currently installed Roblox client. If the native FastFlag container is unavailable, stop retrying large batches.
2. For Roblox-approved local settings, use **Stage safe config** (or `safe_config/zflag_supported_config.py` for maintainers) to write only known allowlisted values to `ClientSettings/ClientAppSettings.json`. It verifies the written file, backs up existing settings and requires a Roblox restart. This is **not injection** and does not guarantee Roblox will honor every chosen value.
3. Preserve failed/success/unsupported/unverified results separately. A file write is not proof of live client effect.
4. Only replace the native engine after obtaining editable upstream code and redistribution permission, auditing the native operations, compiling independently, and running controlled Windows/Roblox compatibility checks without disabling security protections.
5. Only release an installer after signed or at least checksum-verified distributables, reproducible builds, Windows smoke tests and human acceptance. No automatic shipping of an unverified third-party EXE.

Roblox's [official September 2025 FastFlag allowlist notice](https://devforum.roblox.com/t/allowlist-for-local-client-configuration-via-fast-flags/3966569) limits the supported local overrides; [Roblox staff explicitly warned about editing FFlags in memory](https://devforum.roblox.com/t/allowlist-for-local-client-configuration-via-fast-flags/3966569/271), including possible account enforcement.

## Website / download status

Do **not** change the paid ZFLAG product to `available` or attach the upstream `omg` executable as its protected download while unverified. The existing ZFLAG access page correctly states that a verified protected installer is not available. Replacing the landing-page button does not make the binary functional. The current direct public legacy GitHub assets also need separate release retirement if the seller intends paid-only distribution.

**What is verified:** project source and metadata inspection, bundled-source hash, static scanner diagnostics.

**What is not verified:** live native FastFlag injection, Windows behavior of the upstream EXE, Roblox compatibility, executable redistribution rights, antivirus outcomes, and paid installer delivery.
