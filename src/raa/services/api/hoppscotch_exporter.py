"""Hoppscotch v2 JSON collection exporter for synthesized mobile APIs."""

from __future__ import annotations

import json
from typing import Any


def export_to_hoppscotch_collection(
    *,
    project_id: str,
    operations: list[dict[str, Any]],
    collection_name: str | None = None,
    base_url: str = "<<baseUrl>>",
) -> str:
    """Convert RAA API operations into a Hoppscotch v2 collection JSON string."""
    requests_list: list[dict[str, Any]] = []
    for op in operations:
        method = str(op.get("method", "GET")).upper()
        path = str(op.get("path", "/api/v1/resource"))
        op_id = str(op.get("operation_id", "operation"))
        auth_scheme = str(op.get("auth", "none")).lower()

        auth: dict[str, Any] = {"authType": "none", "authActive": False}
        if auth_scheme == "bearer":
            auth = {"authType": "bearer", "authActive": True, "token": "<<bearerToken>>"}
        elif auth_scheme == "api_key":
            auth = {
                "authType": "api-key",
                "authActive": True,
                "key": "X-API-Key",
                "value": "<<apiKey>>",
                "addTo": "Headers",
            }

        body: dict[str, Any] = {"contentType": None, "body": None}
        if "sample_body" in op and op["sample_body"] is not None:
            body = {
                "contentType": "application/json",
                "body": json.dumps(op["sample_body"], indent=2),
            }

        requests_list.append(
            {
                "v": "2",
                "name": op_id,
                "method": method,
                "endpoint": f"{base_url.rstrip('/')}/{path.lstrip('/')}",
                "params": [],
                "headers": [],
                "preRequestScript": "",
                "testScript": "",
                "auth": auth,
                "body": body,
            }
        )

    collection: dict[str, Any] = {
        "v": 2,
        "name": collection_name or f"RAA_{project_id}_Hoppscotch",
        "folders": [],
        "requests": requests_list,
        "auth": {"authType": "inherit", "authActive": True},
        "headers": [],
    }
    return json.dumps(collection, indent=2, ensure_ascii=False)
