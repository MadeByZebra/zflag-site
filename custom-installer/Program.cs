using System;
using System.Diagnostics;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Effects;
using System.Windows.Media.Imaging;
using System.Windows.Threading;

namespace ZFLAG.Setup;

internal static class Program
{
    [STAThread]
    private static int Main(string[] args)
    {
        if (args.Length > 0 && args[0] == "--verify")
        {
            try { InstallEngine.VerifyEmbeddedPayload(); return 0; }
            catch (Exception e) { Debug.WriteLine(e); return 2; }
        }
        if (args.Length > 1 && args[0] == "--qa-install")
        {
            try
            {
                InstallEngine.Install(args[1], false, false, null, CancellationToken.None);
                return InstallEngine.VerifyInstalledFiles(args[1]) ? 0 : 3;
            }
            catch (Exception e) { Debug.WriteLine(e); return 4; }
        }

        var guiTest = args.Length > 0 && args[0] == "--qa-gui-install";
        var app = new Application { ShutdownMode = ShutdownMode.OnMainWindowClose };
        app.Run(new InstallerWindow(args.Length > 0 && args[0] == "--uninstall", guiTest));
        return Environment.ExitCode;
    }
}

internal sealed class InstallerWindow : Window
{
    private static readonly SolidColorBrush Ink = Brush("#E7EDF7");
    private static readonly SolidColorBrush Muted = Brush("#919CAC");
    private static readonly SolidColorBrush Dim = Brush("#647185");
    private static readonly SolidColorBrush Accent = Brush("#DBE8FF");
    private static readonly SolidColorBrush Pane = Brush("#171D28");
    private static readonly SolidColorBrush PaneBorder = Brush("#313A4C");
    private const string SubtleBlue = "#94B3EA";
    private readonly bool _uninstall;
    private readonly bool _guiTest;
    private readonly string _installPath;
    private readonly TextBlock _headline;
    private readonly TextBlock _subline;
    private readonly TextBlock _stage;
    private readonly TextBlock _percent;
    private readonly TextBlock _details;
    private readonly ProgressBar _progress;
    private readonly CheckBox _desktopShortcut;
    private readonly Button _primary;
    private readonly Button _secondary;
    private readonly Button _launch;
    private readonly Button _folder;
    private CancellationTokenSource? _cancel;
    private bool _busy;
    private bool _finished;
    private bool _closeWhenDone;
    private readonly DispatcherTimer _pulse;
    private string _baseStage = "Waiting to begin";
    private int _dots;

    private static SolidColorBrush Brush(string hex) => new((Color)ColorConverter.ConvertFromString(hex));
    private static TextBlock Text(string value, double size, Brush color, FontWeight? weight = null)
        => new() { Text = value, FontFamily = new FontFamily("Segoe UI"), FontSize = size,
                   Foreground = color, FontWeight = weight ?? FontWeights.Normal,
                   VerticalAlignment = VerticalAlignment.Center };
    private static Border Rounded(Brush bg, double radius, Brush? stroke = null, double thickness = 0)
        => new() { Background = bg, CornerRadius = new CornerRadius(radius),
                   BorderBrush = stroke ?? Brushes.Transparent, BorderThickness = new Thickness(thickness) };

    private static Button ActionButton(string title, bool main, double width)
    {
        var b = new Button {
            Content = title, Width = width, Height = 43, Cursor = Cursors.Hand,
            Background = main ? Accent : Brush("#232B3A"), Foreground = main ? Brush("#0D1522") : Ink,
            FontSize = 12, FontWeight = FontWeights.SemiBold, BorderThickness = new Thickness(0),
            HorizontalAlignment = HorizontalAlignment.Right,
        };
        var template = new ControlTemplate(typeof(Button));
        var border = new FrameworkElementFactory(typeof(Border));
        border.SetValue(Border.CornerRadiusProperty, new CornerRadius(11));
        border.SetValue(Border.BackgroundProperty, new System.Windows.Data.Binding("Background") { RelativeSource = System.Windows.Data.RelativeSource.TemplatedParent });
        border.SetValue(Border.SnapsToDevicePixelsProperty, true);
        var present = new FrameworkElementFactory(typeof(ContentPresenter));
        present.SetValue(FrameworkElement.HorizontalAlignmentProperty, HorizontalAlignment.Center);
        present.SetValue(FrameworkElement.VerticalAlignmentProperty, VerticalAlignment.Center);
        border.AppendChild(present);
        template.VisualTree = border;
        b.Template = template;
        b.MouseEnter += (_, _) => { if (b.IsEnabled) b.Opacity = .83; };
        b.MouseLeave += (_, _) => b.Opacity = 1;
        return b;
    }

    internal InstallerWindow(bool uninstall, bool guiTest = false)
    {
        _uninstall = uninstall;
        _guiTest = guiTest;
        _installPath = InstallEngine.InstallDirectory;
        Title = uninstall ? "ZFLAG Uninstaller" : "ZFLAG Installer";
        Width = 735; Height = 545; MinWidth = 735; MinHeight = 545;
        WindowStartupLocation = WindowStartupLocation.CenterScreen;
        WindowStyle = WindowStyle.None;
        ResizeMode = ResizeMode.NoResize;
        AllowsTransparency = true;
        Background = Brushes.Transparent;
        ShowInTaskbar = true;
        try { Icon = BitmapFrame.Create(new Uri("pack://application:,,,/Assets/zflag-logo.png")); } catch { }
        Closing += (_, e) =>
        {
            if (_busy)
            {
                e.Cancel = true;
                _closeWhenDone = true;
                _cancel?.Cancel();
                _stage.Text = "Cancelling safely…";
            }
        };

        var shell = Rounded(new LinearGradientBrush(
            (Color)ColorConverter.ConvertFromString("#111722"),
            (Color)ColorConverter.ConvertFromString("#0B1018"), 118), 22, Brush("#344054"), 1);
        shell.Effect = new DropShadowEffect { Color = Colors.Black, BlurRadius = 28, ShadowDepth = 7, Opacity = .32 };
        Content = shell;
        var frame = new Grid { Margin = new Thickness(33, 18, 33, 25) };
        frame.RowDefinitions.Add(new RowDefinition { Height = new GridLength(52) });
        frame.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
        frame.RowDefinitions.Add(new RowDefinition { Height = new GridLength(80) });
        shell.Child = frame;

        // Custom brand bar: the installer never opens a PowerShell or console window.
        var top = new Grid { Background = Brushes.Transparent, Cursor = Cursors.Hand };
        top.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        top.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        Grid.SetRow(top, 0); frame.Children.Add(top);
        var brand = new StackPanel { Orientation = Orientation.Horizontal, VerticalAlignment = VerticalAlignment.Center };
        var logo = new Image { Width = 32, Height = 32, Margin = new Thickness(0, 0, 11, 0) };
        logo.Source = new BitmapImage(new Uri("pack://application:,,,/Assets/zflag-logo.png"));
        brand.Children.Add(logo);
        brand.Children.Add(Text("ZFLAG", 15, Ink, FontWeights.Bold));
        brand.Children.Add(new Border {
            Width = 1, Height = 15, Background = PaneBorder,
            Margin = new Thickness(14, 0, 12, 0) });
        brand.Children.Add(Text(uninstall ? "UNINSTALLER" : "INSTALLER", 10, Muted, FontWeights.SemiBold));
        top.Children.Add(brand);
        // Capture title-bar mouse-down before nested text and panels handle it.
        // Buttons remain clickable; all blank and branded header space is draggable.
        top.PreviewMouseLeftButtonDown += (_, e) =>
        {
            if (e.ChangedButton != MouseButton.Left || e.ClickCount != 1) return;
            DependencyObject? hit = e.OriginalSource as DependencyObject;
            while (hit != null && hit != top)
            {
                if (hit is Button) return;
                hit = hit is Visual ? VisualTreeHelper.GetParent(hit) : null;
            }
            try { DragMove(); e.Handled = true; }
            catch (InvalidOperationException) { /* mouse released before dragging */ }
        };
        KeyDown += (_, e) => {
            if (e.Key == Key.Escape) { Close(); e.Handled = true; }
        };
        var buttons = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right };
        Grid.SetColumn(buttons, 1); top.Children.Add(buttons);
        buttons.Children.Add(Text("2.0.32   •   TEST BUILD", 10, Dim, FontWeights.SemiBold));
        var minimize = ActionButton("—", false, 32);
        minimize.Height = 29; minimize.Margin = new Thickness(18, 0, 7, 0);
        minimize.Click += (_, _) => WindowState = WindowState.Minimized;
        buttons.Children.Add(minimize);
        var close = ActionButton("×", false, 32); close.Height = 29; close.FontSize = 18;
        close.Click += (_, _) => Close(); buttons.Children.Add(close);

        var body = new StackPanel { Margin = new Thickness(5, 22, 5, 0) };
        Grid.SetRow(body, 1); frame.Children.Add(body);
        var chip = Rounded(Brush("#253248"), 10);
        chip.HorizontalAlignment = HorizontalAlignment.Left;
        chip.Padding = new Thickness(12, 6, 12, 6);
        chip.Child = Text(uninstall ? "SAFE CLEANUP • YOUR SETTINGS ARE KEPT" : "WINDOWS 10/11   •   X64", 10, Brush(SubtleBlue), FontWeights.SemiBold);
        body.Children.Add(chip);

        _headline = Text(uninstall ? "Remove the preview." : "Install ZFLAG", 31, Ink, FontWeights.Bold);
        _headline.Margin = new Thickness(0, 17, 0, 6);
        body.Children.Add(_headline);
        _subline = Text(uninstall ? "Remove this ZFLAG preview without touching your Roblox or other ZFLAG installations."
                                  : "Everything you need, in one installer. No terminal or developer tools.",
                        12.5, Muted);
        _subline.TextWrapping = TextWrapping.Wrap;
        body.Children.Add(_subline);

        var product = Rounded(Pane, 15, PaneBorder, 1);
        product.Padding = new Thickness(18, 15, 18, 15);
        product.Margin = new Thickness(0, 25, 0, 23);
        body.Children.Add(product);
        var productGrid = new Grid();
        productGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        productGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        productGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        product.Child = productGrid;
        var productLogo = new Image { Width = 46, Height = 46, Source = logo.Source };
        productGrid.Children.Add(productLogo);
        var productName = new StackPanel { Margin = new Thickness(14, 0, 0, 0), VerticalAlignment = VerticalAlignment.Center };
        productName.Children.Add(Text("ZFLAG Desktop", 15, Ink, FontWeights.SemiBold));
        var desc = Text("FastFlag Studio   /   Editor + presets", 11, Muted);
        desc.Margin = new Thickness(0, 4, 0, 0); productName.Children.Add(desc);
        Grid.SetColumn(productName, 1); productGrid.Children.Add(productName);
        var productTag = Text("STABILITY BUILD 2.0.30", 10, Brush(SubtleBlue), FontWeights.SemiBold);
        Grid.SetColumn(productTag, 2); productGrid.Children.Add(productTag);

        var progressHeading = new Grid();
        progressHeading.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        progressHeading.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        _stage = Text("Ready to install", 12, Ink, FontWeights.SemiBold);
        _percent = Text("0%", 12, Muted, FontWeights.SemiBold);
        progressHeading.Children.Add(_stage); Grid.SetColumn(_percent, 1); progressHeading.Children.Add(_percent);
        body.Children.Add(progressHeading);
        _progress = new ProgressBar { Minimum = 0, Maximum = 100, Value = 0, Height = 9, Margin = new Thickness(0, 12, 0, 11), Background = Brush("#273246"), Foreground = Brush("#CFDFFF"), BorderThickness = new Thickness(0) };
        var progressTemplate = new ControlTemplate(typeof(ProgressBar));
        var progressGrid = new FrameworkElementFactory(typeof(Grid));
        progressGrid.SetValue(FrameworkElement.HeightProperty, 9.0);
        var track = new FrameworkElementFactory(typeof(Border));
        track.Name = "PART_Track";
        track.SetValue(Border.BackgroundProperty, Brush("#283142"));
        track.SetValue(Border.CornerRadiusProperty, new CornerRadius(5));
        progressGrid.AppendChild(track);
        var indicator = new FrameworkElementFactory(typeof(Border));
        indicator.Name = "PART_Indicator";
        indicator.SetValue(Border.BackgroundProperty, new LinearGradientBrush(Brush("#91B5F8").Color, Brush("#DFEAFF").Color, 0));
        indicator.SetValue(Border.CornerRadiusProperty, new CornerRadius(5));
        indicator.SetValue(FrameworkElement.HorizontalAlignmentProperty, HorizontalAlignment.Left);
        progressGrid.AppendChild(indicator);
        progressTemplate.VisualTree = progressGrid;
        _progress.Template = progressTemplate;
        body.Children.Add(_progress);
        _details = Text("DESTINATION   " + _installPath, 10, Dim);
        _details.TextTrimming = TextTrimming.CharacterEllipsis;
        body.Children.Add(_details);

        var footer = new Grid { Margin = new Thickness(5, 12, 5, 0) };
        footer.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        footer.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        Grid.SetRow(footer, 2); frame.Children.Add(footer);
        var options = new StackPanel { VerticalAlignment = VerticalAlignment.Center };
        _desktopShortcut = new CheckBox {
            Content = "Create desktop shortcut", IsChecked = true,
            FontFamily = new FontFamily("Segoe UI"), FontSize = 12, Foreground = Muted,
            Margin = new Thickness(0, 0, 0, 9) };
        options.Children.Add(_desktopShortcut);
        options.Children.Add(Text("Per-user setup   /   No administrator access", 10, Dim));
        footer.Children.Add(options);
        if (uninstall) _desktopShortcut.Visibility = Visibility.Collapsed;
        var actions = new StackPanel { Orientation = Orientation.Horizontal, VerticalAlignment = VerticalAlignment.Center };
        Grid.SetColumn(actions, 1); footer.Children.Add(actions);
        _secondary = ActionButton("Cancel", false, 105); _secondary.Margin = new Thickness(0, 0, 9, 0);
        _secondary.Click += (_, _) => {
            if (_busy) { _cancel?.Cancel(); _stage.Text = "Cancelling safely…"; }
            else Close();
        };
        actions.Children.Add(_secondary);
        _folder = ActionButton("Open folder", false, 112); _folder.Visibility = Visibility.Collapsed;
        _folder.Margin = new Thickness(0, 0, 9, 0);
        _folder.Click += (_, _) => {
            if (Directory.Exists(_installPath))
                Process.Start(new ProcessStartInfo("explorer.exe", "\"" + _installPath + "\"") { UseShellExecute = true });
        };
        actions.Children.Add(_folder);
        _launch = ActionButton("Launch ZFLAG", false, 120); _launch.Visibility = Visibility.Collapsed;
        _launch.Margin = new Thickness(0, 0, 9, 0);
        _launch.Click += (_, _) => Launch();
        actions.Children.Add(_launch);
        _primary = ActionButton(uninstall ? "Uninstall" : "Install ZFLAG", true, 146);
        System.Windows.Automation.AutomationProperties.SetAutomationId(_primary, "InstallZFLAG");
        _primary.Click += async (_, _) => {
            if (_finished) Close();
            else await BeginAsync();
        };
        actions.Children.Add(_primary);

        _pulse = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(390) };
        _pulse.Tick += (_, _) => { if (_busy) { _dots = (_dots + 1) % 4; _stage.Text = _baseStage + new string('.', _dots); } };
        if (_guiTest) Loaded += async (_, _) =>
        {
            // Exercise the same real WPF button click as an end-user.
            _primary.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            var until = DateTime.UtcNow.AddMinutes(3);
            while (_busy && DateTime.UtcNow < until) await Task.Delay(160);
            var exists = InstallEngine.VerifyInstalledFiles(_installPath);
            var shortcut = File.Exists(Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                "Microsoft", "Windows", "Start Menu", "Programs", "ZFLAG Studio Preview", "ZFLAG.lnk"));
            var success = _finished && exists && shortcut;
            Environment.ExitCode = success ? 0 : 51;
            if (!success) Console.Error.WriteLine("Real WPF Install click failed: " + _details.Text);
            Close();
        };
    }

    private async Task BeginAsync()
    {
        if (_busy) return;
        // Read UI-owned state before starting a worker. Reading the checkbox
        // in Task.Run caused the reported 0% cross-thread WPF exception.
        var createDesktopShortcut = _desktopShortcut.IsChecked == true;
        _stage.Foreground = Ink;
        _busy = true;
        _cancel = new CancellationTokenSource();
        _primary.IsEnabled = false;
        _desktopShortcut.IsEnabled = false;
        _baseStage = "Preparing";
        _pulse.Start();
        var progress = new Progress<InstallProgress>(p => {
            _baseStage = p.Message;
            _stage.Text = p.Message;
            _percent.Text = ((int)Math.Round(p.Percent)).ToString() + "%";
            _progress.Value = Math.Clamp(p.Percent, 0, 100);
            if (p.Percent >= 88 && _busy) { _secondary.IsEnabled = false; _secondary.Content = "Finalizing"; }
        });
        try
        {
            if (_uninstall)
                await Task.Run(() => InstallEngine.Uninstall(progress, _cancel.Token));
            else
                await Task.Run(() => InstallEngine.Install(_installPath, true, createDesktopShortcut, progress, _cancel.Token));
            _pulse.Stop();
            _busy = false;
            _finished = true;
            _progress.Value = 100; _percent.Text = "100%";
            _stage.Text = _uninstall ? "Uninstallation completed" : "Installation completed";
            _headline.Text = _uninstall ? "ZFLAG preview removed." : "Installation complete";
            _subline.Text = _uninstall ? "Your Roblox and other ZFLAG files were not changed."
                                        : "ZFLAG is ready. Open it now or launch it later from Start.";
            _details.Text = _uninstall ? "A locked uninstall helper may finish cleanup after restart."
                                       : "Installed to " + _installPath;
            _secondary.Visibility = Visibility.Collapsed;
            _primary.Content = "Finish";
            _primary.IsEnabled = true;
            if (!_uninstall) { _launch.Visibility = Visibility.Visible; _folder.Visibility = Visibility.Visible; }
            if (_closeWhenDone) Close();
        }
        catch (OperationCanceledException)
        {
            _pulse.Stop(); _busy = false;
            _stage.Text = "Setup cancelled";
            _details.Text = "No incomplete installation was left behind.";
            _primary.IsEnabled = true;
            _primary.Content = _uninstall ? "Uninstall" : "Try again";
            _secondary.IsEnabled = true; _secondary.Content = "Close";
            _desktopShortcut.IsEnabled = true;
            if (_closeWhenDone) Close();
        }
        catch (Exception ex)
        {
            _pulse.Stop(); _busy = false;
            _stage.Text = "Couldn't complete setup";
            _stage.Foreground = Brush("#FF9EA9");
            _details.Text = ex.Message;
            _details.ToolTip = ex.ToString();
            _subline.Text = "Installation stopped. Check the error below, then try again.";
            _primary.IsEnabled = true;
            _primary.Content = "Retry";
            _secondary.IsEnabled = true; _secondary.Content = "Close";
            _desktopShortcut.IsEnabled = true;
            if (_closeWhenDone) Close();
        }
    }

    private void Launch()
    {
        try
        {
            var exe = Path.Combine(_installPath, "fflag-studio.exe");
            if (!File.Exists(exe)) throw new FileNotFoundException("ZFLAG executable is missing.", exe);
            Process.Start(new ProcessStartInfo(exe) { WorkingDirectory = _installPath, UseShellExecute = true });
            Close();
        }
        catch (Exception ex) { _details.Text = "Launch failed: " + ex.Message; _details.Foreground = Brush("#FF9EA9"); }
    }
}
