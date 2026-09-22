# ZFLAG website

Static ZFLAG site ready for Render.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/MadeByZebra/zflag-site)

Files:
- `index.html` — the full website
- `ZFLAG-Setup-v2.0.23.exe` — prebuilt Windows installer linked by every Download button

The installer is precompiled. End users do not need Node.js, Rust, Python, or Visual Studio Build Tools.
- `render.yaml` — Render Blueprint config

## Deploy

Click **Deploy to Render** above.

Render will read `render.yaml` from the repo root and create the static site. The installer stays beside `index.html`, and the Blueprint adds download headers for `/ZFLAG-Setup-v2.0.23.exe`.

After the first deploy, pushes to `main` can automatically redeploy the site.

