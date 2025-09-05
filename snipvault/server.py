# C:\Users\baket\code\m3-snipvault\snipvault\server.py
from __future__ import annotations
import json
import argparse
import logging
import threading
from logging.handlers import RotatingFileHandler
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from typing import Tuple, List, Dict

ROOT = Path(__file__).parents[1]
WEB_DIR = ROOT / "web"
LOG_DIR = ROOT / "logs"
DATA_DIR = ROOT / "data"
LOG_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

MAX_BYTES = 256_000
BACKUPS = 3

_logger = logging.getLogger("snipvault")
_logger.setLevel(logging.INFO)
_log_file = LOG_DIR / "web.log"
_handler = RotatingFileHandler(_log_file, maxBytes=MAX_BYTES, backupCount=BACKUPS, encoding="utf-8")
_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
_logger.addHandler(_handler)

def _log_info(msg: str, *args) -> None:
    _logger.info(msg, *args)

Task = Dict[str, object]

def _load_db(db_path: Path) -> List[Task]:
    if not db_path.exists() or db_path.stat().st_size == 0:
        return []
    with db_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []

def _save_db(db_path: Path, tasks: List[Task]) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with db_path.open("w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)

def _next_id(tasks: List[Task]) -> int:
    return (max((int(t.get("id", 0)) for t in tasks), default=0) + 1)

class AppHandler(SimpleHTTPRequestHandler):
    DB_PATH: Path = DATA_DIR / "snips.json"  # set by make_server()

    def log_message(self, fmt: str, *args) -> None:
        _log_info("%s - " + fmt, self.address_string(), *args)

    # Serve static files from /web; root -> index.html
    def translate_path(self, path: str) -> str:
        if path == "/":
            path = "/index.html"
        return str(WEB_DIR / path.lstrip("/"))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        # GET /api/snips/<id> -> JSON
        if path.startswith("/api/snips/"):
            snip_id = path.rsplit("/", 1)[-1]
            try:
                iid = int(snip_id)
            except ValueError:
                self.send_error(404); return
            tasks = _load_db(self.DB_PATH)
            for t in tasks:
                if int(t.get("id", -1)) == iid:
                    data = json.dumps(t).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
            self.send_error(404); return

        # GET /s/<id> -> simple HTML page showing snippet
        if path.startswith("/s/"):
            snip_id = path.rsplit("/", 1)[-1]
            try:
                iid = int(snip_id)
            except ValueError:
                self.send_error(404); return
            tasks = _load_db(self.DB_PATH)
            for t in tasks:
                if int(t.get("id", -1)) == iid:
                    body = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Snip {iid}</title></head>
<body><h1>Snip {iid}</h1><pre>{t.get("text","")}</pre></body></html>"""
                    data = body.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
            self.send_error(404); return

        # Otherwise serve static (/, /styles.css, /app.js, ...)
        super().do_GET()

    # POST /api/snips  (form field: text=...)
    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/snips":
            self.send_error(404); return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        form = parse_qs(raw)
        text = (form.get("text") or [""])[0]

        tasks = _load_db(self.DB_PATH)
        new = {"id": _next_id(tasks), "text": text}
        tasks.append(new)
        _save_db(self.DB_PATH, tasks)

        data = json.dumps(new).encode("utf-8")
        self.send_response(201)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

def make_server(host: str = "127.0.0.1", port: int = 8000, db: Path | None = None) -> Tuple[HTTPServer, int]:
    if db is None:
        db = DATA_DIR / "snips.json"
    AppHandler.DB_PATH = db
    httpd = HTTPServer((host, port), AppHandler)
    return httpd, httpd.server_port

def run(blocking: bool = True, host: str = "127.0.0.1", port: int = 8000, db: str | None = None):
    httpd, port = make_server(host=host, port=port, db=Path(db) if db else None)
    if blocking:
        print(f"Serving on http://{host}:{port}")
        httpd.serve_forever()
    else:
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        return httpd, port, t

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="snipvault", description="Tiny stdlib pastebin")
    p.add_argument("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    p.add_argument("--port", default=8000, type=int, help="Port (default: 8000)")
    p.add_argument("--db", default=str(DATA_DIR / "snips.json"), help="Path to JSON DB")
    return p

if __name__ == "__main__":
    args = _build_parser().parse_args()
    raise SystemExit(run(blocking=True, host=args.host, port=args.port, db=args.db))
