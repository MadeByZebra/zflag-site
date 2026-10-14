using Microsoft.Win32;
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Threading;

namespace ZFLAG.Setup;

internal sealed record InstallProgress(double Percent, string Message);

internal static class InstallEngine
{
    private const string ResourceName = "ZFLAG.Setup.Payload";
    private const string UninstallKey = @"Software\Microsoft\Windows\CurrentVersion\Uninstall\ZFLAGStudioPreview";
    private const string GroupName = "ZFLAG Studio Preview";
    private static readonly string[] Required = { "fflag-studio.exe", "fflag-backend.exe", "zflag-native.exe" };

    internal static string InstallDirectory => Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), GroupName);

    private static string StartMenuFolder => Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
        "Microsoft", "Windows", "Start Menu", "Programs", GroupName);
    private static string DesktopLink => Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), "ZFLAG Studio Preview.lnk");

    private static Stream OpenPayload()
        => Assembly.GetExecutingAssembly().GetManifestResourceStream(ResourceName)
           ?? throw new InvalidOperationException("ZFLAG application payload was not embedded into this installer.");

    internal static void VerifyEmbeddedPayload()
    {
        using var input = OpenPayload();
        using var zip = new ZipArchive(input, ZipArchiveMode.Read, leaveOpen: false);
        var files = zip.Entries.Where(e => !string.IsNullOrEmpty(e.Name)).ToArray();
        if (files.Length < Required.Length)
            throw new InvalidDataException("The package is incomplete.");
        foreach (var required in Required)
        {
            var entry = files.FirstOrDefault(e => string.Equals(e.Name, required, StringComparison.OrdinalIgnoreCase));
            if (entry == null || entry.Length < 10_000)
                throw new InvalidDataException("ZFLAG installation payload is missing " + required);
        }
        foreach (var entry in files)
        {
            if (entry.FullName != entry.Name || entry.Name == "." || entry.Name == ".." ||
                entry.Name.IndexOfAny(new[] { '/', '\\', ':' }) >= 0)
                throw new InvalidDataException("Unsafe installer payload entry: " + entry.FullName);
        }
    }

    internal static bool VerifyInstalledFiles(string path)
        => Required.All(name => File.Exists(Path.Combine(path, name)) &&
                                  new FileInfo(Path.Combine(path, name)).Length > 10_000);

    internal static void Install(string destination, bool register, bool desktopShortcut,
        IProgress<InstallProgress>? progress, CancellationToken cancel)
    {
        string? staging = null;
        string? backup = null;
        bool promoted = false;
        bool succeeded = false;
        bool hadPriorVersion = false;
        try
        {
            Progress(2, "Checking installation package");
            VerifyEmbeddedPayload();
            cancel.ThrowIfCancellationRequested();
            var installPath = Path.GetFullPath(destination).TrimEnd(Path.DirectorySeparatorChar);
            // Preview installs are separate from older ZFLAG installations.
            // Only a process running FROM THIS destination can block replacement.
            // Other fflag-studio.exe processes must never prevent first-time install.
            if (register && Directory.Exists(installPath) && IsThisPreviewRunning(installPath))
                throw new IOException("Close ZFLAG Studio Preview (not your older ZFLAG) before updating this preview, then retry.");
            var parent = Directory.GetParent(installPath)?.FullName ??
                         throw new IOException("An installation directory is required.");
            Directory.CreateDirectory(parent);
            staging = installPath + ".staging-" + Guid.NewGuid().ToString("N");
            backup = installPath + ".backup-" + Guid.NewGuid().ToString("N");
            Directory.CreateDirectory(staging);
            Progress(8, "Preparing secure install area");
            cancel.ThrowIfCancellationRequested();

            using (var stream = OpenPayload())
            using (var zip = new ZipArchive(stream, ZipArchiveMode.Read))
            {
                var entries = zip.Entries.Where(e => !string.IsNullOrEmpty(e.Name)).ToArray();
                long total = entries.Sum(e => Math.Max(e.Length, 0));
                long done = 0;
                var buffer = new byte[128 * 1024];
                foreach (var entry in entries)
                {
                    cancel.ThrowIfCancellationRequested();
                    if (entry.FullName != entry.Name ||
                        entry.Name.IndexOfAny(new[] { '/', '\\', ':' }) >= 0)
                        throw new InvalidDataException("Unsafe ZIP entry rejected.");

                    Progress(10 + 70 * (total > 0 ? (double)done / total : 0),
                             entry.Name.Contains("backend", StringComparison.OrdinalIgnoreCase)
                                ? "Installing backend" : entry.Name.Contains("native", StringComparison.OrdinalIgnoreCase)
                                ? "Installing native component" : "Extracting ZFLAG");
                    var outputPath = Path.Combine(staging, entry.Name);
                    using var src = entry.Open();
                    using var output = new FileStream(outputPath, FileMode.CreateNew, FileAccess.Write, FileShare.None);
                    int read;
                    while ((read = src.Read(buffer, 0, buffer.Length)) > 0)
                    {
                        cancel.ThrowIfCancellationRequested();
                        output.Write(buffer, 0, read);
                        done += read;
                        Progress(10 + 70 * (total > 0 ? (double)done / total : 0), "Installing ZFLAG components");
                    }
                    output.Flush(true);
                    if (new FileInfo(outputPath).Length != entry.Length)
                        throw new InvalidDataException("Incomplete extraction: " + entry.Name);
                }
            }

            Progress(82, "Verifying application files");
            if (!VerifyInstalledFiles(staging))
                throw new InvalidDataException("The installed ZFLAG payload was incomplete.");

            if (register)
            {
                var setupPath = Environment.ProcessPath;
                if (string.IsNullOrWhiteSpace(setupPath) || !File.Exists(setupPath))
                    throw new IOException("Cannot locate the current ZFLAG installer for uninstall support.");
                File.Copy(setupPath, Path.Combine(staging, "Uninstall ZFLAG.exe"), overwrite: false);
            }
            cancel.ThrowIfCancellationRequested();

            // Commit atomically in the same parent directory. A bad extraction never
            // touches a previous install. Roll back a previous preview if commit fails.
            Progress(88, "Finishing installation");
            if (Directory.Exists(installPath))
            {
                Directory.Move(installPath, backup);
                hadPriorVersion = true;
            }
            Directory.Move(staging, installPath);
            promoted = true;
            staging = null;

            Progress(94, "Creating Windows shortcuts");
            if (register)
            {
                RegisterUninstaller(installPath);
                CreateShortcuts(installPath, desktopShortcut);
            }

            Progress(100, "Installation complete");
            succeeded = true;
        }
        catch
        {
            // Do not destroy existing user data; a failed preview update is restored.
            if (promoted)
            {
                TryDeleteDirectory(destination);
                if (hadPriorVersion && backup != null && Directory.Exists(backup))
                {
                    try { Directory.Move(backup, destination); }
                    catch { /* Preserve the backup on disk instead of deleting it. */ }
                }
            }
            else if (hadPriorVersion && backup != null && Directory.Exists(backup))
            {
                try { Directory.Move(backup, destination); }
                catch { /* Preserve the original data in its backup. */ }
            }
            throw;
        }
        finally
        {
            if (staging != null) TryDeleteDirectory(staging);
            if (succeeded && backup != null) TryDeleteDirectory(backup);
        }

        void Progress(double value, string message) => progress?.Report(new InstallProgress(value, message));
    }

    private static bool IsThisPreviewRunning(string installPath)
    {
        var wanted = Path.GetFullPath(Path.Combine(installPath, "fflag-studio.exe"));
        foreach (var process in Process.GetProcessesByName("fflag-studio"))
        {
            using (process)
            {
                try
                {
                    var actual = process.MainModule?.FileName;
                    if (actual != null && string.Equals(
                        Path.GetFullPath(actual), wanted, StringComparison.OrdinalIgnoreCase))
                        return true;
                }
                catch (System.ComponentModel.Win32Exception) { /* inaccessible other application */ }
                catch (InvalidOperationException) { /* process exited during inspection */ }
            }
        }
        return false;
    }

    private static void RegisterUninstaller(string dir)
    {
        using var key = Registry.CurrentUser.CreateSubKey(UninstallKey);
        if (key == null) throw new IOException("Couldn't register ZFLAG preview in Installed Apps.");
        key.SetValue("DisplayName", "ZFLAG Studio Preview", RegistryValueKind.String);
        key.SetValue("DisplayVersion", "2.0.38", RegistryValueKind.String);
        key.SetValue("Publisher", "Zebra", RegistryValueKind.String);
        key.SetValue("InstallLocation", dir, RegistryValueKind.String);
        key.SetValue("DisplayIcon", Path.Combine(dir, "fflag-studio.exe"), RegistryValueKind.String);
        key.SetValue("UninstallString", "\"" + Path.Combine(dir, "Uninstall ZFLAG.exe") + "\" --uninstall", RegistryValueKind.String);
        key.SetValue("NoModify", 1, RegistryValueKind.DWord);
        key.SetValue("NoRepair", 1, RegistryValueKind.DWord);
    }

    private static void CreateShortcuts(string root, bool makeDesktop)
    {
        Directory.CreateDirectory(StartMenuFolder);
        CreateShortcut(Path.Combine(StartMenuFolder, "ZFLAG.lnk"),
                       Path.Combine(root, "fflag-studio.exe"), root);
        CreateShortcut(Path.Combine(StartMenuFolder, "Uninstall ZFLAG.lnk"),
                       Path.Combine(root, "Uninstall ZFLAG.exe"), root, "--uninstall");
        if (makeDesktop)
            CreateShortcut(DesktopLink, Path.Combine(root, "fflag-studio.exe"), root);
        else if (File.Exists(DesktopLink))
            File.Delete(DesktopLink);
    }

    private static void CreateShortcut(string link, string executable, string workingDir, string args = "")
    {
        // WScript.Shell is a built-in Windows COM service, not a PowerShell/script process.
        var shellType = Type.GetTypeFromProgID("WScript.Shell") ??
                        throw new InvalidOperationException("Windows shortcut service is not available.");
        object? comObject = Activator.CreateInstance(shellType);
        if (comObject == null) throw new InvalidOperationException("Windows shortcut service didn't start.");
        try
        {
            dynamic shell = comObject;
            dynamic shortcut = shell.CreateShortcut(link);
            shortcut.TargetPath = executable;
            shortcut.WorkingDirectory = workingDir;
            shortcut.Arguments = args;
            shortcut.IconLocation = Path.Combine(workingDir, "fflag-studio.exe") + ",0";
            shortcut.Description = args.Length == 0 ? "Launch ZFLAG" : "Remove ZFLAG Studio Preview";
            shortcut.Save();
            if (Marshal.IsComObject(shortcut)) Marshal.FinalReleaseComObject(shortcut);
        }
        finally { if (Marshal.IsComObject(comObject)) Marshal.FinalReleaseComObject(comObject); }
    }

    internal static void Uninstall(IProgress<InstallProgress>? progress, CancellationToken token)
    {
        token.ThrowIfCancellationRequested();
        progress?.Report(new InstallProgress(8, "Checking installed files"));
        var installRoot = InstallDirectory;
        if (!Directory.Exists(installRoot))
            throw new DirectoryNotFoundException("ZFLAG Studio Preview is not installed in " + installRoot);
        progress?.Report(new InstallProgress(40, "Removing shortcuts"));
        if (Directory.Exists(StartMenuFolder)) TryDeleteDirectory(StartMenuFolder);
        if (File.Exists(DesktopLink)) { try { File.Delete(DesktopLink); } catch { } }
        progress?.Report(new InstallProgress(88, "Removing preview app files"));
        // Do not remove %LOCALAPPDATA%\\ZFLAG, the Roblox directory, or user presets.
        foreach (var file in Directory.GetFiles(installRoot, "*", SearchOption.AllDirectories))
        {
            try { File.Delete(file); }
            catch (IOException) { ScheduleRemoval(file); }
            catch (UnauthorizedAccessException) { ScheduleRemoval(file); }
        }
        foreach (var directory in Directory.GetDirectories(installRoot, "*", SearchOption.AllDirectories)
                   .OrderByDescending(path => path.Length))
        {
            try { Directory.Delete(directory); }
            catch (IOException) { ScheduleRemoval(directory); }
        }
        try { Directory.Delete(installRoot); }
        catch (IOException) { ScheduleRemoval(installRoot); }
        Registry.CurrentUser.DeleteSubKey(UninstallKey, throwOnMissingSubKey: false);
        progress?.Report(new InstallProgress(100, "Uninstall complete"));
    }

    private static void TryDeleteDirectory(string directory)
    {
        try { if (Directory.Exists(directory)) Directory.Delete(directory, recursive: true); }
        catch (IOException) { }
        catch (UnauthorizedAccessException) { }
    }

    private const int MOVEFILE_DELAY_UNTIL_REBOOT = 0x4;
    [DllImport("kernel32.dll", EntryPoint = "MoveFileExW", SetLastError = true, CharSet = CharSet.Unicode)]
    private static extern bool MoveFileEx(string existing, string? destination, int flags);
    private static void ScheduleRemoval(string path)
    {
        try { MoveFileEx(path, null, MOVEFILE_DELAY_UNTIL_REBOOT); } catch { }
    }
}
