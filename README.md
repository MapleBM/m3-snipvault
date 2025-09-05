\# m3-snipvault



Tiny stdlib pastebin:

\- POST `/api/snips` with form `text=...` → `{"id":1,"text":"..."}` (201 Created)

\- GET `/api/snips/<id>` → JSON snippet

\- GET `/s/<id>` → HTML page for sharing



\## Run (Windows, PowerShell)

```powershell

\# from project root with venv active

python ".\\snipvault\\server.py" --host 127.0.0.1 --port 8000 --db ".\\data\\snips.json"



