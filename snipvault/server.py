# C:\Users\baket\code\m3-snipvault\snipvault\server.py
from __future__ import annotations
import json
import argparse
import logging
import threading
import secrets
from datetime import datetime, timezone, timedelta
from logging.handlers import RotatingFileHandler
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from typing import Tuple, List, Dict, Optional

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
_handler = RotatingFileHandler(LOG_DIR / "web.log", maxBytes=MAX_BYTES, backupCount=BACKUPS, encoding="utf-8")
_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
_logger.addHandler(_handler)

def _log_info(msg: str, *args) -> None:
    _logger.info(msg, *args)

def _utcnow():
    return datetime.now(timezone.utc)

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

def _make_slug(existing: List[Task], length: int = 6) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    existing_ids = {str(t.get("id", "")) for t in existing}
    while True:
        slug = "".join(secrets.choice(alphabet) for _ in range(length))
        if slug not in existing_ids:
            return slug

def _is_expired(iso: Optional[str], ttl_seconds: int) -> bool:
    if not iso or ttl_seconds <= 0:
        return False
    try:
        created = datetime.fromisoformat(iso)
    except Exception:
        return False
    return (_utcnow() - created) > timedelta(seconds=ttl_seconds)

class AppHandler(SimpleHTTPRequestHandler):
    DB_PATH: Path = DATA_DIR / "snips.json"   # set by make_server()
    TTL_SECONDS: int = 0                      # 0 = never expire

    def log_message(self, fmt: str, *args) -> None:
        _log_info("%s - " + fmt, self.address_string(), *args)

    def translate_path(self, path: str) -> str:
        if path == "/":
            path = "/index.html"
        return str(WEB_DIR / path.lstrip("/"))

    def _find_snip(self, sid: str) -> Optional[Task]:
        for t in _load_db(self.DB_PATH):
            if str(t.get("id")) == sid:
                return t
        return None

    def _serve_json(self, payload: dict, status: int = 200) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        # GET /api/snips/<slug> → JSON (404 if expired/not found)
        if path.startswith("/api/snips/"):
            sid = path.rsplit("/", 1)[-1]
            snip = self._find_snip(sid)
            if not snip or _is_expired(snip.get("created_at"), self.TTL_SECONDS):
                self.send_error(404); return
            self._serve_json(snip); return

        # GET /s/<slug> → HTML (404 if expired/not found)
        if path.startswith("/s/"):
            sid = path.rsplit("/", 1)[-1]
            snip = self._find_snip(sid)
            if not snip or _is_expired(snip.get("created_at"), self.TTL_SECONDS):
                self.send_error(404); return
            body = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Snip {sid}</title></head>
<body><h1>Snip {sid}</h1><pre>{snip.get("text","")}</pre></body></html>"""
            data = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data); return

        # Otherwise static
        super().do_GET()

    # POST /api/snips (form: text=...)
    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/snips":
            self.send_error(404); return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        form = parse_qs(raw)
        text = (form.get("text") or [""])[0]

        tasks = _load_db(self.DB_PATH)
        slug = _make_slug(tasks)
        new = {"id": slug, "text": text, "created_at": _utcnow().isoformat()}
        tasks.append(new)
        _save_db(self.DB_PATH, tasks)

        self._serve_json(new, status=201)

def make_server(host: str = "127.0.0.1", port: int = 8000, db: Path | None = None, ttl_seconds: int = 0) -> Tuple[HTTPServer, int]:
    if db is None:
        db = DATA_DIR / "snips.json"
    AppHandler.DB_PATH = db
    AppHandler.TTL_SECONDS = int(ttl_seconds)
    httpd = HTTPServer((host, port), AppHandler)
    return httpd, httpd.server_port

def run(blocking: bool = True, host: str = "127.0.0.1", port: int = 8000, db: str | None = None, ttl_seconds: int = 0):
    httpd, port = make_server(host=host, port=port, db=Path(db) if db else None, ttl_seconds=ttl_seconds)
    if blocking:
        print(f"Serving on http://{host}:{port}")
        httpd.serve_forever()
    else:
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        return httpd, port, t

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="snipvault", description="Tiny stdlib pastebin")
    p.add_argument("--host", default="127.0.0.1", help="Host (default: 127.0.0.1)")
    p.add_argument("--port", default=8000, type=int, help="Port (default: 8000)")
    p.add_argument("--db", default=str(DATA_DIR / "snips.json"), help="Path to JSON DB")
    p.add_argument("--ttl-seconds", default=0, type=int, help="Expire snips older than N seconds (0 = never)")
    return p

if __name__ == "__main__":
    args = _build_parser().parse_args()
    raise SystemExit(run(blocking=True, host=args.host, port=args.port, db=args.db, ttl_seconds=args.ttl_seconds))
