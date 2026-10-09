import json
import threading
import urllib.error
import urllib.request

import pytest

from autofx.editor_server import make_server, resolve_shader_path


@pytest.fixture
def shader_dir(tmp_path):
    (tmp_path / "fire.glsl").write_text("// @param speed float 1 [0, 2]\n")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "ice.glsl").write_text("void mainImage() {}\n")
    (tmp_path / "notes.txt").write_text("not a shader")
    return tmp_path


@pytest.fixture
def server(shader_dir):
    srv = make_server(shader_dir, initial="fire.glsl", port=0)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def request(url, method="GET", data=None, headers=None):
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def test_resolve_accepts_nested_shaders(shader_dir):
    assert resolve_shader_path(shader_dir, "sub/ice.glsl") == shader_dir / "sub" / "ice.glsl"


@pytest.mark.parametrize("bad", ["../escape.glsl", "/etc/passwd.glsl", "notes.txt", "sub/../../x.glsl", ""])
def test_resolve_rejects_paths_outside_root_or_not_glsl(shader_dir, bad):
    with pytest.raises(ValueError):
        resolve_shader_path(shader_dir, bad)


def test_serves_the_editor_page(server):
    status, body = request(server + "/")
    assert status == 200
    assert "<title>" in body


def test_lists_shaders_and_initial_selection(server):
    status, body = request(server + "/api/shaders")
    data = json.loads(body)
    assert status == 200
    assert data["shaders"] == ["fire.glsl", "sub/ice.glsl"]
    assert data["initial"] == "fire.glsl"
    assert data["writable"] is True


def test_reads_a_shader(server):
    status, body = request(server + "/api/shader?path=sub/ice.glsl")
    assert (status, body) == (200, "void mainImage() {}\n")


def test_saves_a_shader_with_the_editor_header(server, shader_dir):
    status, _ = request(server + "/api/shader?path=fire.glsl", "PUT", b"new code", {"X-AutoFX": "1"})
    assert status == 200
    assert (shader_dir / "fire.glsl").read_text() == "new code"


def test_rejects_saves_without_the_editor_header(server, shader_dir):
    status, _ = request(server + "/api/shader?path=fire.glsl", "PUT", b"evil")
    assert status == 403
    assert "evil" not in (shader_dir / "fire.glsl").read_text()


def test_rejects_requests_for_other_hosts(server):
    status, _ = request(server + "/api/shaders", headers={"Host": "attacker.example"})
    assert status == 403


def test_rejects_reading_outside_root(server):
    status, _ = request(server + "/api/shader?path=../secret.glsl")
    assert status == 400
