# ZFLAG v2.0.41 release patch; maintainer/CI only.
$ErrorActionPreference = 'Stop'
$root = Join-Path $PSScriptRoot '..\_work\ZFLAG-Studio'
$confPath = Join-Path $root 'src-tauri\tauri.conf.json'
$conf = Get-Content $confPath -Raw | ConvertFrom-Json
if ($conf.version -ne '2.0.40') { throw "Unexpected baseline version: $($conf.version)" }
$conf.version = '2.0.41'
$conf | ConvertTo-Json -Depth 64 | Set-Content -Encoding utf8 $confPath
$packagePath = Join-Path $root 'package.json'
$package = Get-Content $packagePath -Raw | ConvertFrom-Json
$package.version = '2.0.41'
$package | ConvertTo-Json -Depth 32 | Set-Content -Encoding utf8 $packagePath

$hookPath = Join-Path $root 'src-tauri\installer\zflag-shortcuts.nsh'
$hook = Get-Content $hookPath -Raw
if (-not $hook.Contains('!macro NSIS_HOOK_POSTINSTALL') -or $hook.Contains('!macro NSIS_HOOK_PREINSTALL')) {
  throw 'Unexpected NSIS hook source.'
}
$preinstall = @'
; Stop old ZFLAG instances before replacing locked installed executables.
; Closing the main window alone keeps the app alive in the tray.
!macro NSIS_HOOK_PREINSTALL
  DetailPrint "Stopping old ZFLAG app and backend processes..."
  nsExec::ExecToLog '"$SYSDIR\taskkill.exe" /F /T /IM fflag-studio.exe'
  nsExec::ExecToLog '"$SYSDIR\taskkill.exe" /F /T /IM fflag-backend.exe'
  nsExec::ExecToLog '"$SYSDIR\taskkill.exe" /F /T /IM fflag-backend-x86_64-pc-windows-msvc.exe'
  nsExec::ExecToLog '"$SYSDIR\taskkill.exe" /F /T /IM zflag-enhanced-injector.exe'
  Sleep 1400
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  nsExec::ExecToLog '"$SYSDIR\taskkill.exe" /F /T /IM fflag-studio.exe'
  nsExec::ExecToLog '"$SYSDIR\taskkill.exe" /F /T /IM fflag-backend.exe'
  nsExec::ExecToLog '"$SYSDIR\taskkill.exe" /F /T /IM fflag-backend-x86_64-pc-windows-msvc.exe'
  Sleep 900
!macroend

'@
Set-Content -LiteralPath $hookPath -Value ($preinstall + $hook) -Encoding utf8

$testPath = Join-Path $root 'scripts\smoke-test-installed-app.ps1'
$test = Get-Content $testPath -Raw
$marker = "  Write-Host 'PASS: fresh silent install; old shortcuts removed; installed shortcuts correct; backend is from installed path' -ForegroundColor Green"
if (-not $test.Contains($marker)) { throw 'Installer smoke test anchor changed.' }
$upgradeTest = @'
  Write-Host 'Checking reinstall with ZFLAG GUI and backend still running...' -ForegroundColor Yellow
  $previousPid = [int]$health.backendPid
  $up = Start-Process -FilePath $Installer -ArgumentList '/S' -PassThru -Wait
  if ($up.ExitCode -ne 0) { throw "Upgrade with active backend failed, exit: $($up.ExitCode)" }
  for ($n = 0; $n -lt 20; $n++) {
    if (-not (Get-Process -Id $previousPid -ErrorAction SilentlyContinue)) { break }
    Start-Sleep -Milliseconds 300
  }
  if (Get-Process -Id $previousPid -ErrorAction SilentlyContinue) {
    throw "Old ZFLAG backend PID $previousPid still alive after upgrade"
  }
  if (-not (Test-Path $exe) -or -not (Test-Path $short)) { throw 'GUI or shortcut missing after upgrade' }
  $uninstall = Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\ZFLAG' -ErrorAction Stop
  if ($uninstall.DisplayVersion -ne '2.0.41') { throw "Unexpected installed version after upgrade: $($uninstall.DisplayVersion)" }
  $appNew = Start-Process -FilePath $exe -PassThru
  $newBackendReady = $false
  try {
    for ($n = 0; $n -lt 30; $n++) {
      Start-Sleep -Milliseconds 800
      if ($appNew.HasExited) { throw "Upgraded GUI exited early: $($appNew.ExitCode)" }
      try {
        $statusNew = Invoke-RestMethod 'http://127.0.0.1:18765/status' -TimeoutSec 2
        if ($statusNew.enhancedAvailable -eq $true -and [int]$statusNew.backendPid -gt 0 -and [int]$statusNew.backendPid -ne $previousPid) {
          $procNew = Get-CimInstance Win32_Process -Filter "ProcessId=$($statusNew.backendPid)" -ErrorAction Stop
          $actualNew = [IO.Path]::GetFullPath($procNew.ExecutablePath)
          if (-not $actualNew.StartsWith(([IO.Path]::GetFullPath($installed) + '\'),[StringComparison]::OrdinalIgnoreCase)) {
            throw "New backend belongs to another install: $actualNew"
          }
          $newBackendReady = $true
          break
        }
      } catch { if ($_.Exception.Message -like '*another install*') { throw } }
    }
    if (-not $newBackendReady) { throw 'Upgraded backend failed to restart' }
    Write-Host 'PASS: upgraded while GUI/backend were running; locked backend replaced and relaunched' -ForegroundColor Green
  } finally {
    if (-not $appNew.HasExited) { Stop-Process -Id $appNew.Id -Force -ErrorAction SilentlyContinue }
    if ($newBackendReady) { Stop-Process -Id ([int]$statusNew.backendPid) -Force -ErrorAction SilentlyContinue }
  }
'@
Set-Content -LiteralPath $testPath -Value ($test.Replace($marker,$upgradeTest + [Environment]::NewLine + $marker)) -Encoding utf8
Write-Host 'ZFLAG v2.0.41 upgrade patch applied.'
