"""Client generation and automated syntax/smoke testing."""

from __future__ import annotations

import ast
import hashlib
import keyword
import re
from pathlib import Path

from raa.domain.api import ClientGenerationResult, OpenAPISpec
from raa.utils.ids import new_id
from raa.utils.time import utc_now


def _sanitize_docstring(text: str) -> str:
    """Escape characters that could break out of a triple-quoted docstring."""
    return (
        text.replace("\\", "\\\\").replace('"""', '\\"\\"\\"').replace("\r", " ").replace("\n", " ")
    )


def _sanitize_ident(name: str) -> str:
    """Sanitize a name to be a valid Python identifier."""
    clean = re.sub(r"[^a-zA-Z0-9_]+", "_", name).strip("_").lower()
    if not clean or clean[0].isdigit():
        clean = f"op_{clean}"
    if keyword.iskeyword(clean):
        clean = f"{clean}_"
    return clean


def _make_method_name(method: str, path_template: str) -> str:
    """Generate an idiomatic Python method name from HTTP method and path."""
    clean_path = path_template.replace("{", "").replace("}", "")
    parts = [p for p in clean_path.split("/") if p]
    if not parts:
        return f"{method.lower()}_root"
    joined = "_".join(parts)
    return _sanitize_ident(f"{method.lower()}_{joined}")


def generate_python_client(
    spec: OpenAPISpec,
    output_dir: Path,
) -> ClientGenerationResult:
    """Generate an idiomatic typed Python client from an OpenAPI specification."""
    output_dir.mkdir(parents=True, exist_ok=True)
    spec_bytes = (spec.raw_yaml or "").encode("utf-8")
    spec_digest = hashlib.sha256(spec_bytes).hexdigest()

    base_url_val = spec.servers[0]["url"] if spec.servers else "https://api.example.com"
    # Generate client code
    lines: list[str] = [
        '"""Auto-generated API client produced by RAA API Reverse-Engineering Studio.',
        "",
        f"Spec Title: {_sanitize_docstring(spec.title)}",
        f"Spec Version: {_sanitize_docstring(spec.version)}",
        f"Spec Digest: {spec_digest[:16]}",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "from typing import Any, Optional",
        "",
        "",
        "class APIClient:",
        '    """Typed client for interacting with reverse-engineered endpoints."""',
        "",
        "    def __init__(",
        "        self,",
        f"        base_url: str = {base_url_val!r},",
        "        api_key: Optional[str] = None,",
        "        bearer_token: Optional[str] = None,",
        "        mock: bool = True,",
        "    ) -> None:",
        "        self.base_url = base_url.rstrip('/')",
        "        self.api_key = api_key",
        "        self.bearer_token = bearer_token",
        "        self.mock = mock",
        "        self._session_headers: dict[str, str] = {}",
        "        if self.bearer_token:",
        '            self._session_headers["Authorization"] = f"Bearer {self.bearer_token}"',
        "        if self.api_key:",
        '            self._session_headers["X-API-Key"] = self.api_key',
        "",
        "    def _get_headers(self, extra: Optional[dict[str, str]] = None) -> dict[str, str]:",
        "        h = dict(self._session_headers)",
        "        if extra:",
        "            h.update(extra)",
        "        return h",
        "",
    ]

    for path, methods in spec.paths.items():
        for method, op_def in methods.items():
            op_id = op_def.get("operationId", "")
            func_name = _make_method_name(method, path)
            params = op_def.get("parameters", [])

            # Parameter list
            path_params = [p["name"] for p in params if p.get("in") == "path"]
            query_params = [p["name"] for p in params if p.get("in") == "query"]

            args_sig = ["self"]
            for pp in path_params:
                args_sig.append(f"{_sanitize_ident(pp)}: Any")
            if method in ("post", "put", "patch"):
                args_sig.append("data: Optional[dict[str, Any]] = None")
            for qp in query_params:
                args_sig.append(f"{_sanitize_ident(qp)}: Optional[Any] = None")

            sig_str = ", ".join(args_sig)

            # Sample response
            content_dict = (
                op_def.get("responses", {})
                .get("200", {})
                .get("content", {})
                .get("application/json", {})
            )
            sample_schema = content_dict.get("schema", {"type": "object"})
            sample_repr = repr(sample_schema.get("example", {"status": "ok", "mock": True}))

            lines.extend(
                [
                    f"    def {func_name}({sig_str}) -> dict[str, Any]:",
                    f'        """{_sanitize_docstring(method.upper())} {_sanitize_docstring(path)} (Operation: {_sanitize_docstring(op_id)})"""',
                    f"        url_template = {path!r}",
                ]
            )

            for pp in path_params:
                clean_pp = _sanitize_ident(pp)
                lines.append(
                    f"        url_template = url_template.replace({'{' + pp + '}'!r}, str({clean_pp}))"
                )

            lines.extend(
                [
                    '        full_url = f"{self.base_url}{url_template}"',
                    "        if self.mock:",
                    f"            return {sample_repr}",
                    (
                        f'        return {{"status": "dispatched", "url": full_url, '
                        f'"method": {method.upper()!r}}}'
                    ),
                    "",
                ]
            )

    client_code = "\n".join(lines)
    client_file = output_dir / "client.py"
    client_file.write_text(client_code, encoding="utf-8")

    init_file = output_dir / "__init__.py"
    init_content = (
        '"""Generated API client package."""\n'
        "from .client import APIClient\n\n"
        '__all__ = ["APIClient"]\n'
    )
    init_file.write_text(init_content, encoding="utf-8")

    # 1. Compile test: verify syntax compiles cleanly
    compiles = True
    try:
        compile(client_code, str(client_file), "exec")
    except Exception:
        compiles = False

    # 2. Smoke test: verify AST structure defines APIClient cleanly without exec()
    smoke_passed = False
    if compiles:
        try:
            tree = ast.parse(client_code, filename=str(client_file))
            api_client_cls = next(
                (
                    node
                    for node in tree.body
                    if isinstance(node, ast.ClassDef) and node.name == "APIClient"
                ),
                None,
            )
            if api_client_cls is not None and any(
                isinstance(m, ast.FunctionDef) and m.name == "__init__" for m in api_client_cls.body
            ):
                smoke_passed = True
        except Exception:
            smoke_passed = False

    client_id = new_id("client")
    return ClientGenerationResult(
        client_id=client_id,
        project_id=spec.project_id,
        language="python",
        spec_digest=spec_digest,
        target_dir=str(output_dir),
        files_written=[str(client_file), str(init_file)],
        compiles=compiles,
        smoke_test_passed=smoke_passed,
        created_at=utc_now(),
    )
