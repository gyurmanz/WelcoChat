# Entry point for cPanel's "Setup Python App" (Phusion Passenger).
# Passenger loads this file and calls the WSGI-callable named "application"
# (set as the app's "entry point" in cPanel). FastAPI is ASGI, not WSGI.
#
# We do NOT use a2wsgi here: its ASGIMiddleware spawns a background thread
# running its own persistent event loop and blocks the calling (WSGI) thread
# on a threading.Event set from that other thread. Under this host's
# CloudLinux CageFS/LVE, that background thread never runs the request to
# completion (confirmed via tracing — the WSGI call hangs forever waiting on
# the event, even though nothing else is wrong), so every request timed out.
#
# Instead this is a minimal, single-threaded ASGI-to-WSGI bridge: it builds
# the ASGI scope from the WSGI environ and runs the app with asyncio.run(),
# entirely on the thread Passenger already gave us. No background thread, no
# cross-thread handoff, nothing to hang. It buffers the whole request body
# and response in memory (fine for this API's JSON/file-upload payloads) and
# does not support streaming responses or websockets — this app uses neither
# (Live Chat replies are polled, not pushed over a socket).
import asyncio
import sys
from http import HTTPStatus
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.main import app as _asgi_app


def _build_scope(environ):
    headers = []
    for key, value in environ.items():
        if key.startswith("HTTP_"):
            name = key[5:].lower().replace("_", "-")
            headers.append((name.encode("latin-1"), value.encode("latin-1")))
        elif key in ("CONTENT_TYPE", "CONTENT_LENGTH") and value:
            headers.append((key.lower().encode("latin-1"), value.encode("latin-1")))

    server_port = environ.get("SERVER_PORT") or "0"
    remote_port = environ.get("REMOTE_PORT") or "0"

    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": environ.get("SERVER_PROTOCOL", "HTTP/1.1").rsplit("/", 1)[-1],
        "method": environ["REQUEST_METHOD"],
        "scheme": environ.get("wsgi.url_scheme", "http"),
        "path": environ.get("PATH_INFO", ""),
        "raw_path": environ.get("PATH_INFO", "").encode("utf-8"),
        "query_string": environ.get("QUERY_STRING", "").encode("latin-1"),
        "root_path": environ.get("SCRIPT_NAME", ""),
        "headers": headers,
        "server": (environ.get("SERVER_NAME", ""), int(server_port)),
        "client": (environ.get("REMOTE_ADDR", ""), int(remote_port)),
        "extensions": {},
    }


async def _run_asgi(scope, body):
    body_sent = False
    response = {"status": 500, "headers": [], "chunks": []}

    async def receive():
        nonlocal body_sent
        if not body_sent:
            body_sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        if message["type"] == "http.response.start":
            response["status"] = message["status"]
            response["headers"] = message.get("headers", [])
        elif message["type"] == "http.response.body":
            response["chunks"].append(message.get("body", b""))

    await _asgi_app(scope, receive, send)
    return response


def application(environ, start_response):
    scope = _build_scope(environ)
    content_length = int(environ.get("CONTENT_LENGTH") or 0)
    body = environ["wsgi.input"].read(content_length) if content_length else b""

    response = asyncio.run(_run_asgi(scope, body))

    try:
        reason = HTTPStatus(response["status"]).phrase
    except ValueError:
        reason = ""
    status_line = f"{response['status']} {reason}".strip()
    wsgi_headers = [
        (name.decode("latin-1"), value.decode("latin-1"))
        for name, value in response["headers"]
    ]
    start_response(status_line, wsgi_headers)
    return response["chunks"]
