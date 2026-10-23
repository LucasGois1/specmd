"""Version-bound approval signatures; signing-key possession is not human login.

The authority store is external to the repository. ``initialize_authority`` is
an explicit local-demo operation; inspection and verification never create keys.
Protected trust is provisioned by an operator with permissions unavailable to
the agent. A JSON mode flag alone does not establish that separation.
"""

from __future__ import annotations

import base64
import binascii
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


_DIGEST = re.compile(r"[0-9a-f]{64}")
_PROPOSAL_FIELDS = (
    "schema", "project_id", "repository", "contract_sha256", "manifest", "documents",
)


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ValueError("O conteúdo não possui representação JSON canônica válida.") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{name} deve ser texto não vazio, sem espaços externos.")
    return value


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or _DIGEST.fullmatch(value) is None:
        raise ValueError(f"{name} deve ser um SHA-256 hexadecimal.")
    return value


def _repository(value: Any) -> str:
    if isinstance(value, str) and value.startswith("repo:"):
        identifier = _text(value[5:], "repository_id")
        if any(character.isspace() or ord(character) < 32 or ord(character) == 127
               for character in identifier) or "\\" in identifier or identifier.startswith("/"):
            raise ValueError("repository_id não pode conter espaços, controles ou caminho absoluto.")
        return "repo:" + identifier
    if not isinstance(value, (str, os.PathLike)):
        raise ValueError("repository precisa ser uma identidade repo: ou caminho absoluto.")
    path = Path(value)
    if not path.is_absolute():
        raise ValueError("repository precisa ser um caminho absoluto.")
    return str(path.resolve())


def _outside(path: Path, repository: str, workspace_root: Path | str | None = None) -> Path:
    roots = [] if repository.startswith("repo:") else [Path(repository)]
    if workspace_root is not None:
        workspace = Path(workspace_root)
        if not workspace.is_absolute():
            raise ValueError("workspace_root precisa ser um caminho absoluto.")
        roots.append(workspace.resolve())
    path = Path(path).absolute()
    resolved = path.resolve()
    if any(path.is_relative_to(root) or resolved.is_relative_to(root) for root in roots):
        raise ValueError("A autoridade e o trust precisam ficar fora do repositório.")
    return resolved


def _read_regular(path: Path) -> bytes:
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError("A autoridade exige arquivos regulares, sem links simbólicos.")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        opened = os.fstat(descriptor)
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise ValueError("O arquivo mudou durante a abertura.")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            data = stream.read()
        after = os.fstat(descriptor)
        current = path.lstat()
        signature = lambda item: (item.st_dev, item.st_ino, item.st_size,
                                  item.st_mtime_ns, item.st_ctime_ns)
        if signature(opened) != signature(after) or signature(after) != signature(current):
            raise ValueError("O arquivo mudou durante a leitura.")
        return data
    finally:
        os.close(descriptor)


def _pairs(items: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError(f"Chave JSON duplicada: {key}.")
        result[key] = value
    return result


def _read_json(path: Path) -> dict:
    def invalid_constant(value: str) -> None:
        raise ValueError(f"Constante JSON inválida: {value}.")
    try:
        value = json.loads(_read_regular(path).decode("utf-8"), object_pairs_hook=_pairs,
                           parse_constant=invalid_constant)
    except (OSError, UnicodeError) as exc:
        raise ValueError("Não foi possível ler o registro externo de autoridade.") from exc
    if not isinstance(value, dict):
        raise ValueError("O registro externo precisa ser um objeto JSON.")
    return value


def _decode(value: Any, length: int, name: str) -> bytes:
    try:
        decoded = base64.b64decode(value, validate=True)
    except (TypeError, ValueError, binascii.Error) as exc:
        raise ValueError(f"{name} não contém base64 válido.") from exc
    if len(decoded) != length:
        raise ValueError(f"{name} possui tamanho inválido.")
    return decoded


def _load_trust(path: Path, repository: str, workspace_root: Path | str | None = None) -> dict:
    # Check the supplied path as well as its target, before reading its bytes.
    _outside(path, repository, workspace_root)
    trust = _read_json(Path(path))
    if type(trust.get("schema")) is not int or trust["schema"] != 1:
        raise ValueError("Versão de trust não suportada.")
    if trust.get("mode") not in {"local_demo", "protected"}:
        raise ValueError("O trust precisa declarar local_demo ou protected.")
    if not isinstance(trust.get("keys"), list) or not trust["keys"]:
        raise ValueError("O trust não declara chaves autorizadas.")
    seen = set()
    for record in trust["keys"]:
        if not isinstance(record, dict):
            raise ValueError("Registro de chave inválido.")
        key_id = _sha(record.get("key_id"), "key_id")
        public = _decode(record.get("public_key"), 32, "public_key")
        if hashlib.sha256(public).hexdigest() != key_id or key_id in seen:
            raise ValueError("Identidade de chave inválida ou duplicada.")
        seen.add(key_id)
        if type(record.get("revoked", False)) is not bool:
            raise ValueError("revoked precisa ser booleano.")
        authorizations = record.get("authorizations")
        if not isinstance(authorizations, list) or not authorizations:
            raise ValueError("A chave precisa de autorização explícita de projeto/repositório.")
        for authorization in authorizations:
            if not isinstance(authorization, dict):
                raise ValueError("Escopo de autorização inválido.")
            _text(authorization.get("project_id"), "project_id")
            value = _text(authorization.get("repository"), "repository")
            if _repository(value) != value:
                raise ValueError("O escopo precisa usar o caminho canônico do repositório.")
    if "latest_decisions" in trust:
        registry = trust["latest_decisions"]
        if not isinstance(registry, dict):
            raise ValueError("latest_decisions precisa ser um mapa.")
        for proposal, envelope in registry.items():
            _sha(proposal, "proposal_sha256")
            _sha(envelope, "envelope_sha256")
    return trust


def _authorized_key(trust: dict, key_id: str, project_id: str, repository: str) -> dict:
    record = next((item for item in trust["keys"] if item["key_id"] == key_id), None)
    if record is None:
        raise ValueError("A chave emissora não é confiável.")
    if record.get("revoked", False):
        raise ValueError("A chave emissora foi revogada.")
    if not any(item["project_id"] == project_id and item["repository"] == repository
               for item in record["authorizations"]):
        raise ValueError("A chave não está autorizada para este projeto e repositório.")
    return record


def _document_path(value: Any) -> str:
    value = _text(value, "path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "\\" in value or path.as_posix() != value:
        raise ValueError("O manifesto contém caminho documental inválido.")
    return value


def _manifest(value: Any, contract_sha256: Any) -> dict:
    if not isinstance(value, dict) or type(value.get("schema")) is not int or value["schema"] != 1:
        raise ValueError("Manifesto contratual inválido.")
    _sha(value.get("config_sha256"), "config_sha256")
    if not isinstance(value.get("documents"), list):
        raise ValueError("O manifesto precisa listar documents.")
    paths = []
    for document in value["documents"]:
        if not isinstance(document, dict) or set(document) != {"path", "sha256"}:
            raise ValueError("Entrada documental do manifesto inválida.")
        paths.append(_document_path(document["path"]))
        _sha(document["sha256"], "sha256")
    if paths != sorted(set(paths)):
        raise ValueError("O manifesto precisa de caminhos únicos em ordem determinística.")
    if _digest(value) != _sha(contract_sha256, "contract_sha256"):
        raise ValueError("O hash do contrato não corresponde ao manifesto.")
    return json.loads(_canonical(value))


def _proposal_body(proposal: dict) -> dict:
    if not isinstance(proposal, dict) or any(key not in proposal for key in _PROPOSAL_FIELDS):
        raise ValueError("Proposta de revisão incompleta.")
    body = {key: proposal[key] for key in _PROPOSAL_FIELDS}
    if type(body["schema"]) is not int or body["schema"] != 1:
        raise ValueError("Versão de proposta não suportada.")
    _text(body["project_id"], "project_id")
    if _repository(body["repository"]) != body["repository"]:
        raise ValueError("A proposta precisa do repositório canônico.")
    manifest = _manifest(body["manifest"], body["contract_sha256"])
    if not isinstance(body["documents"], list):
        raise ValueError("A proposta precisa de snapshots documentais.")
    snapshots = []
    for document in body["documents"]:
        if not isinstance(document, dict) or not isinstance(document.get("text"), str):
            raise ValueError("Snapshot documental inválido.")
        snapshot = {key: document.get(key) for key in ("path", "sha256", "text")}
        _document_path(snapshot["path"])
        if hashlib.sha256(snapshot["text"].encode("utf-8")).hexdigest() != _sha(snapshot["sha256"], "sha256"):
            raise ValueError("O texto apresentado não corresponde ao hash documental.")
        snapshots.append(snapshot)
    if [{"path": item["path"], "sha256": item["sha256"]} for item in snapshots] != manifest["documents"]:
        raise ValueError("Os documentos apresentados não correspondem ao manifesto.")
    body["manifest"] = manifest
    body["documents"] = snapshots  # UI annotations are intentionally not signed.
    return json.loads(_canonical(body))


def _validate_proposal(proposal: dict) -> dict:
    body = _proposal_body(proposal)
    digest = _digest(body)
    if proposal.get("id") != digest or proposal.get("proposal_sha256") != digest:
        raise ValueError("A identidade da proposta não corresponde ao conteúdo apresentado.")
    return body


def _new_file(path: Path, data: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as stream:
            stream.write(data)
    finally:
        os.close(descriptor)


def _replace_json(path: Path, value: dict) -> None:
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(_canonical(value) + b"\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def initialize_authority(directory: Path, project_id: str, repository: Path | str,
                         *, mode: str = "local_demo", workspace_root: Path | str | None = None) -> dict:
    """Explicitly create an external demo key; never claim protected identity."""
    project_id = _text(project_id, "project_id")
    repository = _repository(repository)
    if mode != "local_demo":
        raise ValueError("Trust protected deve ser provisionado separadamente pelo operador.")
    directory = Path(directory)
    if directory.is_symlink():
        raise ValueError("O diretório de autoridade não pode ser um link simbólico.")
    directory = _outside(directory, repository, workspace_root)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    private_path, trust_path = directory / "private.key", directory / "trust.json"
    if private_path.exists() or private_path.is_symlink() or trust_path.exists() or trust_path.is_symlink():
        raise ValueError("A autoridade já contém uma chave ou trust; nada foi sobrescrito.")
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    key_id = hashlib.sha256(public).hexdigest()
    trust = {"schema": 1, "mode": mode, "keys": [{
        "key_id": key_id, "public_key": base64.b64encode(public).decode("ascii"),
        "revoked": False, "authorizations": [{"project_id": project_id, "repository": repository}],
    }], "latest_decisions": {}}
    key_data = private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                     serialization.NoEncryption())
    _new_file(private_path, key_data)
    try:
        _new_file(trust_path, _canonical(trust) + b"\n")
    except Exception:
        private_path.unlink(missing_ok=True)
        raise
    return {"mode": mode, "key_id": key_id, "project_id": project_id, "repository": repository,
            "trust_path": str(trust_path), "private_key_path": str(private_path)}


def create_review(root: Path, inspection: dict, config: dict) -> dict:
    """Capture exact reviewed Markdown; an observed snapshot is not approval."""
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("A raiz da revisão precisa ser um diretório.")
    project_id = _text(config.get("project_id"), "project_id")
    repository_id = config.get("repository_id")
    if repository_id is not None:
        repository_id = _text(repository_id, "repository_id")
        if repository_id.startswith("repo:"):
            raise ValueError("repository_id não deve incluir o prefixo repo:.")
        repository = _repository("repo:" + repository_id)
    else:
        repository = str(root)
    manifest = _manifest(inspection.get("manifest"), inspection.get("manifest_sha256"))
    try:
        if hashlib.sha256(_read_regular(root / "specmd.toml")).hexdigest() != manifest["config_sha256"]:
            raise ValueError("A configuração mudou depois da inspeção.")
        documents = []
        for entry in manifest["documents"]:
            path = root / entry["path"]
            if not path.resolve(strict=True).is_relative_to(root):
                raise ValueError("O documento está fora do repositório.")
            raw = _read_regular(path)
            if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
                raise ValueError("Um documento mudou depois da inspeção; gere nova revisão.")
            documents.append({**entry, "text": raw.decode("utf-8")})
    except (OSError, UnicodeError) as exc:
        raise ValueError("Não foi possível capturar os documentos revisados.") from exc
    body = {"schema": 1, "project_id": project_id, "repository": repository,
            "contract_sha256": inspection["manifest_sha256"], "manifest": manifest, "documents": documents}
    digest = _digest(body)
    return {**body, "id": digest, "proposal_sha256": digest, "workspace_root": str(root)}


def sign_approval(proposal: dict, authority_dir: Path, reviewer: str,
                  decision: str = "accept", *, previous_approval_sha256: str | None = None,
                  workspace_root: Path | str | None = None) -> dict:
    """Sign an explicit decision and pin it in the external decision registry.

    ``reviewer`` is a signed assertion, not proof of a human-authenticated session.
    The caller must arrange the appropriate trusted signing interaction.
    """
    body = _validate_proposal(proposal)
    reviewer = _text(reviewer, "reviewer")
    if decision not in {"accept", "reject"}:
        raise ValueError("decision precisa ser accept ou reject.")
    workspace_root = workspace_root if workspace_root is not None else proposal.get("workspace_root")
    if body["repository"].startswith("repo:") and workspace_root is None:
        raise ValueError("workspace_root é necessário para verificar a autoridade externa.")
    authority_dir = _outside(Path(authority_dir), body["repository"], workspace_root)
    trust_path = authority_dir / "trust.json"
    trust = _load_trust(trust_path, body["repository"], workspace_root)
    try:
        private = serialization.load_pem_private_key(_read_regular(authority_dir / "private.key"), password=None)
    except (OSError, TypeError, ValueError) as exc:
        raise ValueError("Não foi possível ler uma chave privada Ed25519 válida.") from exc
    if not isinstance(private, Ed25519PrivateKey):
        raise ValueError("A chave privada precisa ser Ed25519.")
    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    key_id = hashlib.sha256(public).hexdigest()
    _authorized_key(trust, key_id, body["project_id"], body["repository"])
    registry = trust.setdefault("latest_decisions", {})
    previous = previous_approval_sha256 or registry.get(proposal["proposal_sha256"])
    payload = {key: body[key] for key in ("project_id", "repository", "contract_sha256", "manifest")}
    payload.update({"decision": decision, "reviewer": reviewer,
                    "issued_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "proposal_sha256": proposal["proposal_sha256"]})
    if previous is not None:
        payload["previous_approval_sha256"] = _sha(previous, "previous_approval_sha256")
    signed = {"schema": 1, "algorithm": "Ed25519", "key_id": key_id, "payload": payload}
    envelope = {**signed, "signature": base64.b64encode(private.sign(_canonical(signed))).decode("ascii")}
    registry[proposal["proposal_sha256"]] = _digest(envelope)
    _replace_json(trust_path, trust)
    return envelope


def verify_approval(envelope: dict, trust_path: Path, expected: dict) -> dict:
    """Verify authorized key, context, current decision and exact contract.

    Success proves a currently authorized signing-key decision. It does not prove
    human login, scenario execution, protected CI or separation of permissions.
    """
    if not isinstance(expected, dict):
        raise ValueError("O contexto esperado precisa ser um objeto.")
    project_id = _text(expected.get("project_id"), "project_id")
    repository = _repository(_text(expected.get("repository"), "repository"))
    workspace_root = expected.get("workspace_root")
    if repository.startswith("repo:") and workspace_root is None:
        raise ValueError("workspace_root é necessário para verificar o trust externo.")
    contract_sha256 = _sha(expected.get("contract_sha256"), "contract_sha256")
    if not isinstance(envelope, dict) or set(envelope) != {"schema", "algorithm", "key_id", "payload", "signature"}:
        raise ValueError("Envelope de decisão inválido.")
    if type(envelope["schema"]) is not int or envelope["schema"] != 1 or envelope["algorithm"] != "Ed25519":
        raise ValueError("Versão ou algoritmo de assinatura não suportado.")
    payload = envelope["payload"]
    if not isinstance(payload, dict):
        raise ValueError("Payload de decisão inválido.")
    for key, value in (("project_id", project_id), ("repository", repository), ("contract_sha256", contract_sha256)):
        if payload.get(key) != value:
            raise ValueError(f"A decisão não corresponde ao {key} atual.")
    manifest = _manifest(payload.get("manifest"), contract_sha256)
    if "manifest" in expected and _canonical(expected["manifest"]) != _canonical(manifest):
        raise ValueError("A decisão não corresponde ao manifesto esperado.")
    proposal_sha256 = _sha(payload.get("proposal_sha256"), "proposal_sha256")
    if "proposal_sha256" in expected and expected["proposal_sha256"] != proposal_sha256:
        raise ValueError("A decisão pertence a outra proposta.")
    if payload.get("decision") not in {"accept", "reject"}:
        raise ValueError("Decisão não reconhecida.")
    _text(payload.get("reviewer"), "reviewer")
    try:
        issued = datetime.fromisoformat(_text(payload.get("issued_at"), "issued_at"))
    except ValueError as exc:
        raise ValueError("issued_at precisa ser uma data ISO com timezone.") from exc
    if issued.tzinfo is None:
        raise ValueError("issued_at precisa indicar timezone.")
    if "previous_approval_sha256" in payload:
        _sha(payload["previous_approval_sha256"], "previous_approval_sha256")
    key_id = _sha(envelope["key_id"], "key_id")
    trust = _load_trust(Path(trust_path), repository, workspace_root)
    record = _authorized_key(trust, key_id, project_id, repository)
    signed = {key: value for key, value in envelope.items() if key != "signature"}
    try:
        Ed25519PublicKey.from_public_bytes(_decode(record["public_key"], 32, "public_key")).verify(
            _decode(envelope["signature"], 64, "signature"), _canonical(signed))
    except InvalidSignature as exc:
        raise ValueError("Assinatura da decisão inválida.") from exc
    digest = _digest(envelope)
    if trust["mode"] == "protected" or "latest_decisions" in trust:
        if trust.get("latest_decisions", {}).get(proposal_sha256) != digest:
            raise ValueError("A decisão não é a decisão atual registrada pela autoridade.")
    return {"valid": True, "approved": payload["decision"] == "accept", "decision": payload["decision"],
            "trust_mode": trust["mode"], "key_id": key_id, "claims": json.loads(_canonical(payload)),
            "envelope_sha256": digest, "human_authenticated": False}
