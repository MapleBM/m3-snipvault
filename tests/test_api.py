# C:\Users\baket\code\m3-snipvault\tests\test_api.py
import json, time, socket
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from pathlib import Path
import snipvault.server as app

def _port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

def _post(url, data):
    d = data.encode("utf-8")
    req = Request(url, data=d, headers={"Content-Type": "application/x-www-form-urlencoded"})
    return urlopen(req)

def test_create_and_get_snip(tmp_path):
    db = tmp_path / "snips.json"
    port = _port()
    httpd, _, t = app.run(blocking=False, port=port, db=str(db))
    try:
        time.sleep(0.05)
        with _post(f"http://127.0.0.1:{port}/api/snips", "text=hello") as r:
            assert r.status == 201
            created = json.loads(r.read().decode("utf-8"))
            assert created["id"] == 1 and created["text"] == "hello"

        with urlopen(f"http://127.0.0.1:{port}/api/snips/1") as r:
            assert r.status == 200
            got = json.loads(r.read().decode("utf-8"))
            assert got == {"id": 1, "text": "hello"}
    finally:
        httpd.shutdown()

def test_get_missing_is_404(tmp_path):
    db = tmp_path / "snips.json"
    port = _port()
    httpd, _, t = app.run(blocking=False, port=port, db=str(db))
    try:
        time.sleep(0.05)
        try:
            urlopen(f"http://127.0.0.1:{port}/api/snips/999")
            assert False, "expected 404"
        except HTTPError as e:
            assert e.code == 404
    finally:
        httpd.shutdown()
