from __future__ import annotations

import json
import os
import secrets
import sqlite3
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs


ROOT_DIR = Path(__file__).resolve().parent


def load_dotenv_file() -> None:
    env_path = ROOT_DIR / '.env'

    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()

        if not line or line.startswith('#') or '=' not in line:
            continue

        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip())


load_dotenv_file()

RESPONSES_JSON_FILE = ROOT_DIR / 'responses-data.json'
RESPONSES_DB_PATH = Path(os.environ.get('FOCUS_AI_DB_PATH', str(ROOT_DIR / 'focus_ai.db')))
HOST = os.environ.get('HOST', '0.0.0.0')
PORT = int(os.environ.get('PORT', '4173'))
RESPONSES_PASSWORD = os.environ.get('FOCUS_AI_RESPONSES_PASSWORD')
RESPONSES_SESSION_COOKIE = 'focus_ai_responses_auth'
SECURE_COOKIES = os.environ.get('FOCUS_AI_SECURE_COOKIES', '0') == '1'
ACTIVE_SESSIONS: set[str] = set()


def load_responses() -> list[dict]:
    if not RESPONSES_JSON_FILE.exists():
        return []

    try:
        return json.loads(RESPONSES_JSON_FILE.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return []


def get_db_connection() -> sqlite3.Connection:
    RESPONSES_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(RESPONSES_DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with get_db_connection() as connection:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                app TEXT NOT NULL,
                feedback_type TEXT NOT NULL,
                rating TEXT NOT NULL,
                message TEXT NOT NULL,
                submitted_at TEXT NOT NULL
            )
            '''
        )

    migrate_json_responses_if_needed()


def migrate_json_responses_if_needed() -> None:
    legacy_responses = load_responses()

    if not legacy_responses:
        return

    with get_db_connection() as connection:
        existing_count = connection.execute('SELECT COUNT(*) FROM responses').fetchone()[0]

        if existing_count:
            return

        connection.executemany(
            '''
            INSERT INTO responses (
                name,
                email,
                app,
                feedback_type,
                rating,
                message,
                submitted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            [
                (
                    str(item.get('name', '')).strip(),
                    str(item.get('email', '')).strip(),
                    str(item.get('app', '')).strip(),
                    str(item.get('feedbackType', '')).strip(),
                    str(item.get('rating', '')).strip(),
                    str(item.get('message', '')).strip(),
                    str(item.get('submittedAt', '')).strip(),
                )
                for item in legacy_responses
            ],
        )


def fetch_responses() -> list[dict]:
    with get_db_connection() as connection:
        rows = connection.execute(
            '''
            SELECT
                name,
                email,
                app,
                feedback_type,
                rating,
                message,
                submitted_at
            FROM responses
            ORDER BY submitted_at DESC, id DESC
            '''
        ).fetchall()

    return [
        {
            'name': row['name'],
            'email': row['email'],
            'app': row['app'],
            'feedbackType': row['feedback_type'],
            'rating': row['rating'],
            'message': row['message'],
            'submittedAt': row['submitted_at'],
        }
        for row in rows
    ]


def store_response(response: dict) -> None:
    with get_db_connection() as connection:
        connection.execute(
            '''
            INSERT INTO responses (
                name,
                email,
                app,
                feedback_type,
                rating,
                message,
                submitted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                str(response.get('name', '')).strip(),
                str(response.get('email', '')).strip(),
                str(response.get('app', '')).strip(),
                str(response.get('feedbackType', '')).strip(),
                str(response.get('rating', '')).strip(),
                str(response.get('message', '')).strip(),
                str(response.get('submittedAt', '')).strip(),
            ),
        )


def build_session_cookie(value: str, max_age: int | None = None) -> str:
    parts = [
        f'{RESPONSES_SESSION_COOKIE}={value}',
        'HttpOnly',
        'Path=/',
        'SameSite=Lax',
    ]

    if max_age is not None:
        parts.insert(1, f'Max-Age={max_age}')

    if SECURE_COOKIES:
        parts.append('Secure')

    return '; '.join(parts)


class FocusAIHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT_DIR), **kwargs)

    def do_GET(self) -> None:
        if self.path == '/responses.html' and not self._is_authenticated():
            self._redirect('/responses-login.html')
            return

        if self.path == '/responses-login.html' and self._is_authenticated():
            self._redirect('/responses.html')
            return

        if self.path == '/api/responses':
            if not self._is_authenticated():
                self._send_json({'error': 'Unauthorized'}, status=401)
                return

            self._send_json(fetch_responses())
            return

        super().do_GET()

    def do_POST(self) -> None:
        if self.path == '/responses-login':
            self._handle_login()
            return

        if self.path == '/responses-logout':
            self._handle_logout()
            return

        if self.path != '/api/responses':
            self.send_error(404, 'Not Found')
            return

        content_length = int(self.headers.get('Content-Length', '0'))
        payload = self.rfile.read(content_length)

        try:
            response = json.loads(payload.decode('utf-8'))
        except json.JSONDecodeError:
            self._send_json({'error': 'Invalid JSON payload.'}, status=400)
            return

        required_fields = ['name', 'email', 'message']
        if any(not str(response.get(field, '')).strip() for field in required_fields):
            self._send_json({'error': 'Name, email, and message are required.'}, status=400)
            return

        store_response({
            'name': str(response.get('name', '')).strip(),
            'email': str(response.get('email', '')).strip(),
            'app': str(response.get('app', '')).strip(),
            'feedbackType': str(response.get('feedbackType', '')).strip(),
            'rating': str(response.get('rating', '')).strip(),
            'message': str(response.get('message', '')).strip(),
            'submittedAt': str(response.get('submittedAt', '')).strip(),
        })
        self._send_json({'ok': True}, status=201)

    def _handle_login(self) -> None:
        content_length = int(self.headers.get('Content-Length', '0'))
        payload = self.rfile.read(content_length).decode('utf-8')
        form_data = parse_qs(payload)
        password = form_data.get('password', [''])[0]

        if password != RESPONSES_PASSWORD:
            self._redirect('/responses-login.html?error=1')
            return

        session_token = secrets.token_urlsafe(24)
        ACTIVE_SESSIONS.add(session_token)

        self.send_response(303)
        self.send_header('Location', '/responses.html')
        self.send_header('Set-Cookie', build_session_cookie(session_token))
        self.end_headers()

    def _handle_logout(self) -> None:
        session_token = self._get_session_token()
        if session_token:
            ACTIVE_SESSIONS.discard(session_token)

        self.send_response(303)
        self.send_header('Location', '/responses-login.html')
        self.send_header('Set-Cookie', build_session_cookie('', 0))
        self.end_headers()

    def _is_authenticated(self) -> bool:
        session_token = self._get_session_token()

        if not session_token:
            return False

        return session_token in ACTIVE_SESSIONS

    def _get_session_token(self) -> str | None:
        cookie_header = self.headers.get('Cookie', '')
        cookies = [item.strip() for item in cookie_header.split(';') if item.strip()]

        for cookie in cookies:
            key, separator, value = cookie.partition('=')
            if separator and key == RESPONSES_SESSION_COOKIE:
                return value

        return None

    def _redirect(self, location: str) -> None:
        self.send_response(303)
        self.send_header('Location', location)
        self.end_headers()

    def _send_json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=True).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == '__main__':
    if not RESPONSES_PASSWORD:
        raise RuntimeError('Set FOCUS_AI_RESPONSES_PASSWORD in the environment or .env before starting the server.')

    initialize_database()

    server = ThreadingHTTPServer((HOST, PORT), FocusAIHandler)
    print(f'Serving Focus-AI on http://{HOST}:{PORT}')
    print('Responses password protected at /responses.html')
    print('Responses login session stays active until logout or server restart')
    print(f'Using SQLite database at {RESPONSES_DB_PATH}')
    server.serve_forever()