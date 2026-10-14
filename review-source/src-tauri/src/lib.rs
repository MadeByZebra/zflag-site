use tauri::{
    menu::{MenuBuilder, MenuItemBuilder},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    AppHandle, Emitter, Manager, WindowEvent,
};


#[tauri::command]
fn open_default_browser(url: String) -> Result<(), String> {
    let allowed = url.starts_with("http://127.0.0.1:") || url.starts_with("http://localhost:");
    if !allowed {
        return Err("Only local ZFLAG browser URLs are allowed".to_string());
    }

    #[cfg(target_os = "windows")]
    {
        use std::{
            ffi::{c_void, OsStr},
            os::windows::ffi::OsStrExt,
            ptr,
        };

        #[link(name = "shell32")]
        extern "system" {
            fn ShellExecuteW(
                hwnd: *mut c_void,
                operation: *const u16,
                file: *const u16,
                parameters: *const u16,
                directory: *const u16,
                show_cmd: i32,
            ) -> isize;
        }

        let operation: Vec<u16> = OsStr::new("open").encode_wide().chain(Some(0)).collect();
        let target: Vec<u16> = OsStr::new(&url).encode_wide().chain(Some(0)).collect();

        let result = unsafe {
            ShellExecuteW(
                ptr::null_mut(),
                operation.as_ptr(),
                target.as_ptr(),
                ptr::null(),
                ptr::null(),
                1,
            )
        };

        if result <= 32 {
            return Err(format!("Windows ShellExecute failed with code {result}"));
        }
        return Ok(());
    }

    #[cfg(not(target_os = "windows"))]
    {
        let _ = url;
        Err("ZFLAG browser launching is currently supported on Windows only".to_string())
    }
}

fn show_main_window(app: &AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.show();
        let _ = window.unminimize();
        let _ = window.set_focus();
    }
}

fn show_and_emit(app: &AppHandle, action: &str) {
    show_main_window(app);
    let _ = app.emit("tray-action", action.to_string());
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![open_default_browser])
        .setup(|app| {
            let show_item = MenuItemBuilder::with_id("show", "Show ZFLAG").build(app)?;
            let editor_item = MenuItemBuilder::with_id("editor", "Open Editor").build(app)?;
            let agent_item = MenuItemBuilder::with_id("agent", "Open AI Agent").build(app)?;
            let apply_item = MenuItemBuilder::with_id("apply", "Save Allowed Config").build(app)?;
            let refresh_item = MenuItemBuilder::with_id("refresh", "Refresh Status").build(app)?;
            let quit_item = MenuItemBuilder::with_id("quit", "Quit").build(app)?;
            let menu = MenuBuilder::new(app)
                .item(&show_item)
                .item(&editor_item)
                .item(&agent_item)
                .separator()
                .item(&apply_item)
                .item(&refresh_item)
                .separator()
                .item(&quit_item)
                .build()?;

            let app_icon = app.default_window_icon().cloned();

            let mut tray = TrayIconBuilder::with_id("zflag-tray")
                .tooltip("ZFLAG • FFlag Studio")
                .show_menu_on_left_click(false)
                .menu(&menu)
                .on_menu_event(|app, event| match event.id().as_ref() {
                    "show" => show_main_window(app),
                    "editor" => show_and_emit(app, "editor"),
                    "agent" => show_and_emit(app, "agent"),
                    "apply" => show_and_emit(app, "apply"),
                    "refresh" => show_and_emit(app, "refresh"),
                    "quit" => app.exit(0),
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        show_main_window(tray.app_handle());
                    }
                });

            if let Some(icon) = app_icon {
                tray = tray.icon(icon);
            }

            let _ = tray.build(app)?;
            Ok(())
        })
        .on_window_event(|window, event| {
            if window.label() != "main" {
                return;
            }

            if let WindowEvent::CloseRequested { .. } = event {
                // Respect the X button: close completely, do not silently hide to tray.
                window.app_handle().exit(0);
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running ZFLAG");
}
