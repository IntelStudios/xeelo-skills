"""Tests for Xeelo GraphQL connection, XML helpers, and transfer client."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ot_builder.graphql_client import (  # noqa: E402
    AUTH_HINT,
    PERMISSION_FULL,
    PERMISSION_READ_ONLY,
    PERMISSION_READ_WRITE,
    ConnectionConfig,
    ConnectionPermissionError,
    GraphqlAuthError,
    GraphqlError,
    MUTATION_UPLOAD,
    MUTATION_BACKUP,
    QUERY_DOWNLOAD,
    XeeloGraphqlClient,
    collect_transfer_paths,
    decode_transfer_xml_bytes,
    download_db_transfer_json,
    backup_admin_transfer,
    packages_from_loop,
    precompile_settings,
    push_object_transfer,
    transfer_path_to_json,
    transfer_path_to_xml,
    xml_to_utf16_le_bytes,
)


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | str):
        self.status_code = status_code
        self._payload = payload
        self.text = payload if isinstance(payload, str) else json.dumps(payload)

    def json(self) -> dict:
        if isinstance(self._payload, dict):
            return self._payload
        raise ValueError("not json")


class _FakeHttp:
    def __init__(self, responses: list[_FakeResponse]):
        self.responses = list(responses)
        self.posts: list[dict] = []

    def post(self, url, json=None):
        self.posts.append({"url": url, "json": json})
        return self.responses.pop(0)

    def get(self, url):
        return _FakeResponse(503, "down")

    def close(self) -> None:
        return None


class ConnectionConfigTests(unittest.TestCase):
    def _write(self, payload: dict) -> Path:
        tmp = Path(tempfile.mkdtemp()) / ".xeelo-connection.json"
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        return tmp

    def test_loads_xeelo_url_and_token(self) -> None:
        path = self._write(
            {"xeeloUrl": "https://example.xeelo.online/", "token": "secret-admin"}
        )
        config = ConnectionConfig.load(path)
        self.assertEqual(config.xeelo_url, "https://example.xeelo.online")
        self.assertEqual(config.token, "secret-admin")
        self.assertEqual(config.permission, PERMISSION_READ_ONLY)
        self.assertFalse(config.can_write)
        self.assertFalse(config.can_precompile)
        self.assertEqual(config.graphql_url, "https://example.xeelo.online/graphql")
        self.assertEqual(config.health_url, "https://example.xeelo.online/graphql-api/health")

    def test_rejects_url_alias(self) -> None:
        path = self._write({"url": "https://demo.xeelo.online", "token": "t"})
        with self.assertRaisesRegex(ValueError, "missing xeeloUrl"):
            ConnectionConfig.load(path)

    def test_rejects_empty_token(self) -> None:
        path = self._write({"xeeloUrl": "https://example.xeelo.online/", "token": ""})
        with self.assertRaisesRegex(ValueError, "missing token"):
            ConnectionConfig.load(path)

    def test_optional_ui_fields_empty_or_omitted(self) -> None:
        path = self._write(
            {
                "xeeloUrl": "https://example.xeelo.online/",
                "token": "secret-admin",
                "userLogin": "",
                "userPwd": "  ",
                "ignoredExtra": True,
            }
        )
        config = ConnectionConfig.load(path)
        self.assertIsNone(config.user_login)
        self.assertIsNone(config.user_pwd)
        self.assertFalse(config.has_ui_login)
        with self.assertRaisesRegex(ValueError, "missing userLogin/userPwd"):
            config.require_ui_login()

    def test_loads_ui_login_and_redacts_password_in_repr(self) -> None:
        path = self._write(
            {
                "xeeloUrl": "https://example.xeelo.online/",
                "token": "secret-admin",
                "userLogin": "tester",
                "userPwd": "super-secret-password",
            }
        )
        config = ConnectionConfig.load(path)
        self.assertEqual(config.user_login, "tester")
        self.assertEqual(config.user_pwd, "super-secret-password")
        self.assertEqual(config.require_ui_login(), ("tester", "super-secret-password"))
        text = repr(config)
        self.assertNotIn("super-secret-password", text)
        self.assertNotIn("secret-admin", text)
        self.assertIn("user_pwd=<set>", text)
        self.assertIn("permission='read-only'", text)

    def test_permission_missing_or_empty_defaults_read_only(self) -> None:
        path = self._write(
            {"xeeloUrl": "https://example.xeelo.online/", "token": "t", "permission": "  "}
        )
        config = ConnectionConfig.load(path)
        self.assertEqual(config.permission, PERMISSION_READ_ONLY)
        with self.assertRaisesRegex(ConnectionPermissionError, "read-only"):
            config.require_write()
        with self.assertRaisesRegex(ConnectionPermissionError, "needs full"):
            config.require_precompile()

    def test_permission_read_write_and_full(self) -> None:
        path = self._write(
            {
                "xeeloUrl": "https://example.xeelo.online/",
                "token": "t",
                "permission": PERMISSION_READ_WRITE,
            }
        )
        rw = ConnectionConfig.load(path)
        self.assertTrue(rw.can_write)
        self.assertFalse(rw.can_precompile)
        rw.require_write()
        with self.assertRaisesRegex(ConnectionPermissionError, "needs full"):
            rw.require_precompile()

        path = self._write(
            {
                "xeeloUrl": "https://example.xeelo.online/",
                "token": "t",
                "permission": PERMISSION_FULL,
            }
        )
        full = ConnectionConfig.load(path)
        self.assertTrue(full.can_write)
        self.assertTrue(full.can_precompile)
        full.require_write()
        full.require_precompile()

    def test_permission_invalid_raises(self) -> None:
        path = self._write(
            {
                "xeeloUrl": "https://example.xeelo.online/",
                "token": "t",
                "permission": "admin",
            }
        )
        with self.assertRaisesRegex(ValueError, "invalid permission"):
            ConnectionConfig.load(path)


class XmlHelperTests(unittest.TestCase):
    def test_utf16_roundtrip_with_bom(self) -> None:
        xml = "<XMLData><TransferInfo/></XMLData>"
        data = xml_to_utf16_le_bytes(xml)
        self.assertEqual(data[:2], b"\xff\xfe")
        self.assertEqual(decode_transfer_xml_bytes(data), xml)

    def test_transfer_path_from_xml_and_zip(self) -> None:
        xml = "<XMLData>ok</XMLData>"
        tmp = Path(tempfile.mkdtemp())
        xml_path = tmp / "example-object-transfer.xml"
        xml_path.write_bytes(xml_to_utf16_le_bytes(xml))
        name, text = transfer_path_to_xml(xml_path)
        self.assertEqual(name, "example-object-transfer.xml")
        self.assertEqual(text, xml)

        zip_path = tmp / "example-object-transfer.zip"
        with ZipFile(zip_path, "w", ZIP_DEFLATED) as zf:
            zf.writestr("object-transfer.xml", xml_to_utf16_le_bytes(xml))
        name, text = transfer_path_to_xml(zip_path)
        self.assertEqual(name, "object-transfer.xml")
        self.assertEqual(text, xml)

    def test_packages_from_loop_uses_json(self) -> None:
        loop = Path(tempfile.mkdtemp())
        output = loop / "output"
        output.mkdir()
        json_path = output / "example-object-transfer.json"
        xml_path = output / "example-object-transfer.xml"
        json_path.write_text('{"Object":[{"ObjectID":1}]}', encoding="utf-8")
        xml_path.write_text("<XMLData/>", encoding="utf-8")
        self.assertEqual(packages_from_loop(loop), [json_path])
        self.assertEqual(
            collect_transfer_paths(loop=loop),
            [json_path],
        )

    def test_transfer_path_to_json(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        path = tmp / "example-object-transfer.json"
        path.write_text('{"Object":[{"ObjectID":1,"ObjectName":"A"}]}', encoding="utf-8")
        name, text = transfer_path_to_json(path)
        self.assertEqual(name, "example-object-transfer.json")
        self.assertIn("Object", text)


class GraphqlClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = ConnectionConfig(
            xeelo_url="https://example.xeelo.online",
            token="admin-token",
        )

    def test_request_maps_graphql_errors(self) -> None:
        fake = _FakeHttp(
            [_FakeResponse(200, {"errors": [{"message": "boom"}]})]
        )
        client = XeeloGraphqlClient(self.config)
        client._client = fake  # type: ignore[method-assign]
        with self.assertRaisesRegex(GraphqlError, "boom"):
            client.request("query { health }")

    def test_request_maps_auth_errors(self) -> None:
        fake = _FakeHttp(
            [
                _FakeResponse(
                    200,
                    {
                        "errors": [
                            {
                                "message": "ACCESS_DENIED: This operation requires an admin GraphQL access token"
                            }
                        ]
                    },
                )
            ]
        )
        client = XeeloGraphqlClient(self.config)
        client._client = fake  # type: ignore[method-assign]
        with self.assertRaises(GraphqlAuthError) as ctx:
            client.request("query { health }")
        self.assertIn(AUTH_HINT, str(ctx.exception))

    def test_request_maps_http_401(self) -> None:
        fake = _FakeHttp([_FakeResponse(401, "nope")])
        client = XeeloGraphqlClient(self.config)
        client._client = fake  # type: ignore[method-assign]
        with self.assertRaises(GraphqlAuthError):
            client.request("query { health }")


class DownloadDbTransferJsonTests(unittest.TestCase):
    def test_reads_json_field(self) -> None:
        payload = '{"Company":[],"Object":[]}'
        config = ConnectionConfig(xeelo_url="https://example.xeelo.online", token="t")

        class FakeClient:
            def __init__(self, *_args, **_kwargs):
                return None

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def request(self, document, variables=None):
                seen.append(document)
                return {"Select_admin_transfer_download": {"json": payload}}

        seen: list[str] = []
        with patch("ot_builder.graphql_client.XeeloGraphqlClient", FakeClient):
            text = download_db_transfer_json(config)
        self.assertEqual(text, payload)
        self.assertEqual(seen, [QUERY_DOWNLOAD])
        self.assertIn("json", QUERY_DOWNLOAD)

    def test_rejects_empty_json(self) -> None:
        config = ConnectionConfig(xeelo_url="https://example.xeelo.online", token="t")

        class FakeClient:
            def __init__(self, *_args, **_kwargs):
                return None

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def request(self, document, variables=None):
                return {"Select_admin_transfer_download": {"json": ""}}

        with patch("ot_builder.graphql_client.XeeloGraphqlClient", FakeClient):
            with self.assertRaisesRegex(GraphqlError, "empty json"):
                download_db_transfer_json(config)

    def test_rejects_xml_field_only(self) -> None:
        config = ConnectionConfig(xeelo_url="https://example.xeelo.online", token="t")

        class FakeClient:
            def __init__(self, *_args, **_kwargs):
                return None

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def request(self, document, variables=None):
                return {"Select_admin_transfer_download": {"xml": "<XMLData/>"}}

        with patch("ot_builder.graphql_client.XeeloGraphqlClient", FakeClient):
            with self.assertRaisesRegex(GraphqlError, "empty json"):
                download_db_transfer_json(config)


class PushObjectTransferTests(unittest.TestCase):
    def _json_path(self) -> Path:
        tmp = Path(tempfile.mkdtemp())
        path = tmp / "example-object-transfer.json"
        path.write_text(
            '{"Object":[{"ObjectID":1,"ObjectName":"Account"}]}',
            encoding="utf-8",
        )
        return path

    def test_single_upload_with_is_test(self) -> None:
        json_path = self._json_path()
        config = ConnectionConfig(
            xeelo_url="https://example.xeelo.online",
            token="t",
            permission=PERMISSION_READ_WRITE,
        )
        calls: list[tuple[str, dict | None]] = []

        class FakeClient:
            def __init__(self, *_args, **_kwargs):
                return None

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def request(self, document, variables=None):
                calls.append((document, variables))
                if document == MUTATION_UPLOAD:
                    return {
                        "Mutate_admin_transfer_upload": {
                            "success": True,
                            "messages": [],
                        }
                    }
                raise AssertionError(document)

        with patch("ot_builder.graphql_client.XeeloGraphqlClient", FakeClient):
            result = push_object_transfer(config, json_path, only_test=True)

        self.assertTrue(result.success)
        self.assertTrue(result.only_test)
        self.assertEqual(result.filename, "example-object-transfer.json")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], MUTATION_UPLOAD)
        self.assertEqual(calls[0][1]["isTest"], True)
        self.assertIn("Object", calls[0][1]["json"])

        calls.clear()
        with patch("ot_builder.graphql_client.XeeloGraphqlClient", FakeClient):
            push_object_transfer(config, json_path, only_test=False)
        self.assertEqual(calls[0][1]["isTest"], False)

    def test_upload_failure_raises(self) -> None:
        json_path = self._json_path()
        config = ConnectionConfig(
            xeelo_url="https://example.xeelo.online",
            token="t",
            permission=PERMISSION_READ_WRITE,
        )

        class FakeClient:
            def __init__(self, *_args, **_kwargs):
                return None

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def request(self, document, variables=None):
                return {
                    "Mutate_admin_transfer_upload": {
                        "success": False,
                        "messages": [
                            {
                                "procedure": "dbo.spAdminObjectSetupJSONProcess",
                                "msgType": "DANGER",
                                "msgText": "bad row",
                            }
                        ],
                    }
                }

        with patch("ot_builder.graphql_client.XeeloGraphqlClient", FakeClient):
            with self.assertRaisesRegex(GraphqlError, "bad row"):
                push_object_transfer(config, json_path, only_test=True)

    def test_read_only_blocks_dry_run_and_apply(self) -> None:
        json_path = self._json_path()
        config = ConnectionConfig(
            xeelo_url="https://example.xeelo.online",
            token="t",
            permission=PERMISSION_READ_ONLY,
        )
        with self.assertRaisesRegex(ConnectionPermissionError, "read-only"):
            push_object_transfer(config, json_path, only_test=True)
        with self.assertRaisesRegex(ConnectionPermissionError, "read-only"):
            push_object_transfer(config, json_path, only_test=False)

    def test_read_write_allows_apply_but_blocks_precompile(self) -> None:
        json_path = self._json_path()
        config = ConnectionConfig(
            xeelo_url="https://example.xeelo.online",
            token="t",
            permission=PERMISSION_READ_WRITE,
        )

        class FakeClient:
            def __init__(self, *_args, **_kwargs):
                return None

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def request(self, document, variables=None):
                if document == MUTATION_UPLOAD:
                    return {
                        "Mutate_admin_transfer_upload": {
                            "success": True,
                            "messages": [],
                        }
                    }
                raise AssertionError(document)

        with patch("ot_builder.graphql_client.XeeloGraphqlClient", FakeClient):
            result = push_object_transfer(config, json_path, only_test=False)
        self.assertTrue(result.success)
        with self.assertRaisesRegex(ConnectionPermissionError, "needs full"):
            precompile_settings(config)


class BackupAdminTransferTests(unittest.TestCase):
    def test_backup_without_delete_older_than(self) -> None:
        config = ConnectionConfig(
            xeelo_url="https://example.xeelo.online",
            token="t",
            permission=PERMISSION_READ_WRITE,
        )
        calls: list[tuple[str, dict | None]] = []

        class FakeClient:
            def __init__(self, *_args, **_kwargs):
                return None

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def request(self, document, variables=None):
                calls.append((document, variables))
                return {
                    "Mutate_admin_transfer_backup": {
                        "success": True,
                        "messages": [],
                    }
                }

        with patch("ot_builder.graphql_client.XeeloGraphqlClient", FakeClient):
            result = backup_admin_transfer(config)
        self.assertTrue(result["success"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], MUTATION_BACKUP)
        self.assertEqual(calls[0][1], {"deleteOlderThan": None})

    def test_backup_with_delete_older_than(self) -> None:
        config = ConnectionConfig(
            xeelo_url="https://example.xeelo.online",
            token="t",
            permission=PERMISSION_FULL,
        )

        class FakeClient:
            def __init__(self, *_args, **_kwargs):
                return None

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def request(self, document, variables=None):
                seen.append(variables)
                return {"Mutate_admin_transfer_backup": {"success": True, "messages": []}}

        seen: list[dict | None] = []
        with patch("ot_builder.graphql_client.XeeloGraphqlClient", FakeClient):
            backup_admin_transfer(config, delete_older_than=7)
        self.assertEqual(seen, [{"deleteOlderThan": 7}])

    def test_backup_rejects_non_positive_days(self) -> None:
        config = ConnectionConfig(
            xeelo_url="https://example.xeelo.online",
            token="t",
            permission=PERMISSION_READ_WRITE,
        )
        with self.assertRaisesRegex(ValueError, "positive integer"):
            backup_admin_transfer(config, delete_older_than=0)

    def test_read_only_blocks_backup(self) -> None:
        config = ConnectionConfig(
            xeelo_url="https://example.xeelo.online",
            token="t",
            permission=PERMISSION_READ_ONLY,
        )
        with self.assertRaisesRegex(ConnectionPermissionError, "read-only"):
            backup_admin_transfer(config)

    def test_backup_failure_raises(self) -> None:
        config = ConnectionConfig(
            xeelo_url="https://example.xeelo.online",
            token="t",
            permission=PERMISSION_READ_WRITE,
        )

        class FakeClient:
            def __init__(self, *_args, **_kwargs):
                return None

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def request(self, document, variables=None):
                return {
                    "Mutate_admin_transfer_backup": {
                        "success": False,
                        "messages": [
                            {
                                "procedure": "dbo.spAdminDbSetupXMLBackup",
                                "msgType": "DANGER",
                                "msgText": "backup failed",
                            }
                        ],
                    }
                }

        with patch("ot_builder.graphql_client.XeeloGraphqlClient", FakeClient):
            with self.assertRaisesRegex(GraphqlError, "backup failed"):
                backup_admin_transfer(config)


if __name__ == "__main__":
    unittest.main()
