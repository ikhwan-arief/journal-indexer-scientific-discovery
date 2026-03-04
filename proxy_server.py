from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse, unquote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import ssl
import json
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8787
SSL_CONTEXT = ssl._create_unverified_context()
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
STATE_FILE = DATA_DIR / "repo_state.json"


def default_state():
    return {
        "endpoints": [],
        "harvestedArticles": [],
        "journalOverrides": {},
        "deletedJournals": [],
        "posts": [],
        "users": []
    }


def load_state():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not STATE_FILE.exists():
        state = default_state()
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        return state

    try:
        raw = STATE_FILE.read_text(encoding="utf-8")
        parsed = json.loads(raw) if raw.strip() else {}
        state = default_state()
        if isinstance(parsed, dict):
            state.update(parsed)
        return state
    except Exception:
        return default_state()


def save_state(state):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    current = default_state()
    if isinstance(state, dict):
        current.update(state)
    STATE_FILE.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")


class OAIProxyHandler(BaseHTTPRequestHandler):
    def _send(self, status_code: int, body: bytes, content_type: str = "text/plain; charset=utf-8"):
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(204, b"")

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/health":
            self._send(200, b"ok")
            return

        if parsed.path == "/state":
            body = json.dumps(load_state(), ensure_ascii=False).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")
            return

        if parsed.path != "/oai":
            self._send(404, b"Not found")
            return

        params = parse_qs(parsed.query)
        raw_url = params.get("url", [""])[0]
        if not raw_url:
            self._send(400, b"Missing query parameter: url")
            return

        target_url = unquote(raw_url)
        try:
            request = Request(
                target_url,
                headers={
                    "User-Agent": "JournalIndexer-OAI-Proxy/1.0",
                    "Accept": "application/xml,text/xml,text/html;q=0.9,*/*;q=0.8",
                },
            )
            with urlopen(request, timeout=40, context=SSL_CONTEXT) as response:
                data = response.read()
                content_type = response.headers.get("Content-Type", "application/xml; charset=utf-8")
                self._send(200, data, content_type)
        except HTTPError as error:
            message = f"Upstream HTTPError {error.code}: {error.reason}".encode("utf-8")
            self._send(error.code, message)
        except URLError as error:
            message = f"Upstream URLError: {error.reason}".encode("utf-8")
            self._send(502, message)
        except Exception as error:
            message = f"Proxy error: {str(error)}".encode("utf-8")
            self._send(500, message)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/state":
            self._send(404, b"Not found")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length) if length > 0 else b"{}"
            payload = json.loads(raw_body.decode("utf-8") or "{}")
            if not isinstance(payload, dict):
                self._send(400, b"State payload must be a JSON object")
                return

            save_state(payload)
            body = json.dumps({"ok": True, "stateFile": str(STATE_FILE)}).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")
        except json.JSONDecodeError:
            self._send(400, b"Invalid JSON payload")
        except Exception as error:
            message = f"State save error: {str(error)}".encode("utf-8")
            self._send(500, message)


if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), OAIProxyHandler)
    print(f"OAI proxy running at http://{HOST}:{PORT}")
    print("Health check: http://127.0.0.1:8787/health")
    print(f"Persistent state: {STATE_FILE}")
    server.serve_forever()
