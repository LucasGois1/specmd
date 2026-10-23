"""Versioned review, evidence and completion lifecycle.

Local demonstration state is deliberately distinguished from a fresh execution
under externally provisioned trust. Neither a cache nor a repository receipt
can nominate its own trusted key.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import subprocess
from typing import Any

from .core import _read_regular_file, inspect_project, _PRUNED_DIRECTORIES

APPROVALS = ".specmd/approvals"
SOURCE_SUFFIXES = {".py", ".java", ".go", ".js", ".jsx", ".ts", ".tsx", ".rs", ".rb", ".cs", ".cpp", ".c", ".h", ".sh", ".sql", ".kt", ".swift", ".scala", ".php", ".vue", ".svelte"}


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def _directory(root: Path, relative: str) -> Path:
    current = root
    for part in Path(relative).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("Estado SpecMD não pode atravessar links simbólicos.")
        current.mkdir(exist_ok=True)
    return current


def _write(root: Path, relative: str, value: Any) -> None:
    destination = root / relative
    parent = _directory(root, str(Path(relative).parent))
    if destination.is_symlink():
        raise ValueError("Estado SpecMD não pode ser um link simbólico.")
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=parent, delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    try:
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _read_json(root: Path, relative: str) -> Any:
    path = root / relative
    if any(p.is_symlink() for p in (path, *path.parents) if p != root.parent):
        raise ValueError("Estado SpecMD não pode atravessar links simbólicos.")
    return _loads_json(_read_regular_file(path))


def _loads_json(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError(f"Chave JSON duplicada: {key}.")
            value[key] = item
        return value
    def invalid_constant(value):
        raise ValueError(f"Constante JSON inválida: {value}.")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid_constant)


def _safe_relative(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError("Caminho de rastreabilidade deve ser relativo e permanecer no projeto.")
    path = root / relative
    if any(p.is_symlink() for p in (path, *path.parents) if p != root.parent):
        raise ValueError("Rastreabilidade não pode atravessar links simbólicos.")
    return path


def code_snapshot(root: Path) -> dict:
    """Hash source, tests, config and resources, including untracked files."""
    entries = []
    for directory, names, files in os.walk(root, followlinks=False):
        base = Path(directory)
        retained = []
        for name in sorted(names):
            if name in _PRUNED_DIRECTORIES or name in {".cache", ".tools"}:
                continue
            if (base / name).is_symlink():
                raise ValueError("Snapshot de código recusa diretórios simbólicos.")
            retained.append(name)
        names[:] = retained
        for name in sorted(files):
            path = base / name
            if path.suffix.lower() in {".md", ".markdown"}:
                continue
            if name in {".DS_Store"}:
                continue
            raw = _read_regular_file(path)
            entries.append({"path": path.relative_to(root).as_posix(),
                            "sha256": hashlib.sha256(raw).hexdigest()})
    entries.sort(key=lambda x: x["path"])
    return {"files": entries, "sha256": digest(entries)}


def _configuration(root):
    from .config import load_config
    return load_config(root)


def _repository_identity(root, config):
    return "repo:" + config["repository_id"] if config.get("repository_id") else str(root)


def _traceability(root: Path, config: dict, inspection: dict) -> tuple[dict, list]:
    settings = config.get("traceability", {})
    relative = settings.get("map", ".specmd/traceability.json")
    path = _safe_relative(root, relative)
    findings = []
    if not path.exists():
        return {"path": relative, "sha256": None, "entries": {}}, [{"kind": "traceability_missing", "message": f"Crie {relative} com vínculos explícitos entre código/testes e requisitos."}]
    raw = _read_regular_file(path)
    mapping = _loads_json(raw)
    if not isinstance(mapping, dict) or type(mapping.get("schema")) is not int or mapping["schema"] != 1 or not isinstance(mapping.get("files"), dict):
        raise ValueError("Mapa exige schema=1 e files como mapa de caminhos para requisitos/cenários.")
    requirements = {r["id"] for doc in inspection["documents"] for r in doc["requirements"]}
    scenarios = {s["id"] for doc in inspection["documents"] for s in doc["scenarios"]}
    sources = {item["path"] for item in code_snapshot(root)["files"] if Path(item["path"]).suffix.lower() in SOURCE_SUFFIXES}
    for relative_source, links in mapping["files"].items():
        candidate = _safe_relative(root, relative_source)
        if not candidate.is_file():
            findings.append({"kind": "traceability_orphan", "path": relative_source, "message": "Vínculo aponta para arquivo ausente."})
        if not isinstance(links, dict):
            raise ValueError("Cada entrada de rastreabilidade deve ser um mapa.")
        reqs, scns = links.get("requirements", []), links.get("scenarios", [])
        if not isinstance(reqs, list) or not all(isinstance(v, str) for v in reqs) or not isinstance(scns, list) or not all(isinstance(v, str) for v in scns):
            raise ValueError("Vínculos requirements/scenarios devem ser listas de IDs.")
        if not reqs or not set(reqs) <= requirements or not set(scns) <= scenarios:
            findings.append({"kind": "traceability_invalid", "path": relative_source, "message": "Arquivo exige requisitos conhecidos e cenários existentes."})
    if settings.get("policy", "strict") == "strict":
        for source in sorted(sources - mapping["files"].keys()):
            findings.append({"kind": "behavior_origin_missing", "path": source, "message": "Código ou teste sem vínculo declarado a um requisito revisável."})
    return {"path": relative, "sha256": hashlib.sha256(raw).hexdigest(), "entries": mapping["files"]}, findings


def _inspection(root: Path) -> tuple[dict, dict]:
    result = inspect_project(root)
    if result["status"] in {"inactive", "error"}:
        return result, {}
    config = _configuration(root)
    if config["schema"] == 1:
        return result, config
    result["findings"] = [f for f in result["findings"] if f["kind"] not in {"authority_not_configured", "evidence_not_executed"}]
    trace, findings = _traceability(root, config, result)
    result["traceability"] = trace
    result["findings"].extend(findings)
    if result["manifest"]:
        result["manifest"] = {**result["manifest"], "traceability_sha256": trace["sha256"]}
        result["manifest_sha256"] = digest(result["manifest"])
    result["status"] = "blocked" if result["findings"] else "waiting_human_review"
    return result, config


def _approval_files(root: Path) -> list[Path]:
    directory = root / APPROVALS
    if directory.is_symlink():
        raise ValueError("Recibos não podem atravessar links simbólicos.")
    return sorted(directory.glob("*.json")) if directory.exists() else []


def _previous_review(root, config, trust_path):
    from .authority import verify_approval, _validate_proposal
    trust = _trust_path(root, trust_path)
    if trust is None:
        return {}
    accepted = []
    for path in _approval_files(root):
        try:
            envelope = _read_json(root, str(path.relative_to(root)))
            payload = envelope["payload"]
            verified = verify_approval(envelope, trust, {
                "project_id": config["project_id"], "repository": _repository_identity(root, config),
                "workspace_root": str(root), "contract_sha256": payload["contract_sha256"],
                "manifest": payload["manifest"]})
            if not verified["approved"]:
                continue
            identifier = payload["proposal_sha256"]
            if not isinstance(identifier, str) or len(identifier) != 64 or any(c not in "0123456789abcdef" for c in identifier):
                continue
            snapshot = _read_json(root, f".specmd/reviews/{identifier}.json")
            _validate_proposal(snapshot)
            if snapshot["proposal_sha256"] != identifier:
                continue
            accepted.append((payload["issued_at"], snapshot))
        except (OSError, ValueError, TypeError, KeyError):
            continue
    if not accepted:
        return {}
    snapshot = max(accepted, key=lambda item: item[0])[1]
    return {doc["path"]: doc["text"] for doc in snapshot["documents"]}


def _proposal_view(root: Path, proposal: dict, inspection: dict, trust_path=None) -> dict:
    # Display metadata is never an independent approval authority.
    previous = _previous_review(root, _configuration(root), trust_path)
    by_path = {doc["path"]: doc for doc in inspection["documents"]}
    provenance = {}
    try:
        completed = subprocess.run(["git", "log", "-1", "--format=%H%n%an%n%aI"],
                                   cwd=root, capture_output=True, text=True, timeout=5)
        if completed.returncode == 0:
            commit, author, authored_at = completed.stdout.strip().split("\n", 2)
            provenance = {"commit": commit, "declared_git_author": author, "authored_at": authored_at,
                          "note": "Autoria declarada no Git não autentica a pessoa que aceitou o contrato."}
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return {**proposal, "proposal_id": proposal["id"], "git_provenance": provenance,
        "config_text": _read_regular_file(root / "specmd.toml").decode("utf-8"), "documents": [
        {**by_path.get(doc["path"], {}), **doc,
         "previous_text": previous.get(doc["path"])}
        for doc in proposal["documents"]],
        "removed_documents": [{"path": path, "previous_text": text} for path, text in previous.items()
                              if path not in by_path],
        "traceability": inspection.get("traceability", {}),
        "limitations": "A revisão local é uma demonstração. Um processo com acesso à chave local pode emitir aceites. Vínculos não provam equivalência semântica."}


def prepare_review(root: Path, trust_path=None) -> dict:
    from .authority import create_review
    root = Path(root).resolve(strict=True)
    inspection, config = _inspection(root)
    if config.get("schema") != 2:
        raise ValueError("O fluxo completo exige specmd.toml schema=2.")
    if inspection["findings"] or not inspection["manifest_sha256"]:
        raise ValueError("Resolva a estrutura/rastreabilidade antes da revisão: " + "; ".join(f["message"] for f in inspection["findings"]))
    proposal = create_review(root, inspection, config)
    _write(root, f".specmd/reviews/{proposal['id']}.json", proposal)
    return _proposal_view(root, proposal, inspection, trust_path)


def get_review(root: Path, trust_path=None) -> dict:
    return prepare_review(root, trust_path)


def accept_review(root: Path, proposal_id: str, authority_dir: Path,
                  reviewer: str, decision: str = "accept") -> dict:
    from .authority import sign_approval
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise ValueError("Identifique a pessoa responsável pela decisão.")
    root = Path(root).resolve(strict=True)
    _trust_path(root, Path(authority_dir) / "trust.json")
    current = prepare_review(root)
    if current["id"] != proposal_id:
        raise ValueError("A proposta mudou. Recarregue e revise a versão atual antes de decidir.")
    bare = _read_json(root, f".specmd/reviews/{proposal_id}.json")
    receipt = sign_approval(bare, Path(authority_dir), reviewer.strip(), decision=decision)
    # Refuse a contract changed while the authority was signing.
    if prepare_review(root)["id"] != proposal_id:
        raise ValueError("O contrato mudou durante a assinatura; aceite não aplicado ao projeto.")
    receipt_id = digest(receipt)
    _write(root, f".specmd/approvals/{receipt_id}.json", receipt)
    if decision == "accept":
        _write(root, ".specmd/local/last-accepted-review.json", bare)
    return {"status": "accepted" if decision == "accept" else "rejected", "proposal_id": proposal_id,
            "receipt_sha256": receipt_id, "may_complete": False,
            "message": "Decisão registrada; a conclusão depende de evidências atuais."}


def _trust_path(root, provided):
    value = provided or os.environ.get("SPECMD_TRUST_STORE")
    if not value:
        return None
    path = Path(value).resolve(strict=True)
    if path.is_relative_to(root):
        raise ValueError("A raiz de confiança precisa ser provisionada fora do repositório.")
    return path


def _approval(root, inspection, config, trust_path):
    from .authority import verify_approval
    if trust_path is None:
        return None, [{"kind": "authority_not_configured", "message": "Informe SPECMD_TRUST_STORE ou --trust apontando para confiança externa ao projeto."}]
    valid = []
    rejected = []
    for path in _approval_files(root):
        try:
            receipt = _read_json(root, str(path.relative_to(root)))
            verified = verify_approval(receipt, trust_path, {
                "project_id": config["project_id"], "repository": _repository_identity(root, config),
                "workspace_root": str(root),
                "contract_sha256": inspection["manifest_sha256"], "manifest": inspection["manifest"]})
            if verified.get("valid"):
                valid.append(verified)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            rejected.append(str(exc))
    if not valid:
        return None, [{"kind": "human_review_required", "message": "Esta versão do contrato, classificação e vínculos ainda exige aceite válido.",
                       "invalid_receipts": len(rejected)}]
    latest = max(valid, key=lambda item: item["claims"]["issued_at"])
    if not latest.get("approved"):
        return None, [{"kind": "human_review_rejected", "message": "A decisão vigente rejeita esta versão do contrato."}]
    return latest, []


def _error(exc):
    return {"protocol_version": 1, "stage": "completion", "status": "error", "may_complete": False,
            "findings": [{"kind": "verification_error", "message": str(exc)}]}


def check_project(root: Path, trust_path=None, *, fresh_evidence=None,
                  require_real=False) -> dict:
    if require_real and fresh_evidence is None:
        return run_project(root, trust_path, require_real=True)
    try:
        root = Path(root).resolve(strict=True)
        result, config = _inspection(root)
        if config.get("schema") != 2 or result["findings"]:
            return result
        trust = _trust_path(root, trust_path)
        approval, issues = _approval(root, result, config, trust)
        if issues:
            return {**result, "status": "waiting_human_review", "findings": issues}
        result["approval"] = {k: v for k, v in approval.items() if k != "claims"}
        try:
            evidence = fresh_evidence if fresh_evidence is not None else _read_json(root, ".specmd/local/evidence.json")
        except FileNotFoundError:
            return {**result, "status": "awaiting_evidence", "findings": [{"kind": "evidence_missing", "message": "Execute specmd run para verificar a implementação aceita."}]}
        if not isinstance(evidence, dict) or type(evidence.get("schema")) is not int or evidence["schema"] != 1:
            raise ValueError("Evidência precisa ser um relatório completo schema=1; evidência fresca inválida não pode reutilizar cache.")
        body = {k: v for k, v in evidence.items() if k != "sha256"}
        expected = sorted(s["id"] for d in result["documents"] for s in d["scenarios"])
        observed = evidence.get("execution", {}).get("scenarios", [])
        source = code_snapshot(root)
        trace_hash = result["traceability"]["sha256"]
        coherent = (evidence.get("sha256") == digest(body)
                    and evidence.get("contract_sha256") == result["manifest_sha256"]
                    and evidence.get("code_sha256") == source["sha256"]
                    and evidence.get("traceability_sha256") == trace_hash
                    and evidence.get("approval_sha256") == approval["envelope_sha256"])
        if not coherent:
            return {**result, "status": "awaiting_evidence", "findings": [{"kind": "evidence_stale", "message": "Contrato, código, testes, configuração ou aceite mudou; execute os cenários novamente."}]}
        elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(evidence["created_at"])).total_seconds()
        if elapsed < -5 or elapsed > config.get("evidence", {}).get("max_age_seconds", 86400):
            return {**result, "status": "awaiting_evidence", "findings": [{"kind": "evidence_expired", "message": "A validade temporal da evidência terminou; execute novamente."}]}
        execution = evidence["execution"]
        okay = (bool(expected) and execution.get("passed") is True
                and sorted(s.get("id", "") for s in observed) == expected
                and all(s.get("status") == "passed" for s in observed))
        if not okay:
            return {**result, "status": "blocked", "evidence": evidence,
                    "findings": [{"kind": "scenarios_not_passed", "message": "Todos os cenários esperados precisam executar e passar, sem omissões.", "details": execution.get("findings", [])}]}
        simulated = execution.get("mode") != "real"
        protected = (approval["trust_mode"] == "protected" and fresh_evidence is not None
                     and not simulated and config.get("traceability", {}).get("policy", "strict") == "strict")
        if require_real and not protected:
            return {**result, "status": "blocked", "findings": [{"kind": "protected_execution_required", "message": "Gate exige confiança externa protegida, rastreabilidade estrita e execução real atual. Demonstração não satisfaz esse gate."}]}
        return {**result, "status": "passed" if protected else "demo_passed", "may_complete": True,
                "verification_mode": "real" if protected else "demo", "assurance": "protected" if protected else "local_demo",
                "test_mode": execution["mode"], "evidence": evidence, "findings": [],
                "limitations": [] if protected else ["Resultado para experimentar o fluxo local; não é aceite autenticado por uma autoridade isolada nem evidência independente."]}
    except Exception as exc:
        return _error(exc)


def run_project(root: Path, trust_path=None, *, require_real=False) -> dict:
    from .runner import execute_project
    try:
        root = Path(root).resolve(strict=True)
        initial, config = _inspection(root)
        if config.get("schema") != 2 or initial["findings"]:
            return initial
        approval, issues = _approval(root, initial, config, _trust_path(root, trust_path))
        if issues:
            return {**initial, "status": "waiting_human_review", "findings": issues}
        before = code_snapshot(root)
        execution = execute_project(root, initial, config)
        after = code_snapshot(root)
        final, _ = _inspection(root)
        if before != after or initial["manifest_sha256"] != final["manifest_sha256"]:
            return {**final, "status": "blocked", "may_complete": False,
                    "findings": [{"kind": "changed_during_execution", "message": "Código ou contrato mudou durante a execução; resultado descartado."}]}
        evidence = {"schema": 1, "created_at": datetime.now(timezone.utc).isoformat(),
                    "contract_sha256": initial["manifest_sha256"], "code_sha256": before["sha256"],
                    "traceability_sha256": initial["traceability"]["sha256"],
                    "approval_sha256": approval["envelope_sha256"], "execution": execution}
        evidence["sha256"] = digest(evidence)
        _write(root, ".specmd/local/evidence.json", evidence)
        return check_project(root, trust_path, fresh_evidence=evidence, require_real=require_real)
    except Exception as exc:
        return _error(exc)


def audit_project(root: Path, trust_path=None) -> dict:
    """Inspect signed decisions; invalid/obsolete receipts remain visible."""
    from .authority import verify_approval
    root = Path(root).resolve(strict=True)
    trust = _trust_path(root, trust_path)
    records = []
    for path in _approval_files(root):
        row = {"path": str(path.relative_to(root)), "valid": False}
        try:
            envelope = _read_json(root, row["path"])
            payload = envelope.get("payload", {})
            row.update({key: payload.get(key) for key in (
                "decision", "reviewer", "issued_at", "contract_sha256", "project_id",
                "proposal_sha256", "previous_approval_sha256")})
            row["key_id"] = envelope.get("key_id")
            if trust:
                checked = verify_approval(envelope, trust, {
                    "project_id": _configuration(root)["project_id"],
                    "repository": _repository_identity(root, _configuration(root)), "workspace_root": str(root),
                    "contract_sha256": payload.get("contract_sha256"), "manifest": payload.get("manifest")})
                row.update({"valid": checked["valid"], "trust_mode": checked["trust_mode"]})
            else:
                row["error"] = "Confiança externa não configurada."
        except Exception as exc:
            row["error"] = str(exc)
        records.append(row)
    return {"schema": 1, "decisions": records, "current": check_project(root, trust),
            "limitations": "O histórico no repositório pode ser apagado; preservação e auditoria completas dependem do registro externo e da política Git/CI."}
