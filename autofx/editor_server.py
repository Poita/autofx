"""
Local web server for the shader editor (`autofx editor`).

Serves the static editor from autofx/editor/ plus a small API over the .glsl
files under one root directory:

    GET  /api/shaders            {"shaders": [...], "initial": ..., "writable": true}
    GET  /api/shader?path=REL    shader source
    PUT  /api/shader?path=REL    save shader source (requires the X-AutoFX header)

The server binds to localhost only. Requests must name a localhost Host
(guards against DNS rebinding), and saves need the custom X-AutoFX header,
which other sites cannot send without a CORS preflight this server never grants.
"""

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import List, Optional
from urllib.parse import parse_qs, urlparse

EDITOR_DIR = Path(__file__).parent / "editor"
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
}
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".claude"}
MAX_SHADERS = 1000
LOCAL_HOSTS = {"127.0.0.1", "localhost"}


def resolve_shader_path(root: Path, relative: str) -> Path:
    """Resolve a client-supplied path, allowing only .glsl files inside root."""
    root = root.resolve()
    path = (root / relative).resolve()
    if path.suffix != ".glsl" or not path.is_relative_to(root) or path == root:
        raise ValueError(f"not a .glsl file inside {root}: {relative!r}")
    return path


def list_shaders(root: Path) -> List[str]:
    found = []
    for path in sorted(root.rglob("*.glsl")):
        relative = path.relative_to(root)
        if any(part in SKIP_DIRS for part in relative.parts[:-1]):
            continue
        found.append(relative.as_posix())
        if len(found) >= MAX_SHADERS:
            break
    return found


def make_handler(root: Path, initial: Optional[str]):
    class EditorHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def _send(self, status, body=b"", content_type="text/plain; charset=utf-8"):
            if isinstance(body, str):
                body = body.encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _host_ok(self) -> bool:
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]")
            return host in LOCAL_HOSTS

        def _shader_path(self) -> Path:
            query = parse_qs(urlparse(self.path).query)
            return resolve_shader_path(root, query.get("path", [""])[0])

        def do_GET(self):
            if not self._host_ok():
                return self._send(HTTPStatus.FORBIDDEN, "forbidden host")
            route = urlparse(self.path).path

            if route == "/api/shaders":
                payload = {"shaders": list_shaders(root), "initial": initial, "writable": True}
                return self._send(HTTPStatus.OK, json.dumps(payload), "application/json")

            if route == "/api/shader":
                try:
                    path = self._shader_path()
                except ValueError as e:
                    return self._send(HTTPStatus.BAD_REQUEST, str(e))
                if not path.is_file():
                    return self._send(HTTPStatus.NOT_FOUND, "no such shader")
                return self._send(HTTPStatus.OK, path.read_text())

            name = "index.html" if route == "/" else route.lstrip("/")
            static = EDITOR_DIR / name
            if "/" not in name and static.suffix in CONTENT_TYPES and static.is_file():
                return self._send(HTTPStatus.OK, static.read_bytes(), CONTENT_TYPES[static.suffix])
            return self._send(HTTPStatus.NOT_FOUND, "not found")

        def do_PUT(self):
            if not self._host_ok() or self.headers.get("X-AutoFX") != "1":
                return self._send(HTTPStatus.FORBIDDEN, "forbidden")
            if urlparse(self.path).path != "/api/shader":
                return self._send(HTTPStatus.NOT_FOUND, "not found")
            try:
                path = self._shader_path()
            except ValueError as e:
                return self._send(HTTPStatus.BAD_REQUEST, str(e))
            length = int(self.headers.get("Content-Length") or 0)
            source = self.rfile.read(length).decode()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(source)
            return self._send(HTTPStatus.OK, json.dumps({"ok": True}), "application/json")

    return EditorHandler


def make_server(root: Path, initial: Optional[str] = None, port: int = 8765) -> ThreadingHTTPServer:
    root = Path(root).resolve()
    return ThreadingHTTPServer(("127.0.0.1", port), make_handler(root, initial))


def run_editor(target: str = ".", port: int = 8765, open_browser: bool = True) -> int:
    """Serve the editor for a .glsl file (opened on start) or a directory of shaders."""
    path = Path(target).resolve()
    if path.is_file():
        if path.suffix != ".glsl":
            print(f"Error: not a .glsl file: {target}")
            return 1
        root, initial = path.parent, path.name
    elif path.is_dir():
        root, initial = path, None
    else:
        print(f"Error: no such file or directory: {target}")
        return 1

    try:
        server = make_server(root, initial, port)
    except OSError as e:
        print(f"Error: could not listen on port {port}: {e}. Try --port.")
        return 1

    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"AutoFX editor: {url}")
    print(f"  Shaders under: {root}")
    print("  Press Ctrl+C to stop.")
    if open_browser:
        import webbrowser
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        server.server_close()
    return 0
