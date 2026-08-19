"""Xeelo Admin API client: token refresh, WebSocket notifications, OT push, precompile."""

from __future__ import annotations

import asyncio
import json
import re
import ssl
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlencode, urlparse, urlunparse

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore

try:
    import websockets
except ImportError:  # pragma: no cover
    websockets = None  # type: ignore


def _require_httpx():
    if httpx is None:
        raise SystemExit("httpx is required: pip install httpx")
    return httpx


def _require_websockets():
    if websockets is None:
        raise SystemExit("websockets is required: pip install websockets")
    return websockets


@dataclass
class ConnectionConfig:
    admin_base_url: str
    site_id: int
    credentials: dict[str, Any]
    path: Path | None = None

    @classmethod
    def load(cls, path: Path) -> "ConnectionConfig":
        data = json.loads(path.read_text(encoding="utf-8"))
        creds = data.get("credentials") or data
        if "access_token" in data and "credentials" not in data:
            creds = {
                k: data[k]
                for k in (
                    "access_token",
                    "refresh_token",
                    "token_type",
                    "expires",
                    "clientId",
                    "rememberMe",
                )
                if k in data
            }
        admin = data.get("adminBaseUrl") or data.get("admin_base_url") or data.get("adminUrl")
        site = data.get("siteId")
        if not admin:
            raise ValueError(f"Missing adminBaseUrl in {path}")
        if site is None:
            raise ValueError(f"Missing siteId in {path}")
        return cls(
            admin_base_url=str(admin).rstrip("/"),
            site_id=int(site),
            credentials=creds,
            path=path,
        )

    def save(self) -> None:
        if not self.path:
            raise ValueError("ConnectionConfig has no path to save")
        payload = {
            "adminBaseUrl": self.admin_base_url,
            "siteId": self.site_id,
            "credentials": self.credentials,
        }
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    @property
    def access_token(self) -> str:
        token = self.credentials.get("access_token")
        if not token:
            raise ValueError("credentials.access_token is missing")
        return str(token)

    @property
    def refresh_token(self) -> str:
        token = self.credentials.get("refresh_token")
        if not token:
            raise ValueError("credentials.refresh_token is missing")
        return str(token)

    @property
    def client_id(self) -> str:
        return str(self.credentials.get("clientId") or "XeeloApp")

    def token_expired(self, skew_seconds: int = 60) -> bool:
        expires = self.credentials.get("expires")
        if not expires:
            return True
        try:
            # Admin uses .NET-style timestamps, sometimes with 7 fractional digits.
            text = str(expires).rstrip("Z")
            if "." in text:
                head, frac = text.split(".", 1)
                frac = "".join(ch for ch in frac if ch.isdigit())[:6].ljust(6, "0")
                text = f"{head}.{frac}"
            dt = datetime.fromisoformat(text).replace(tzinfo=timezone.utc)
        except ValueError:
            return True
        return datetime.now(timezone.utc).timestamp() >= dt.timestamp() - skew_seconds


def ws_url_for_admin(admin_base_url: str, access_token: str) -> str:
    parsed = urlparse(admin_base_url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    netloc = parsed.netloc
    path = "/api/ws"
    query = urlencode({"access_token": access_token})
    return urlunparse((scheme, netloc, path, "", query, ""))


class AdminClient:
    def __init__(self, config: ConnectionConfig, *, timeout: float = 120.0):
        self.config = config
        self.timeout = timeout
        httpx_mod = _require_httpx()
        self._client = httpx_mod.Client(timeout=timeout, follow_redirects=True)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "AdminClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _auth_headers(self, *, include_site: bool = True) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {self.config.access_token}"}
        if include_site:
            headers["XA-SITE-ID"] = str(self.config.site_id)
        return headers

    def refresh_access_token(self, *, force: bool = False) -> dict[str, Any]:
        if not force and not self.config.token_expired():
            return self.config.credentials
        body = {
            "grant_type": "refresh_token",
            "client_id": self.config.client_id,
            "refresh_token": self.config.refresh_token,
        }
        resp = self._client.post(
            f"{self.config.admin_base_url}/token",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"Token refresh failed ({resp.status_code}): {resp.text[:500]}")
        data = resp.json()
        self.config.credentials = {
            **self.config.credentials,
            **data,
        }
        if self.config.path:
            self.config.save()
        return self.config.credentials

    def start_db_transfer_download(self) -> Any:
        resp = self._client.get(
            f"{self.config.admin_base_url}/api/SiteAdmin/XeeloSetup",
            headers=self._auth_headers(include_site=True),
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"XeeloSetup download start failed ({resp.status_code}): {resp.text[:500]}")
        try:
            return resp.json()
        except Exception:
            return {"raw": resp.text}

    def download_admin_temp_file(self, temp_file_id: int) -> tuple[bytes, str | None]:
        resp = self._client.get(
            f"{self.config.admin_base_url}/api/SuperAdmin/General/AdminTempFile/{temp_file_id}",
            headers=self._auth_headers(include_site=False),
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"AdminTempFile download failed ({resp.status_code}): {resp.text[:500]}")
        filename = _filename_from_content_disposition(resp.headers.get("content-disposition") or "")
        return resp.content, filename

    def upload_object_transfer_zip(self, zip_path: Path) -> Any:
        zip_path = Path(zip_path)
        with zip_path.open("rb") as fh:
            resp = self._client.post(
                f"{self.config.admin_base_url}/api/SiteAdmin/XeeloObjectTransfer/Upload",
                headers=self._auth_headers(include_site=True),
                files={zip_path.name: (zip_path.name, fh, "application/zip")},
            )
        if resp.status_code >= 400:
            raise RuntimeError(f"Object Transfer upload failed ({resp.status_code}): {resp.text[:500]}")
        return _json_or_raw(resp)

    def list_object_transfers(self) -> list["ObjectTransferRow"]:
        resp = self._client.get(
            f"{self.config.admin_base_url}/api/SiteAdmin/XeeloObjectTransfer/GridModel",
            headers=self._auth_headers(include_site=True),
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"Object Transfer GridModel failed ({resp.status_code}): {resp.text[:500]}")
        return parse_object_transfer_grid(resp.json())

    def process_object_transfer(self, xml_id: int, *, only_test: bool = False) -> Any:
        resp = self._client.put(
            f"{self.config.admin_base_url}/api/SiteAdmin/XeeloObjectTransfer/Process",
            params={"xmlId": xml_id, "onlyTest": str(only_test).lower()},
            headers=self._auth_headers(include_site=True),
            content=b"",
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"Object Transfer process failed ({resp.status_code}): {resp.text[:500]}")
        data = _json_or_raw(resp)
        _raise_for_info_msg(data, f"Object Transfer process xmlId={xml_id}")
        return data

    def precompile_settings(self) -> Any:
        resp = self._client.post(
            f"{self.config.admin_base_url}/api/SiteAdmin/PreCompileSettings",
            headers=self._auth_headers(include_site=True),
            content=b"",
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"PreCompileSettings failed ({resp.status_code}): {resp.text[:500]}")
        return _json_or_raw(resp)


PROCESS_STATUS_PENDING = "Pending"
PROCESS_STATUS_PROCESSING = "Processing"
PROCESS_STATUS_COMPLETED = "Completed"
PROCESS_STATUS_FAILED = "Failed"
PROCESS_STATUS_TERMINAL = frozenset({PROCESS_STATUS_COMPLETED, PROCESS_STATUS_FAILED})

GRID_COL_FILENAME = "COL1_T1_8_File name"
GRID_COL_TEST_STATUS = "COL1_T9_1_Status"
GRID_COL_PROCESS_STATUS = "COL1_T10_2_Status"
GRID_COL_MESSAGE = "COL1_B1_12_Message"


@dataclass
class ObjectTransferRow:
    xml_id: int
    filename: str
    process_status: str
    test_status: str
    message: str
    color: str
    raw: dict[str, Any]


def _filename_from_content_disposition(cd: str) -> str | None:
    """Parse Content-Disposition; prefer filename*=UTF-8''... over filename=."""
    if not cd:
        return None
    # RFC 5987: filename*=UTF-8''encoded-name
    m = re.search(r"filename\*\s*=\s*([^']*)''([^;]+)", cd, flags=re.IGNORECASE)
    if m:
        return unquote(m.group(2).strip().strip('"'))
    m = re.search(r'filename\s*=\s*"([^"]+)"', cd, flags=re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r"filename\s*=\s*([^;]+)", cd, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip().strip('"')
    return None


def _json_or_raw(resp: Any) -> Any:
    try:
        return resp.json()
    except Exception:
        return {"raw": getattr(resp, "text", "")}


def _info_msg_type(data: Any) -> str:
    if not isinstance(data, dict):
        return ""
    return str(data.get("MsgType") or data.get("msgType") or "").lower()


def _info_msg_text(data: Any) -> str:
    if not isinstance(data, dict):
        return ""
    return str(data.get("MsgText") or data.get("msgText") or data.get("Message") or "")


def _raise_for_info_msg(data: Any, context: str) -> None:
    msg_type = _info_msg_type(data)
    msg_text = _info_msg_text(data)
    if msg_type in ("danger", "error"):
        raise RuntimeError(f"{context}: {msg_text or 'unknown error'}")
    if msg_type == "warning" and "already ongoing" in msg_text.lower():
        raise RuntimeError(f"{context}: {msg_text}")


def _grid_table_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []
    table = payload.get("DataTable")
    if table is None:
        table = payload.get("dataTable")
    if isinstance(table, list):
        return [row for row in table if isinstance(row, dict)]
    if isinstance(table, dict):
        nested = table.get("Table") or table.get("Rows") or table.get("rows")
        if isinstance(nested, list):
            return [row for row in nested if isinstance(row, dict)]
    return []


def _row_value(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row:
            return row[key]
    lowered = {str(k).lower(): v for k, v in row.items()}
    for key in keys:
        found = lowered.get(key.lower())
        if found is not None:
            return found
    return None


def parse_object_transfer_grid(payload: Any) -> list[ObjectTransferRow]:
    """Parse Admin GridModel JSON into Object Transfer rows."""
    rows: list[ObjectTransferRow] = []
    for raw in _grid_table_rows(payload):
        xml_id = _row_value(raw, "ID", "id")
        if xml_id is None:
            continue
        try:
            parsed_id = int(xml_id)
        except (TypeError, ValueError):
            continue
        filename = str(
            _row_value(raw, "SHORT", GRID_COL_FILENAME, "ObjectSetupXMLFileName") or ""
        )
        process_status = str(_row_value(raw, GRID_COL_PROCESS_STATUS) or "")
        test_status = str(_row_value(raw, GRID_COL_TEST_STATUS) or "")
        message = str(_row_value(raw, GRID_COL_MESSAGE, "ObjectSetupXMLStatusMessage") or "")
        color = str(_row_value(raw, "COLOR", "Color") or "")
        rows.append(
            ObjectTransferRow(
                xml_id=parsed_id,
                filename=filename,
                process_status=process_status,
                test_status=test_status,
                message=message,
                color=color,
                raw=raw,
            )
        )
    return rows


def newest_object_transfer_row(
    rows: list[ObjectTransferRow],
    *,
    known_ids: set[int] | None = None,
) -> ObjectTransferRow | None:
    """Pick the newest grid row, preferring IDs not in known_ids."""
    if not rows:
        return None
    if known_ids:
        fresh = [row for row in rows if row.xml_id not in known_ids]
        if fresh:
            return max(fresh, key=lambda row: row.xml_id)
    return max(rows, key=lambda row: row.xml_id)


def is_terminal_process_status(status: str) -> bool:
    return status in PROCESS_STATUS_TERMINAL


def _ids_match(task_id: str | None, msg_id: Any) -> bool:
    return not (task_id and msg_id and str(msg_id) != str(task_id))


async def wait_for_notification(
    *,
    ws_url: str,
    success_type: str,
    timeout_seconds: float = 3600.0,
    ping_period: float = 30.0,
    failure_message: str = "Admin task failed",
    require_temp_file_id: bool = False,
) -> dict[str, Any]:
    """Connect to Admin WS and wait for success_type Success or matching Failed."""
    ws_mod = _require_websockets()
    ssl_ctx = ssl.create_default_context() if ws_url.startswith("wss://") else None
    fail_type = "Task" if success_type in ("TempFile", "Task") else success_type

    async with ws_mod.connect(ws_url, ssl=ssl_ctx, max_size=8 * 1024 * 1024) as ws:
        deadline = asyncio.get_event_loop().time() + timeout_seconds
        task_id: str | None = None

        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                raise TimeoutError(f"Timed out waiting for {success_type} after {timeout_seconds}s")

            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=min(remaining, ping_period))
            except asyncio.TimeoutError:
                await ws.send(json.dumps("ping"))
                continue

            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="replace")
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(msg, dict):
                continue

            msg_type = msg.get("Type")
            status = msg.get("Status")
            msg_id = msg.get("ID")

            if status == "InProgress" and (
                msg_type == success_type or (success_type == "TempFile" and msg_type == "Task")
            ):
                task_id = str(msg_id) if msg_id else task_id
                continue

            if msg_type == success_type and status == "Success":
                if not _ids_match(task_id, msg_id):
                    continue
                if require_temp_file_id:
                    params = msg.get("Params") or {}
                    if "id" not in params:
                        raise RuntimeError(f"TempFile success without Params.id: {msg}")
                return msg

            if msg_type == fail_type and status == "Failed":
                if not _ids_match(task_id, msg_id):
                    continue
                detail = msg.get("Detail") or msg.get("Message") or "unknown"
                raise RuntimeError(f"{failure_message}: {detail}")


async def wait_for_temp_file(
    *,
    ws_url: str,
    timeout_seconds: float = 3600.0,
    ping_period: float = 30.0,
) -> dict[str, Any]:
    """Connect to Admin WS and wait for TempFile success or Task failure."""
    return await wait_for_notification(
        ws_url=ws_url,
        success_type="TempFile",
        timeout_seconds=timeout_seconds,
        ping_period=ping_period,
        failure_message="DB transfer preparation failed",
        require_temp_file_id=True,
    )


async def wait_for_process_status(
    client: AdminClient,
    xml_id: int,
    *,
    timeout_seconds: float = 3600.0,
    poll_period: float = 5.0,
) -> ObjectTransferRow:
    deadline = asyncio.get_event_loop().time() + timeout_seconds
    last: ObjectTransferRow | None = None
    while True:
        rows = client.list_object_transfers()
        last = next((row for row in rows if row.xml_id == xml_id), None)
        if last is not None and is_terminal_process_status(last.process_status):
            if last.process_status == PROCESS_STATUS_FAILED:
                raise RuntimeError(
                    f"Object Transfer xmlId={xml_id} failed: {last.message or 'unknown'}"
                )
            return last
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            status = last.process_status if last else "missing"
            raise TimeoutError(
                f"Timed out waiting for Object Transfer xmlId={xml_id} "
                f"(status={status!r}) after {timeout_seconds}s"
            )
        await asyncio.sleep(min(poll_period, remaining))


def download_db_transfer_zip(
    config: ConnectionConfig,
    *,
    timeout_seconds: float = 3600.0,
) -> tuple[bytes, str]:
    """Full orchestrator: refresh → WS → start → wait → AdminTempFile."""
    with AdminClient(config) as client:
        client.refresh_access_token(force=config.token_expired())
        token = client.config.access_token
        ws_url = ws_url_for_admin(config.admin_base_url, token)

        async def _run() -> tuple[bytes, str]:
            wait_task = asyncio.create_task(
                wait_for_temp_file(ws_url=ws_url, timeout_seconds=timeout_seconds)
            )
            # Give WS a moment to connect before starting async prep.
            await asyncio.sleep(0.5)
            client.start_db_transfer_download()
            msg = await wait_task
            temp_id = int((msg.get("Params") or {})["id"])
            filename = msg.get("Message") or f"db-transfer-{temp_id}.zip"
            data, header_name = client.download_admin_temp_file(temp_id)
            return data, header_name or filename

        return asyncio.run(_run())


def push_object_transfer_zip(
    config: ConnectionConfig,
    zip_path: Path,
    *,
    timeout_seconds: float = 3600.0,
    poll_period: float = 5.0,
    only_test: bool = False,
) -> ObjectTransferRow:
    """Upload OT ZIP, wait for parse WS, process, poll grid until Completed/Failed."""
    zip_path = Path(zip_path)
    if not zip_path.is_file():
        raise FileNotFoundError(f"Object Transfer ZIP not found: {zip_path}")

    http_timeout = max(120.0, min(timeout_seconds, 3600.0))
    with AdminClient(config, timeout=http_timeout) as client:
        client.refresh_access_token(force=config.token_expired())
        ws_url = ws_url_for_admin(config.admin_base_url, client.config.access_token)

        async def _run() -> ObjectTransferRow:
            known_ids = {row.xml_id for row in client.list_object_transfers()}
            wait_task = asyncio.create_task(
                wait_for_notification(
                    ws_url=ws_url,
                    success_type="Task",
                    timeout_seconds=timeout_seconds,
                    failure_message="Object Transfer upload failed",
                )
            )
            await asyncio.sleep(0.5)
            client.upload_object_transfer_zip(zip_path)
            await wait_task

            row = newest_object_transfer_row(
                client.list_object_transfers(),
                known_ids=known_ids,
            )
            if row is None:
                raise RuntimeError(
                    f"Upload succeeded but GridModel has no Object Transfer for {zip_path.name}"
                )

            client.process_object_transfer(row.xml_id, only_test=only_test)
            return await wait_for_process_status(
                client,
                row.xml_id,
                timeout_seconds=timeout_seconds,
                poll_period=poll_period,
            )

        return asyncio.run(_run())


def publish_site(
    config: ConnectionConfig,
    *,
    timeout_seconds: float = 3600.0,
) -> dict[str, Any]:
    """Start PreCompileSettings and wait for Compile WS success."""
    http_timeout = max(120.0, min(timeout_seconds, 3600.0))
    with AdminClient(config, timeout=http_timeout) as client:
        client.refresh_access_token(force=config.token_expired())
        ws_url = ws_url_for_admin(config.admin_base_url, client.config.access_token)

        async def _run() -> dict[str, Any]:
            wait_task = asyncio.create_task(
                wait_for_notification(
                    ws_url=ws_url,
                    success_type="Compile",
                    timeout_seconds=timeout_seconds,
                    failure_message="PreCompileSettings failed",
                )
            )
            await asyncio.sleep(0.5)
            client.precompile_settings()
            return await wait_task

        return asyncio.run(_run())
