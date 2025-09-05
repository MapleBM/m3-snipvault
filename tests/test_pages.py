# C:\Users\baket\code\m3-snipvault\tests\test_pages.py
import time, socket
from urllib.request import urlopen, Request
import snipvault.server as app

def _port():
    import socket
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

def test_index_served(tmp_path):
    port = _port()
    httpd, _, t = app.run(blocking=False, port=port, db=str(tmp_path/"snips.json"))
    try:
        time.sleep(0.05)
        with urlopen(f"http://127.0.0.1:{port}/") as r:
            assert r.status == 200
            html = r.read().decode("utf-8")
            assert "<title>SnipVault</title>" in html
    finally:
        httpd.shutdown()

def test_s_page_shows_text(tmp_path):
    port = _port()
    db = tmp_path / "snips.json"
    httpd, _, t = app.run(blocking=False, port=port, db=str(db))
    try:
        time.sleep(0.05)
        body = "text=Alpha%20Bravo"
        req = Request(f"http://127.0.0.1:{port}/api/snips", data=body.encode("utf-8"),
                      headers={"Content-Type":"application/x-www-form-urlencoded"})
        with urlopen(req) as r:
            assert r.status == 201
        with urlopen(f"http://127.0.0.1:{port}/s/1") as r:
            html = r.read().decode("utf-8")
            assert "Alpha Bravo" in html
    finally:
        httpd.shutdown()
