"""Build and run the Docker image (v0.20). Written by the architect; implementation must pass it unchanged.
Skipped when Docker is not installed or its engine is not running. The image must serve the web app, answer the
API, run as a non-root user, and not contain the local .venv or .git."""
import json
import os
import shutil
import socket
import subprocess
import time
import urllib.request

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
IMAGE = "clusterflow:test"


def docker_ready():
    if shutil.which("docker") is None:
        return False
    try:
        return subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                              timeout=30).returncode == 0
    except subprocess.TimeoutExpired:
        return False


pytestmark = pytest.mark.skipif(not docker_ready(), reason="Docker engine not available")


def docker(*args, timeout=600):
    return subprocess.run(["docker", *args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          universal_newlines=True, encoding="utf-8", timeout=timeout)


@pytest.fixture(scope="module")
def container():
    build = docker("build", "-t", IMAGE, ROOT)
    assert build.returncode == 0, build.stdout[-3000:]
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    run = docker("run", "-d", "--rm", "-p", "127.0.0.1:%d:8000" % port, IMAGE)
    assert run.returncode == 0, run.stdout
    cid = run.stdout.strip()
    base = "http://127.0.0.1:%d" % port
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(base + "/api/health", timeout=2)
                break
            except OSError:
                time.sleep(0.5)
        yield cid, base
    finally:
        docker("stop", cid, timeout=60)


def test_health(container):
    _, base = container
    with urllib.request.urlopen(base + "/api/health", timeout=10) as r:
        assert json.load(r) == {"status": "ok"}


def test_serves_page_and_analyses_demo(container):
    _, base = container
    with urllib.request.urlopen(base + "/", timeout=10) as r:
        assert "ClusterFlow" in r.read().decode("utf-8")
    demo = urllib.request.urlopen(base + "/api/example", timeout=10).read().decode("utf-8")
    req = urllib.request.Request(base + "/api/analyze-text", data=json.dumps({"text": demo}).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        assert json.load(r)["summary"]["job_count"] == 32


def test_runs_as_non_root(container):
    cid, _ = container
    assert docker("exec", cid, "id", "-u").stdout.strip() != "0"


def test_no_local_junk_in_image(container):
    cid, _ = container
    out = docker("exec", cid, "sh", "-c", "ls -a /app /app/backend").stdout
    assert ".venv" not in out and ".git" not in out and "__pycache__" not in out
