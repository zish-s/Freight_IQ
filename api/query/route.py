"""POST /api/query/route - the full decision pack for one corridor.

Self-contained: see the note in api/corridors.py about Vercel bundling.

The website posts a fixed shape (origin, destination, vessel_class, cargo type
and tonnage). The corridor is looked up by the first three and the recorded
response for it is returned verbatim.
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
    for base in (here.parent, here.parent.parent, here.parent.parent.parent,
                 Path.cwd(), Path.cwd() / "api"):
        for name in (base / "api_data.json", base.parent / "api_data.json"):
            if name.is_file():
                _DATA = json.loads(name.read_text(encoding="utf-8"))
                return _DATA
    raise FileNotFoundError(
        "api_data.json not found. Run: python tools/build_api_snapshot.py"
    )


def unavailable(reason):
    """The same shape the backend returns when a corridor has no history, so the
    website keeps showing its honest message instead of an error."""
    return {
        "available": False,
        "reason": reason,
        "freight_forecast": {"available": False, "reason": reason},
        "congestion_model": {"available": False, "reason": reason},
        "market_timing": {"available": False, "reason": reason},
        "contract_comparison": {"available": False, "reason": reason},
        "vessel_optimizer": {"available": False, "reason": reason},
        "idle_analysis": {"available": False, "reason": reason},
        "risk_mitigation": {"available": False, "reason": reason},
        "explanation": {"available": False, "reason": reason},
    }


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

    def do_POST(self):
        if urlparse(self.path).path.rstrip("/") != "/api/query/route":
            self._send({"detail": "not found"}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            length = 0
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            self._send({"detail": "invalid JSON body"}, 400)
            return

        origin = str(body.get("origin", "")).strip()
        destination = str(body.get("destination", "")).strip()
        vessel_class = str(body.get("vessel_class", "")).strip()
        if not (origin and destination and vessel_class):
            self._send({"detail": "origin, destination and vessel_class are required"}, 400)
            return

        try:
            data = load()
        except FileNotFoundError as e:
            self._send({"detail": str(e)}, 500)
            return
        except Exception as e:
            self._send({"detail": f"{type(e).__name__}: {e}"}, 500)
            return

        k = f"{origin}|{destination}|{vessel_class}"
        found = data.get("route", {}).get(k)
        if found is None:
            self._send(unavailable(
                f"no recorded response for corridor '{origin} -> {destination}' "
                f"/ {vessel_class}"), 200)
            return
        self._send(found)

    def log_message(self, *args):
        pass
