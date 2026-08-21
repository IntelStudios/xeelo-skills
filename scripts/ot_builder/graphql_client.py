"""Xeelo GraphQL client: connection, admin transfer download/upload/process, precompile."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from zipfile import ZipFile

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore


DEFAULT_TIMEOUT_SECONDS = 600.0
HEALTH_WAIT_SECONDS = 120.0
HEALTH_POLL_SECONDS = 2.0

QUERY_DOWNLOAD = """
query AdminTransferDownload {
  Select_admin_transfer_download {
    json
  }
}
"""

MUTATION_UPLOAD = """
mutation AdminTransferUpload($fileName: String!, $xml: String!) {
  Mutate_admin_transfer_upload(fileName: $fileName, xml: $xml) {
    objectSetupXmlId
  }
}
"""

MUTATION_PROCESS = """
mutation AdminTransferProcess($id: Int!, $isTestOnly: Boolean!) {
  Mutate_admin_transfer_process(id: $id, isTestOnly: $isTestOnly) {
    success
    messages { procedure msgType msgText }
  }
}
"""

MUTATION_PRECOMPILE = """
mutation AdminPrecompile {
  Mutate_admin_precompile {
    success
    messages { procedure msgType msgText }
  }
}
"""

QUERY_HEALTH = "query Health { health }"

NEW_FORMAT_HELP = (
    ".xeelo-connection.json needs xeeloUrl and token "
    "(Xeelo GraphQL access token with isAdmin). "
    'Example: { "xeeloUrl": "https://<site>.xeelo.online/", "token": "..." }'
)

AUTH_HINT = (
    "Use an admin GraphQL access token (isAdmin) in .xeelo-connection.json "
    'as { "xeeloUrl": "https://<site>.xeelo.online/", "token": "..." }. '
    "There is no token refresh."
)


class GraphqlError(RuntimeError):
    """GraphQL operation failed."""


class GraphqlAuthError(GraphqlError):
    """Missing, invalid, or non-admin GraphQL token."""


def _require_httpx():
    if httpx is None:
        raise SystemExit("httpx is required: pip install httpx")
    return httpx


def _join_url(base: str, path: str) -> str:
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


def xml_to_utf16_le_bytes(xml: str) -> bytes:
    """Encode GraphQL XML string as UTF-16 LE with BOM (extract/validate format)."""
    return xml.lstrip("\ufeff").encode("utf-16")


def decode_transfer_xml_bytes(data: bytes) -> str:
    if data[:2] == b"\xff\xfe":
        text = data.decode("utf-16-le")
    elif data[:2] == b"\xfe\xff":
        text = data.decode("utf-16-be")
    else:
        text = data.decode("utf-8")
    return text.lstrip("\ufeff")


def transfer_path_to_xml(path: Path) -> tuple[str, str]:
    """Return (fileName, xml string) from a .xml file or a ZIP with one XML entry."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Object Transfer not found: {path}")
    if path.suffix.lower() == ".zip":
        with ZipFile(path) as zf:
            for info in zf.infolist():
                if info.filename.endswith("/"):
                    continue
                data = zf.read(info.filename)
                name = Path(info.filename).name
                if not name.lower().endswith(".xml"):
                    name = path.with_suffix(".xml").name
                return name, decode_transfer_xml_bytes(data)
        raise FileNotFoundError(f"No XML entry in ZIP: {path}")
    return path.name, decode_transfer_xml_bytes(path.read_bytes())


def packages_from_loop(loop: Path) -> list[Path]:
    """Prefer output/*-object-transfer.xml; fall back to .zip."""
    output = Path(loop) / "output"
    xmls = sorted(output.glob("*-object-transfer.xml"))
    if xmls:
        return xmls
    zips = sorted(output.glob("*-object-transfer.zip"))
    if zips:
        return zips
    raise FileNotFoundError(f"No Object Transfer XML/ZIP under {output}")


def collect_transfer_paths(
    *,
    loop: Path | None = None,
    xmls: list[Path] | None = None,
    zips: list[Path] | None = None,
) -> list[Path]:
    paths: list[Path] = list(xmls or []) + list(zips or [])
    if loop:
        paths.extend(packages_from_loop(loop))
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(path)
    if not unique:
        raise FileNotFoundError("Provide --xml, --zip, and/or --loop")
    return unique


def format_mutation_messages(messages: list[dict[str, Any]] | None) -> str:
    if not messages:
        return ""
    parts: list[str] = []
    for msg in messages:
        proc = msg.get("procedure") or ""
        kind = msg.get("msgType") or ""
        text = msg.get("msgText") or ""
        label = " ".join(p for p in (proc, kind) if p)
        parts.append(f"{label}: {text}".strip(": ").strip())
    return "; ".join(parts)


def _is_auth_failure(message: str, status_code: int | None = None) -> bool:
    if status_code in (401, 403):
        return True
    upper = message.upper()
    return any(
        token in upper
        for token in (
            "UNAUTHORIZED",
            "ACCESS_DENIED",
            "ADMIN GRAPHQL ACCESS TOKEN",
        )
    )


def _looks_like_legacy_admin(data: dict[str, Any]) -> bool:
    if data.get("adminBaseUrl") or data.get("admin_base_url") or data.get("adminUrl"):
        return True
    if "siteId" in data or "credentials" in data:
        return True
    return False


@dataclass
class ConnectionConfig:
    xeelo_url: str
    token: str
    path: Path | None = None

    @classmethod
    def load(cls, path: Path) -> "ConnectionConfig":
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"{path}: connection file must be a JSON object")
        if _looks_like_legacy_admin(data):
            raise ValueError(f"{path}: {NEW_FORMAT_HELP}")
        xeelo = data.get("xeeloUrl")
        token = data.get("token")
        if not xeelo or not str(xeelo).strip():
            raise ValueError(f"{path}: missing xeeloUrl. {NEW_FORMAT_HELP}")
        if not token or not str(token).strip():
            raise ValueError(f"{path}: missing token. {NEW_FORMAT_HELP}")
        return cls(
            xeelo_url=str(xeelo).rstrip("/"),
            token=str(token).strip(),
            path=path,
        )

    @property
    def graphql_url(self) -> str:
        return _join_url(self.xeelo_url, "/graphql")

    @property
    def health_url(self) -> str:
        return _join_url(self.xeelo_url, "/graphql-api/health")


@dataclass
class TransferResult:
    object_setup_xml_id: int
    filename: str
    only_test: bool
    success: bool
    messages: list[dict[str, Any]] = field(default_factory=list)


class XeeloGraphqlClient:
    def __init__(self, config: ConnectionConfig, *, timeout: float = DEFAULT_TIMEOUT_SECONDS):
        httpx_mod = _require_httpx()
        self.config = config
        self.timeout = timeout
        self._client = httpx_mod.Client(
            timeout=httpx_mod.Timeout(timeout, connect=30.0),
            follow_redirects=True,
            headers={
                "Authorization": f"Bearer {config.token}",
                "Content-Type": "application/json",
            },
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "XeeloGraphqlClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def request(self, document: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            resp = self._client.post(
                self.config.graphql_url,
                json={"query": document, "variables": variables or {}},
            )
        except Exception as exc:
            raise GraphqlError(f"GraphQL request failed: {exc}") from exc

        if resp.status_code in (401, 403):
            raise GraphqlAuthError(
                f"GraphQL HTTP {resp.status_code}: {resp.text[:300]}. {AUTH_HINT}"
            )
        if resp.status_code >= 400:
            raise GraphqlError(
                f"GraphQL HTTP {resp.status_code}: {resp.text[:500]}"
            )
        try:
            body = resp.json()
        except Exception as exc:
            raise GraphqlError(f"GraphQL response is not JSON: {exc}") from exc
        errors = body.get("errors") or []
        if errors:
            message = "; ".join(
                str(err.get("message") or err) for err in errors if isinstance(err, dict)
            ) or str(errors)
            if _is_auth_failure(message, resp.status_code):
                raise GraphqlAuthError(f"{message}. {AUTH_HINT}")
            raise GraphqlError(message)
        data = body.get("data")
        if not isinstance(data, dict):
            raise GraphqlError("GraphQL response has no data")
        return data

    def health_ok(self) -> bool:
        try:
            resp = self._client.get(self.config.health_url)
            if resp.status_code == 200:
                return True
        except Exception:
            pass
        try:
            data = self.request(QUERY_HEALTH)
            return data.get("health") not in (None, "")
        except Exception:
            return False


def wait_for_graphql_ready(
    client: XeeloGraphqlClient,
    *,
    timeout_seconds: float = HEALTH_WAIT_SECONDS,
    poll_seconds: float = HEALTH_POLL_SECONDS,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_ok = False
    while True:
        if client.health_ok():
            last_ok = True
            return
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(poll_seconds, remaining))
    if not last_ok:
        raise TimeoutError(
            f"Timed out waiting for GraphQL health at {client.config.health_url} "
            f"after {timeout_seconds}s"
        )


def _transport_interrupt_types() -> tuple[type, ...]:
    httpx_mod = _require_httpx()
    types: list[type] = [httpx_mod.RemoteProtocolError, httpx_mod.ConnectError]
    for name in ("ReadError", "WriteError", "TimeoutException"):
        cls = getattr(httpx_mod, name, None)
        if isinstance(cls, type):
            types.append(cls)
    return tuple(types)


def _is_precompile_interrupt(exc: BaseException) -> bool:
    cause = exc.__cause__
    if cause is not None and isinstance(cause, _transport_interrupt_types()):
        return True
    text = str(exc)
    if "GraphQL request failed" in text:
        return True
    return any(token in text for token in ("GraphQL HTTP 502", "GraphQL HTTP 503", "GraphQL HTTP 504"))


def download_db_transfer_json(
    config: ConnectionConfig,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> str:
    with XeeloGraphqlClient(config, timeout=timeout_seconds) as client:
        data = client.request(QUERY_DOWNLOAD)
    payload = data.get("Select_admin_transfer_download") or {}
    raw = payload.get("json") if isinstance(payload, dict) else None
    if not raw or not str(raw).strip():
        raise GraphqlError("Select_admin_transfer_download returned empty json")
    text = str(raw)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise GraphqlError(
            f"Select_admin_transfer_download returned invalid json: {exc}"
        ) from exc
    if not isinstance(parsed, dict) or isinstance(parsed, list):
        raise GraphqlError("Select_admin_transfer_download json must be an object")
    return text


def push_object_transfer(
    config: ConnectionConfig,
    path: Path,
    *,
    only_test: bool = False,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> TransferResult:
    filename, xml = transfer_path_to_xml(path)
    if not xml.strip():
        raise GraphqlError(f"Empty Object Transfer XML: {path}")
    with XeeloGraphqlClient(config, timeout=timeout_seconds) as client:
        uploaded = client.request(
            MUTATION_UPLOAD,
            {"fileName": filename, "xml": xml},
        )
        raw_id = (uploaded.get("Mutate_admin_transfer_upload") or {}).get("objectSetupXmlId")
        if raw_id is None:
            raise GraphqlError(f"Mutate_admin_transfer_upload returned no objectSetupXmlId for {filename}")
        xml_id = int(raw_id)
        processed = client.request(
            MUTATION_PROCESS,
            {"id": xml_id, "isTestOnly": only_test},
        )
    result = processed.get("Mutate_admin_transfer_process") or {}
    messages = list(result.get("messages") or [])
    success = bool(result.get("success"))
    if not success:
        detail = format_mutation_messages(messages) or "unknown error"
        kind = "test" if only_test else "process"
        raise GraphqlError(
            f"Mutate_admin_transfer_process {kind} failed xmlId={xml_id} {filename}: {detail}"
        )
    return TransferResult(
        object_setup_xml_id=xml_id,
        filename=filename,
        only_test=only_test,
        success=True,
        messages=messages,
    )


def precompile_settings(
    config: ConnectionConfig,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    health_wait_seconds: float = HEALTH_WAIT_SECONDS,
) -> dict[str, Any]:
    interrupted = False
    result: dict[str, Any] | None = None
    with XeeloGraphqlClient(config, timeout=timeout_seconds) as client:
        try:
            data = client.request(MUTATION_PRECOMPILE)
            payload = data.get("Mutate_admin_precompile") or {}
            result = payload if isinstance(payload, dict) else {"success": False}
        except GraphqlAuthError:
            raise
        except GraphqlError as exc:
            if _is_precompile_interrupt(exc):
                interrupted = True
            else:
                raise
        except _transport_interrupt_types():
            interrupted = True

        if result is not None and not result.get("success"):
            detail = format_mutation_messages(result.get("messages")) or "unknown error"
            raise GraphqlError(f"Mutate_admin_precompile failed: {detail}")

        wait_for_graphql_ready(client, timeout_seconds=health_wait_seconds)

    if result is None:
        return {
            "success": True,
            "interrupted": interrupted,
            "messages": [
                {
                    "procedure": "Mutate_admin_precompile",
                    "msgType": "INFO",
                    "msgText": "connection dropped after precompile; GraphQL is healthy again",
                }
            ],
        }
    return {**result, "interrupted": interrupted}


def publish_object_transfers(
    config: ConnectionConfig,
    paths: list[Path],
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> list[TransferResult]:
    results: list[TransferResult] = []
    for path in paths:
        results.append(
            push_object_transfer(
                config,
                path,
                only_test=False,
                timeout_seconds=timeout_seconds,
            )
        )
    precompile_settings(config, timeout_seconds=timeout_seconds)
    return results
