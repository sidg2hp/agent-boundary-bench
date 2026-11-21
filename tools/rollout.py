"""Run Terminus-2 with the model credential retained in the host relay process."""
import argparse
from collections import Counter
from http.client import HTTPSConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import threading
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
MODEL = "gpt-6.1-sol"


def settings(pdf):
    if pdf is None:
        return os.environ["OPENAI_BASE_URL"], os.environ["OPENAI_API_KEY"]
    executable = shutil.which("pdftotext") or shutil.which("pdftotext.exe")
    if not executable:
        raise ValueError("pdftotext is required for --pdf")
    content = subprocess.check_output([executable, "-layout", "-enc", "UTF-8", str(pdf), "-"],
                                      stderr=subprocess.DEVNULL).decode("utf-8")
    def field(name):
        match = re.search(r"(?m)^\s*" + name + r"[ \t]+(\S+)", content)
        if not match:
            raise ValueError(f"missing {name} field")
        return match[1]
    return field("OPENAI_BASE_URL"), field("OPENAI_API_KEY")


def handler(upstream, key, local_auth, counts):
    class Relay(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            if self.path != "/v1/chat/completions" or not secrets.compare_digest(
                    self.headers.get("Authorization", ""), "Bearer " + local_auth):
                self.send_error(403)
                return
            try:
                size = int(self.headers.get("Content-Length", 0))
                if not 0 < size <= 16_000_000:
                    raise ValueError("invalid body length")
                payload = json.loads(self.rfile.read(size))
                if payload.get("model") != MODEL or payload.get("stream"):
                    raise ValueError("unexpected model or streaming mode")
                if payload.get("reasoning_effort", "high") != "high":
                    raise ValueError("unexpected reasoning effort")
                payload["reasoning_effort"] = "high"
                if "max_tokens" in payload:
                    legacy = payload.pop("max_tokens")
                    payload.setdefault("max_completion_tokens", legacy)
            except (ValueError, TypeError):
                self.send_error(400)
                return
            remote = HTTPSConnection(upstream.hostname, upstream.port or 443, timeout=900)
            try:
                remote.request("POST", upstream.path.rstrip("/") + "/chat/completions",
                               json.dumps(payload).encode(), {"Content-Type":"application/json",
                               "Authorization":"Bearer " + key})
                response = remote.getresponse()
                body = response.read()
                status = response.status
                if status == 200:
                    parsed = json.loads(body)
                    if parsed.get("model") != MODEL or not parsed.get("choices"):
                        raise ValueError("unexpected response schema")
                else:
                    body = json.dumps({"error":{"message":f"Upstream HTTP {status}"}}).encode()
            except (OSError, ValueError):
                status, body = 502, b'{"error":{"message":"upstream transport or response error"}}'
            finally:
                remote.close()
            counts[status] += 1
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
    return Relay


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--pdf", type=Path)
    cli.add_argument("--job-name", required=True)
    cli.add_argument("--task", choices=[f"rle_0{i}" for i in range(1,6)], action="append")
    cli.add_argument("--concurrency", type=int, default=3)
    cli.add_argument("--attempts", type=int, default=1, help="independent trials per task")
    args = cli.parse_args()
    url, key = settings(args.pdf)
    upstream = urlsplit(url)
    if upstream.scheme != "https" or not upstream.hostname or upstream.username or upstream.query:
        raise ValueError("expected an HTTPS API base URL")
    counts = Counter()
    local_auth = secrets.token_hex(24)
    with ThreadingHTTPServer(("127.0.0.1", 0), handler(upstream, key, local_auth, counts)) as server:
        base = f"http://127.0.0.1:{server.server_port}/v1"
        threading.Thread(target=server.serve_forever, daemon=True).start()
        env = {**os.environ, "OPENAI_API_KEY":local_auth, "OPENAI_BASE_URL":base,
               "OPENAI_API_BASE":base, "LITELLM_LOG":"ERROR"}
        cmd = ["harbor", "run", "-p", str(ROOT / "environments"), "-a", "terminus-2", "-m",
               "openai/" + MODEL, "--ak", "reasoning_effort=high", "--base-url", base,
               "-k", str(args.attempts), "-n", str(args.concurrency), "-o", str(ROOT / "jobs"),
               "--job-name", args.job_name, "--yes"]
        for task in args.task or []:
            cmd.extend(["-i", task])
        try:
            outcome = subprocess.run(cmd, env=env)
        finally:
            server.shutdown()
        print("Model endpoint HTTP status counts", dict(counts), flush=True)
        if outcome.returncode or not counts[200]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
