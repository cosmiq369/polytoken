"""Zetaris SQL client following the local platform's verify.sh contract."""

from __future__ import annotations

import time
from uuid import uuid4

import httpx

from .config import Settings
from .logs import JsonlLogger


class ZetarisError(RuntimeError):
    pass


class ZetarisTruncated(ZetarisError):
    """The result page may omit rows; callers must explicitly accept that."""


class ZetarisClient:
    def __init__(self, settings: Settings, *, logger: JsonlLogger | None = None,
                 client: httpx.Client | None = None, timeout_s: float = 60.0):
        self.settings = settings
        self.logger = logger or JsonlLogger(secrets=settings.secrets)
        self.logger.add_secrets(*settings.secrets)
        self._client = client or httpx.Client()
        self._owns_client = client is None
        self._timeout = httpx.Timeout(timeout_s, connect=min(timeout_s, 10.0))
        self._token: str | None = None
        self.org_id: int | str | None = None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _failure(self, response: httpx.Response, action: str, detail: str = "") -> ZetarisError:
        # Redact the full body before truncation so a cut-off secret cannot leak.
        safe = self.logger.redact(response.text)
        return ZetarisError(f"Zetaris {action} failed: HTTP {response.status_code}{': ' + detail if detail else ''}: {safe[:200]}")

    def _json(self, response: httpx.Response, action: str) -> dict:
        try:
            body = response.json()
        except ValueError:
            raise self._failure(response, action, "invalid JSON") from None
        if not isinstance(body, dict):
            raise self._failure(response, action, "expected a JSON object")
        return body

    def login(self) -> None:
        try:
            response = self._client.post(
                self.settings.zetaris_url + "/api/auth/login",
                json={"username": self.settings.zetaris_user, "password": self.settings.zetaris_password},
                timeout=self._timeout,
            )
            if not response.is_success:
                raise self._failure(response, "login")
            body = self._json(response, "login")
            # Register all response tokens before any later error can include them.
            for key in ("idToken", "accessToken", "token", "refreshToken"):
                if isinstance(body.get(key), str):
                    self.logger.add_secrets(body[key])
            token = body.get("idToken") or body.get("accessToken") or body.get("token")
            org_id = body.get("orgId")
            if not isinstance(token, str) or not token or isinstance(org_id, bool) or not isinstance(org_id, (int, str)) or not str(org_id):
                raise self._failure(response, "login", "missing a valid JWT or orgId")
            self._token, self.org_id = token, org_id
        except ZetarisError:
            raise
        except Exception as exc:
            raise ZetarisError(f"Zetaris login failed: {type(exc).__name__}") from None

    def query(self, sql: str, page_limit: int = 1000, *, allow_truncated: bool = False) -> list[dict]:
        start = time.monotonic()
        rows = []
        ok = False
        error_class = None
        possibly_truncated = False
        try:
            if not isinstance(page_limit, int) or isinstance(page_limit, bool) or page_limit <= 0:
                raise ZetarisError("page_limit must be a positive integer")
            if self._token is None:
                self.login()
            for attempt in range(2):
                response = self._client.post(
                    self.settings.zetaris_url + "/api/proxy/query/sql/start",
                    headers={"Authorization": "Bearer " + self._token,
                             "X-Org-ID": str(self.org_id), "X-Request-ID": str(uuid4())},
                    json={"select": sql, "pageLimit": page_limit}, timeout=self._timeout,
                )
                if response.status_code == 401 and attempt == 0:
                    self._token = None
                    self.login()
                    continue
                if not response.is_success:
                    raise self._failure(response, "query")
                body = self._json(response, "query")
                if body.get("error"):
                    raise self._failure(response, "query response")
                records = body.get("records")
                if not isinstance(records, list) or any(not isinstance(row, dict) for row in records):
                    raise self._failure(response, "query", "missing a valid records list")
                rows = records
                possibly_truncated = (
                    len(rows) >= page_limit
                    or int(body.get("totalPages") or 1) > int(body.get("pageNumber") or 1)
                    or int(body.get("totalCount") or len(rows)) > len(rows)
                )
                if possibly_truncated and not allow_truncated:
                    raise ZetarisTruncated(
                        "Zetaris result may be truncated; increase page_limit, partition the query, "
                        "or explicitly pass allow_truncated=True"
                    )
                ok = True
                return rows
            raise AssertionError("unreachable")
        except Exception as exc:
            error_class = type(exc).__name__
            if isinstance(exc, ZetarisError):
                raise
            raise ZetarisError(f"Zetaris query failed: {error_class}") from None
        finally:
            self.logger.write("zetaris_queries", "query", sql=self.logger.redact(sql)[:500],
                              rows_returned=len(rows), latency_s=time.monotonic() - start,
                              ok=ok, error_class=error_class, possibly_truncated=possibly_truncated)
