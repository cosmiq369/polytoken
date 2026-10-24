import json
from uuid import UUID

import httpx
import pytest

from polytoken.zetaris import ZetarisClient, ZetarisError


def make_client(settings, logger, handler):
    return ZetarisClient(settings, logger=logger, client=httpx.Client(transport=httpx.MockTransport(handler)))


def rows(logger):
    return [json.loads(line) for line in (logger.directory / "zetaris_queries.jsonl").read_text().splitlines()]


def test_non_one_org_id_and_query_headers(settings, logger):
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path.endswith("login"):
            assert json.loads(request.content) == {"username": settings.zetaris_user, "password": settings.zetaris_password}
            return httpx.Response(200, json={"idToken": "fixture-jwt-opaque", "orgId": 73})
        assert request.headers["Authorization"] == "Bearer fixture-jwt-opaque"
        assert request.headers["X-Org-ID"] == "73"
        UUID(request.headers["X-Request-ID"], version=4)
        assert json.loads(request.content) == {"select": "select 7 as seven", "pageLimit": 1000}
        assert request.extensions["timeout"]["read"] == 60
        return httpx.Response(200, json={"records": [{"seven": "7"}]})

    client = make_client(settings, logger, handler)
    client.login()
    assert client.org_id == 73
    assert client.query("select 7 as seven") == [{"seven": "7"}]
    assert len(requests) == 2
    audit = rows(logger)
    assert len(audit) == 1
    assert audit[0]["ok"] is True
    assert audit[0]["rows_returned"] == 1


@pytest.mark.parametrize("second_status", [200, 401])
def test_401_relogs_in_exactly_once(settings, logger, second_status):
    logins, queries, request_ids = [], [], []

    def handler(request):
        if request.url.path.endswith("login"):
            logins.append(request)
            return httpx.Response(200, json={"idToken": f"jwt-{len(logins)}", "orgId": len(logins) + 10})
        queries.append(request)
        request_ids.append(request.headers["X-Request-ID"])
        assert request.headers["Authorization"] == f"Bearer jwt-{len(logins)}"
        assert request.headers["X-Org-ID"] == str(len(logins) + 10)
        return httpx.Response(401 if len(queries) == 1 else second_status, json={"records": []})

    client = make_client(settings, logger, handler)
    if second_status == 401:
        with pytest.raises(ZetarisError, match="HTTP 401"):
            client.query("select 1")
    else:
        assert client.query("select 1") == []
    assert len(logins) == len(queries) == 2
    assert len(set(request_ids)) == 2
    assert len(rows(logger)) == 1
    assert rows(logger)[0]["ok"] == (second_status == 200)


def test_body_truncation_and_secret_redaction(settings, logger):
    def handler(request):
        if request.url.path.endswith("login"):
            return httpx.Response(200, json={"idToken": "private-returned-jwt", "orgId": 99})
        return httpx.Response(500, text=settings.zetaris_password + " private-returned-jwt " + "x" * 500)

    with pytest.raises(ZetarisError, match="HTTP 500") as exc:
        make_client(settings, logger, handler).query("select '" + settings.nvidia_api_key + "' " + "x" * 700)
    message = str(exc.value)
    assert settings.zetaris_password not in message
    assert "private-returned-jwt" not in message
    assert len(message.split("HTTP 500: ")[1]) == 200
    assert len(rows(logger)[0]["sql"]) <= 500
    assert settings.nvidia_api_key not in (logger.directory / "zetaris_queries.jsonl").read_text()
    assert rows(logger)[0]["ok"] is False


@pytest.mark.parametrize("body", [{}, {"idToken": "x"}, {"orgId": 7}, {"idToken": "x", "orgId": None}])
def test_invalid_login_is_a_logged_query_failure(settings, logger, body):
    with pytest.raises(ZetarisError, match="JWT or orgId"):
        make_client(settings, logger, lambda r: httpx.Response(200, json=body)).query("select 1")
    assert rows(logger)[0]["ok"] is False


@pytest.mark.parametrize("body", [{}, {"records": None}, {"records": [1]}, {"error": "SQL failed"}])
def test_invalid_query_body_does_not_invent_empty_results(settings, logger, body):
    def handler(request):
        return httpx.Response(200, json={"idToken": "x", "orgId": 2} if request.url.path.endswith("login") else body)

    with pytest.raises(ZetarisError):
        make_client(settings, logger, handler).query("select 1")
    assert rows(logger)[0]["ok"] is False


def test_transport_error_is_safe_and_logged(settings, logger):
    def handler(request):
        raise httpx.ConnectError(settings.zetaris_password)

    with pytest.raises(ZetarisError, match="ConnectError") as exc:
        make_client(settings, logger, handler).query("select 1")
    assert settings.zetaris_password not in str(exc.value)
    assert len(rows(logger)) == 1
