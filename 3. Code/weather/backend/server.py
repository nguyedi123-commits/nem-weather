"""Local web server for the Weather screen: serves web/ and the /api/* JSON. Reads data/ only – never downloads.

Pages (layouts) are saved as settings/layouts/<page>.json; built-in pages live in web/layouts/ (used until a page is
saved, and by "Reset"). Screen settings (theme, last page) in settings/settings.json.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import math
import os
from pathlib import Path
import re
import sys
import threading
from urllib.parse import parse_qs, unquote, urlparse

from . import cloud, config as C, progress, refresh, views

log = logging.getLogger("weather.server")
WEB = (Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]) / "web"
LAYOUTS = C.SETTINGS / "layouts"
BUILT_IN = ["Short", "Medium", "AI vs IFS", "Seasonal", "Map"]   # page order; first = start page
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".json": "application/json", ".txt": "text/plain; charset=utf-8", ".svg": "image/svg+xml"}

ROUTES = {"short": views.short, "medium": views.medium, "compare": views.compare, "seasonal": views.seasonal,
          "changes": views.changes}
ARGS = {"short": ("run", "vs"), "medium": ("run", "vs"), "seasonal": ("run", "vs"), "changes": ("model", "run", "vs"),
        "compare": ()}


class Cache:
    """JSON per (route, query), rebuilt when catalog.json changes (i.e. after a refresh)."""

    def __init__(self):
        self.version, self.data, self.lock = None, {}, threading.Lock()

    def get(self, key, make):
        cat = C.DATA / "catalog.json"
        v = cat.stat().st_mtime if cat.exists() else 0
        with self.lock:
            if v != self.version:
                self.version, self.data = v, {}
                views._cities.cache_clear()
                views._grid.cache_clear()
            if key not in self.data:
                self.data[key] = json.dumps(make(), allow_nan=False, default=_clean).encode()
            return self.data[key]


def _clean(v):
    if isinstance(v, float) and math.isnan(v):
        return None
    return str(v)


CACHE = Cache()


def safe_name(name):
    """Page name -> file name: letters, numbers, spaces, - and &."""
    n = re.sub(r"[^\w &\-]", "", unquote(name)).strip()
    if not n:
        raise ValueError("bad page name")
    return n


def _save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1))
    os.replace(tmp, path)


def load_settings():
    try:
        return json.loads((C.SETTINGS / "settings.json").read_text())
    except (FileNotFoundError, ValueError):
        return {"theme": "light", "page": BUILT_IN[0]}


def page_names():
    saved = [p.stem for p in LAYOUTS.glob("*.json")] if LAYOUTS.exists() else []
    return BUILT_IN + sorted(n for n in set(saved) if n not in BUILT_IN)


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data, code=200):
        self._send(code, json.dumps(data).encode())

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def _route(self):
        u = urlparse(self.path)
        return u, u.path.strip("/").split("/"), {k: v[0] for k, v in parse_qs(u.query).items()}

    def do_GET(self):
        u, parts, q = self._route()
        try:
            if parts[0] != "api":
                return self._static(u.path)
            name = parts[1] if len(parts) > 1 else ""
            if name == "status":   # small and changes with the clock: never cached
                return self._json({**views.status(), "progress": progress.read(), "refreshing": refresh.running(),
                                   "cloud": cloud.status()})
            if name == "layouts":
                return self._json(page_names())
            if name == "layout" and len(parts) == 3:
                f = LAYOUTS / f"{safe_name(parts[2])}.json"
                return self._json(json.loads(f.read_text()) if f.exists() else {})
            if name == "settings":
                return self._json(load_settings())
            if name == "runs":
                return self._send(200, CACHE.get(("runs",), views.runs_view))
            if name == "map":
                key = ("map", q.get("src", "ifs"), q.get("field", "temp"), q.get("i", "0"), q.get("run", "latest"),
                       q.get("vs", "none"))
                return self._send(200, CACHE.get(key, lambda: views.map_view(*key[1:])))
            if name in ROUTES:
                args = tuple(q[a] for a in ARGS[name] if a in q)
                kw = {a: q[a] for a in ARGS[name] if a in q}
                return self._send(200, CACHE.get((name,) + args, lambda: ROUTES[name](**kw)))
            return self._json({"error": "unknown"}, 404)
        except Exception as e:   # show the problem on the page instead of a blank panel
            log.exception("GET %s", self.path)
            return self._json({"error": f"{type(e).__name__}: {e}"}, 500)

    def do_PUT(self):
        u, parts, q = self._route()
        try:
            if parts[:2] == ["api", "layout"] and len(parts) == 3:
                _save_json(LAYOUTS / f"{safe_name(parts[2])}.json", self._body())
                return self._json({"ok": True})
            return self._json({"error": "unknown"}, 404)
        except Exception as e:
            log.exception("PUT %s", self.path)
            return self._json({"error": str(e)}, 500)

    def do_DELETE(self):
        u, parts, q = self._route()
        try:
            if parts[:2] == ["api", "layout"] and len(parts) == 3:
                (LAYOUTS / f"{safe_name(parts[2])}.json").unlink(missing_ok=True)
                return self._json({"ok": True})
            return self._json({"error": "unknown"}, 404)
        except Exception as e:
            return self._json({"error": str(e)}, 500)

    def do_POST(self):
        u, parts, q = self._route()
        try:
            if parts[:2] == ["api", "refresh"]:   # the Refresh button (W-018): downloads in the background
                why = refresh.start(self._body().get("mode", "light"))
                return self._json({"ok": why is None, "error": why})
            if parts[:2] == ["api", "settings"]:
                s = {**load_settings(), **self._body()}
                _save_json(C.SETTINGS / "settings.json", s)
                return self._json(s)
            return self._json({"error": "unknown"}, 404)
        except Exception as e:
            return self._json({"error": str(e)}, 500)

    def _static(self, path):
        rel = "index.html" if path in ("", "/") else unquote(path).lstrip("/")
        f = (WEB / rel).resolve()
        if WEB.resolve() not in f.parents or not f.is_file():
            return self._send(404, b"not found", "text/plain")
        self._send(200, f.read_bytes(), TYPES.get(f.suffix, "application/octet-stream"))

    def log_message(self, *args):
        pass


class _Server(ThreadingHTTPServer):
    allow_reuse_address = False   # on Windows "reuse" would let two servers share a port – we want the next free one
    daemon_threads = True


def start(port):
    """Start on `port`, or the next free one (e.g. a dev copy already on 8892)."""
    for p in range(port, port + 20):
        try:
            server = _Server(("127.0.0.1", p), Handler)
            break
        except OSError:
            continue
    else:
        raise OSError(f"no free port from {port}")
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
