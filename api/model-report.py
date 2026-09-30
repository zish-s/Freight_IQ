"""GET /api/model-report - the recorded walk-forward validation results.

Self-contained: see the note in api/corridors.py about Vercel bundling.
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

_DATA = None


def load():
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


def _clean(obj):
    """Replace non-finite floats with None.

    Python writes NaN by default, but NaN is not valid JSON and the browser's
    JSON.parse() rejects the entire body. A missing measurement is None, which
    the frontend already renders as "n/a".
    """
    if isinstance(obj, float):
        return obj if obj == obj and obj not in (float("inf"), float("-inf")) else None
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    return obj

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
        if urlparse(self.path).path.rstrip("/") not in ("/api/model-report", ""):
            self._send({"detail": "not found"}, 404)
            return
        try:
            self._send(_clean(load()["model_report"]))
        except FileNotFoundError as e:
            self._send({"detail": str(e)}, 500)
        except Exception as e:
            self._send({"detail": f"{type(e).__name__}: {e}"}, 500)

    def log_message(self, *args):
        pass
