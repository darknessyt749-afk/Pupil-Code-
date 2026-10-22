# Pupil Code — Pupil AI
Windows-first desktop AI app: Tauri + React, FastAPI, Ollama local chat, Groq cloud chat, SQLite history, optional local image generation.

## Windows setup
Install Node.js 20+, Python 3.11+, Rust stable/MSVC build tools, WebView2, and Ollama. In PowerShell at this folder:
```powershell
.\scripts\setup_windows.ps1
ollama pull qwen2.5:0.5b
Copy-Item .env.example backend\.env
npm run dev
```
Edit `backend\.env` and set `GROQ_API_KEY` for Groq. Get a key from https://console.groq.com.

## Image generation
Optional and hardware-heavy. Install with:
```powershell
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements-image.txt
```
Set `IMAGE_MODEL_ID` to a compatible Diffusers model ID in `backend\.env`, restart backend, and use Image Studio. First run may download multiple GB of weights. No model is bundled.

## Windows build
Run `.\scriptsuild_exe.ps1` on Windows after installing prerequisites. This starter does not bundle Ollama or model weights. Test packaged backend startup/lifecycle before distribution.

Never commit API keys. Local Ollama requests stay on your PC; Groq requests leave your PC. Generated code is not executed.
