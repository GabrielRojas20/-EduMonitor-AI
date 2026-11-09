"""Carga el contrato OpenAPI del gateway, resuelve sus $ref (incluidos los de analytics.v1.yaml) y lo
convierte a JSON Schema para validar las respuestas del mock."""
import copy
from pathlib import Path

import yaml

CONTRACTS = Path(__file__).resolve().parents[3] / "docs" / "contracts"
GATEWAY = "api-gateway.v1.yaml"
_docs: dict = {}


def load(name: str) -> dict:
    if name not in _docs:
        with open(CONTRACTS / name, encoding="utf-8") as fh:
            _docs[name] = yaml.safe_load(fh)
    return _docs[name]


def _walk(doc: dict, pointer: str):
    node = doc
    for part in pointer.lstrip("/").split("/"):
        node = node[part]
    return node


def resolve(node, base: str):
    """Sustituye cada $ref por su contenido, siguiendo referencias entre archivos."""
    if isinstance(node, dict):
        if "$ref" in node:
            file, _, pointer = node["$ref"].partition("#")
            target_file = file or base
            return resolve(copy.deepcopy(_walk(load(target_file), pointer)), target_file)
        return {k: resolve(v, base) for k, v in node.items()}
    if isinstance(node, list):
        return [resolve(v, base) for v in node]
    return node


def to_jsonschema(node):
    """OpenAPI 3.0 -> JSON Schema: convierte `nullable` y quita palabras que no son de validación."""
    if isinstance(node, list):
        return [to_jsonschema(v) for v in node]
    if not isinstance(node, dict):
        return node
    out = {k: to_jsonschema(v) for k, v in node.items() if k not in ("nullable", "example", "description", "format")}
    if node.get("nullable") is True:
        if "type" in out:
            out["type"] = [out["type"], "null"]
        if "enum" in out:
            out["enum"] = out["enum"] + [None]
    return out


def operations():
    """(ruta, método) de todas las operaciones del contrato del gateway."""
    for path, item in load(GATEWAY)["paths"].items():
        for method in item:
            if method in ("get", "post", "put", "patch", "delete"):
                yield path, method


def response_schema(path: str, method: str, status: int, media: str):
    """JSON Schema de la respuesta documentada, o None si el contrato no documenta ese estado."""
    responses = load(GATEWAY)["paths"][path][method]["responses"]
    if str(status) not in responses:
        return None
    resp = resolve(responses[str(status)], GATEWAY)
    content = resp.get("content", {})
    if media not in content:
        raise AssertionError(f"{method.upper()} {path} {status}: el contrato no declara {media}; declara {list(content)}")
    return to_jsonschema(content[media]["schema"])
