"""GET /api/corridors - the corridors the models can price.

Self-contained on purpose. Vercel bundles and imports each file under api/ as an
independent function, so a function that imports a sibling module can fail with a
500 if that sibling is not traced into the bundle. Nothing here is imported from
the rest of the project; this file is the whole function.
"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

_DATA = None


def load():
    """Read api_data.json, cached for the life of this warm function."""
    global _DATA
    if _DATA is not None:
        return _DATA
    here = Path(__file__).resolve()
    for base in (here.parent, here.parent.parent, Path.cwd(), Path.cwd() / "api"):
        for name in (base / "api_data.json", base.parent / "api_data.json"):
            if name.is_file():
                _DATA = json.loads(name.read_text(encoding="utf-8"))
                return _DATA
    raise FileNotFoundError(
        "api_data.json not found. Run: python tools/build_api_snapshot.py"
    )


class handler(BaseHTTPRequestHandler):
    def _send(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send({})

    def do_GET(self):
        if urlparse(self.path).path.rstrip("/") not in ("/api/corridors", ""):
            self._send({"detail": "not found"}, 404)
            return
        try:
            self._send(load()["corridors"])
        except FileNotFoundError as e:
            self._send({"detail": str(e)}, 500)
        except Exception as e:  # never return an empty 500
            self._send({"detail": f"{type(e).__name__}: {e}"}, 500)

    def log_message(self, *args):
        pass
