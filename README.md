# m3-snipvault

A tiny stdlib pastebin you can demo in ~2 minutes.

## Run (Windows, PowerShell)
```powershell
# from project root with venv active
python ".\snipvault\server.py" --host 127.0.0.1 --port 8000 --db ".\data\snips.json"
# then open: http://127.0.0.1:8000
# API example (create):
# PowerShell:
curl -X POST -H "Content-Type: application/x-www-form-urlencoded" -d "text=Hello%20World" http://127.0.0.1:8000/api/snips
# Browser page for the snip:
# http://127.0.0.1:8000/s/1
