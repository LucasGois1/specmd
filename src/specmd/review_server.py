"""Loopback-only browser review for the local demonstration workflow.

The browser token is a CSRF/session capability, not proof of a human identity.
Another process running as the same OS user can access this local demo's state.
"""

from __future__ import annotations

import difflib
import html
from http.server import BaseHTTPRequestHandler, HTTPServer
import ipaddress
import json
from pathlib import Path
import secrets
import socket
from typing import Any
from urllib.parse import urlsplit
import webbrowser


_MAX_REQUEST_BYTES = 16_384


def _workflow():
    # Keep the HTTP presentation independent from workflow/CLI imports.
    from . import workflow
    return workflow


def _escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def _proposal_id(proposal: dict[str, Any]) -> str:
    identifier = proposal.get("id")
    if not isinstance(identifier, str) or not identifier:
        raise ValueError("A proposta não possui uma identidade de versão válida.")
    return identifier


def _identifiers(items: Any) -> str:
    if not isinstance(items, list) or not items:
        return "<p>Nenhum identificador declarado.</p>"
    rows = []
    for item in items:
        if isinstance(item, dict):
            identifier = item.get("id") or "sem ID"
            details = []
            if item.get("name"):
                details.append(str(item["name"]))
            if item.get("line"):
                details.append(f"linha {item['line']}")
            if item.get("requirements"):
                details.append("requisitos: " + ", ".join(map(str, item["requirements"])))
            suffix = " — " + "; ".join(details) if details else ""
            rows.append(f"<li><code>{_escape(identifier)}</code>{_escape(suffix)}</li>")
        else:
            rows.append(f"<li><code>{_escape(item)}</code></li>")
    return "<ul>" + "".join(rows) + "</ul>"


def _diff(previous: str | None, current: str, path: str) -> str:
    if previous == current:
        return "<p>Sem alteração textual em relação ao último snapshot aceito.</p>"
    lines = difflib.unified_diff(
        (previous or "").splitlines(), current.splitlines(),
        fromfile=f"aceito/{path}" if previous is not None else "/dev/null",
        tofile=f"proposto/{path}", lineterm="",
    )
    rendered = []
    for line in lines:
        kind = "added" if line.startswith("+") and not line.startswith("+++") else (
            "removed" if line.startswith("-") and not line.startswith("---") else "context"
        )
        rendered.append(f'<span class="{kind}">{_escape(line)}</span>')
    if not rendered:
        return "<p>Documento vazio; nenhuma linha de diff.</p>"
    return '<pre class="diff">' + "\n".join(rendered) + "</pre>"


def _document(document: dict[str, Any], index: int) -> str:
    path = str(document.get("path", "documento sem caminho"))
    text = document.get("text", "")
    if not isinstance(text, str):
        text = str(text)
    previous = document.get("previous_text")
    if previous is not None and not isinstance(previous, str):
        previous = str(previous)
    reason = document.get("exemption_reason") or document.get("reason")
    reason_html = f"<p><strong>Justificativa da dispensa proposta:</strong> {_escape(reason)}</p>" if reason else ""
    return f'''<article class="document" id="document-{index}">
<h2>{_escape(path)}</h2>
<p><strong>ID:</strong> <code>{_escape(document.get('id') or 'não declarado')}</code>
 · <strong>Classificação proposta:</strong> {_escape(document.get('kind') or 'não declarada')}</p>
{reason_html}
<p><strong>SHA-256:</strong> <code>{_escape(document.get('sha256') or '')}</code></p>
<h3>Requisitos</h3>{_identifiers(document.get('requirements'))}
<h3>Cenários</h3>{_identifiers(document.get('scenarios'))}
<h3>Texto integral proposto — Markdown</h3><pre class="narrative">{_escape(text)}</pre>
<h3>Diff para o último conteúdo aceito</h3>
<p>{'Documento novo, sem snapshot aceito anterior.' if previous is None else 'Comparação com o snapshot aceito anterior, não com o arquivo atual em disco.'}</p>
{_diff(previous, text, path)}
</article>'''


_STYLE = """
body{font-family:system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#18222e;background:#fff;line-height:1.5}
h1,h2,h3{line-height:1.25}code{overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere;padding:1rem;background:#f5f7fa;border:1px solid #d8dee7;border-radius:.4rem}
.warning{border-left:5px solid #b35a00;background:#fff4e5;padding:1rem}.document{border-top:2px solid #d8dee7;margin-top:2rem;padding-top:1rem}
.added{display:block;background:#daf5df}.removed{display:block;background:#ffe1e1}.context{display:block}.diff{line-height:1.35}
label{display:block;margin:.7rem 0}input[type=text]{font:inherit;padding:.5rem;width:min(28rem,90%)}button{font:inherit;padding:.65rem 1rem;cursor:pointer}button:disabled{cursor:default;opacity:.6}
form{border:2px solid #315a87;padding:1rem;margin:2rem 0}#action-result{white-space:pre-wrap}small{display:block;color:#435368}
"""


_SCRIPT = r"""
(() => {
  const fragment = new URLSearchParams(window.location.hash.slice(1));
  let token = fragment.get('token');
  window.history.replaceState(null, '', window.location.pathname);
  const form = document.getElementById('accept-form');
  const message = document.getElementById('action-result');
  const status = document.getElementById('status');
  async function refreshStatus() {
    try {
      const response = await fetch('/api/status', {cache: 'no-store', credentials: 'omit'});
      const body = await response.json();
      status.textContent = JSON.stringify(body, null, 2);
    } catch (error) {
      message.textContent = 'Não foi possível atualizar o estado: ' + error.message;
    }
  }
  document.getElementById('refresh-status').addEventListener('click', refreshStatus);
  if (!form) return;
  const buttons = Array.from(form.querySelectorAll('button[type="submit"]'));
  const disableDecisions = (disabled) => buttons.forEach(button => { button.disabled = disabled; });
  if (!token) {
    disableDecisions(true);
    message.textContent = 'Reabra o link completo impresso pelo comando de revisão para habilitar a decisão nesta sessão.';
  }
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!token || !form.reportValidity()) return;
    const reviewer = document.getElementById('reviewer').value.trim();
    const confirmed = document.getElementById('read-confirmed').checked;
    const decision = event.submitter && event.submitter.value === 'reject' ? 'reject' : 'accept';
    if (!reviewer || !confirmed) return;
    disableDecisions(true);
    try {
      const response = await fetch('/api/accept', {
        method: 'POST', credentials: 'omit', cache: 'no-store',
        headers: {'Content-Type': 'application/json', 'X-SpecMD-Review-Token': token},
        body: JSON.stringify({proposal_id: document.getElementById('proposal-id').value,
          reviewer: reviewer, read_confirmed: confirmed, decision: decision})
      });
      const body = await response.json();
      const success = decision === 'reject'
        ? 'Rejeição registrada. A tarefa permanece pendente; ajuste o contrato e submeta uma nova versão.'
        : 'Aceite registrado para esta versão. Isso não conclui a tarefa. Execute run e check para produzir e verificar evidências.';
      message.textContent = response.ok
        ? success + '\n' + JSON.stringify(body, null, 2)
        : 'A decisão não foi registrada: ' + (body.error || JSON.stringify(body));
      if (response.ok) { token = null; } else { disableDecisions(false); }
      await refreshStatus();
    } catch (error) {
      message.textContent = 'Falha ao registrar a decisão: ' + error.message;
      disableDecisions(false);
    }
  });
})();
"""


def _page(proposal: dict[str, Any] | None, status: dict[str, Any], nonce: str,
          review_error: str | None = None) -> str:
    documents = ""
    controls = "<p>A revisão ainda não está disponível. Corrija as pendências e recarregue esta página.</p>"
    identity = "<p>Nenhuma versão disponível para aceite.</p>"
    if proposal is not None:
        identifier = _proposal_id(proposal)
        identity = f'''<p><strong>Versão da proposta:</strong> <code>{_escape(identifier)}</code></p>
<p><strong>Projeto:</strong> {_escape(proposal.get('project_id', ''))}
 · <strong>Repositório:</strong> {_escape(proposal.get('repository', ''))}</p>
<p><strong>Hash contratual:</strong> <code>{_escape(proposal.get('contract_sha256', ''))}</code></p>'''
        entries = proposal.get("documents", [])
        if isinstance(entries, list):
            documents = "".join(_document(item, index) for index, item in enumerate(entries, start=1)
                                if isinstance(item, dict))
        removed = proposal.get("removed_documents", [])
        if isinstance(removed, list):
            for item in removed:
                if not isinstance(item, dict):
                    continue
                path = str(item.get("path", "documento removido"))
                previous = str(item.get("previous_text", ""))
                documents += f'''<article class="document"><h2>Removido: {_escape(path)}</h2>
<h3>Texto integral anteriormente aceito</h3><pre>{_escape(previous)}</pre>
<h3>Diff da remoção</h3>{_diff(previous, '', path)}</article>'''
        if isinstance(proposal.get("config_text"), str):
            documents += f'''<section class="document"><h2>Configuração integral — specmd.toml</h2>
<p>A configuração participa da identidade desta versão contratual.</p>
<pre>{_escape(proposal['config_text'])}</pre></section>'''
        traceability = proposal.get("traceability")
        if traceability is not None:
            documents += f'''<section class="document"><h2>Mapa de rastreabilidade completo</h2>
<p>Revise caminhos, requisitos e cenários relacionados. Os vínculos fazem parte da versão revisada; sua declaração não prova equivalência semântica.</p>
<pre>{_escape(_json(traceability))}</pre></section>'''
        git_metadata = proposal.get("git_provenance") or proposal.get("git_metadata") or proposal.get("git")
        if git_metadata:
            documents += f'''<details><summary>Metadados Git informados</summary><pre>{_escape(_json(git_metadata))}</pre>
<p>Autoria declarada em Git não autentica quem concede este aceite.</p></details>'''
        controls = f'''<form id="accept-form">
<h2>Decisão sobre esta versão</h2>
<input type="hidden" id="proposal-id" value="{_escape(identifier)}">
<label for="reviewer">Seu nome ou identificador declarado</label>
<input id="reviewer" type="text" required maxlength="160" autocomplete="name">
<label><input id="read-confirmed" type="checkbox" required>
Declaro que li o conteúdo integral e os diffs desta versão, incluindo configuração, vínculos, classificações e dispensas, e estou registrando minha decisão explícita.</label>
<p>Aceitar expressa concordância com o contrato apresentado. Rejeitar mantém a tarefa pendente.</p>
<button id="accept-button" type="submit" name="decision" value="accept">Aceitar esta versão do contrato</button>
<button id="reject-button" type="submit" name="decision" value="reject">Rejeitar esta versão do contrato</button>
<small>O registro desta declaração não comprova compreensão nem autenticação forte da pessoa.</small>
</form>'''
    error = f'<p class="warning">Revisão indisponível: {_escape(review_error)}</p>' if review_error else ""
    return f'''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SpecMD — revisão local</title><style nonce="{nonce}">{_STYLE}</style></head><body>
<h1>Revisão local do contrato</h1>
<p class="warning"><strong>Demonstração local, sem garantia contra outro processo do mesmo usuário.</strong>
O nome é declarado nesta interface; o token de sessão não prova identidade humana. Um agente com acesso ao mesmo usuário, aos arquivos ou às credenciais locais pode contornar essa separação. Este servidor não é uma autoridade de produção.</p>
{identity}{error}{documents}{controls}
<p id="action-result" role="status" aria-live="polite"></p>
<h2>Estado da tarefa</h2><p>Aceitar o contrato não executa cenários nem conclui a tarefa.</p>
<button id="refresh-status" type="button">Atualizar estado</button><pre id="status">{_escape(_json(status))}</pre>
<h2>Próximos passos</h2><p>Após o aceite, execute <code>specmd run</code> e <code>specmd check --stage completion --format json</code> no projeto, com a configuração de confiança correspondente. Consulte <code>--help</code> para as opções da CLI.</p>
<p>Finalize o servidor no terminal com Ctrl+C.</p>
<script nonce="{nonce}">{_SCRIPT}</script></body></html>'''


class _ReviewServer(HTTPServer):
    project_root: Path
    authority_dir: Path
    trust_path: Path | None
    review_token: str
    base_url: str
    review_url: str
    expected_host: str


class _IPv6ReviewServer(_ReviewServer):
    address_family = socket.AF_INET6


class _Handler(BaseHTTPRequestHandler):
    server: _ReviewServer

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, _format: str, *args: Any) -> None:
        # Avoid logging URL/query strings or the capability passed by a browser.
        return

    def _headers(self, status: int, content_type: str, size: int, nonce: str | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(size))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Pragma", "no-cache")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        if nonce is not None:
            self.send_header("Content-Security-Policy", (
                "default-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'; "
                f"script-src 'nonce-{nonce}'; style-src 'nonce-{nonce}'; connect-src 'self'"
            ))
        self.end_headers()

    def _send_json(self, status: int, value: dict[str, Any]) -> None:
        body = _json(value).encode("utf-8")
        self._headers(status, "application/json; charset=utf-8", len(body))
        self.wfile.write(body)

    def _valid_host(self) -> bool:
        hosts = self.headers.get_all("Host", [])
        return len(hosts) == 1 and hosts[0].lower() == self.server.expected_host.lower()

    def _route(self) -> str | None:
        if not self._valid_host():
            self._send_json(403, {"error": "Host não permitido para esta revisão local."})
            return None
        try:
            parsed = urlsplit(self.path)
        except ValueError:
            self._send_json(400, {"error": "Rota inválida."})
            return None
        if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
            self._send_json(400, {"error": "Use somente as rotas locais, sem token ou parâmetros na query."})
            return None
        return parsed.path

    def do_GET(self) -> None:
        route = self._route()
        if route is None:
            return
        workflow = _workflow()
        if route == "/api/status":
            try:
                status = workflow.check_project(self.server.project_root, trust_path=self.server.trust_path)
            except Exception as error:
                self._send_json(500, {"error": str(error), "may_complete": False})
                return
            self._send_json(200, status)
            return
        if route != "/":
            self._send_json(404, {"error": "Rota não encontrada."})
            return
        try:
            status = workflow.check_project(self.server.project_root, trust_path=self.server.trust_path)
        except Exception as error:
            status = {"status": "error", "may_complete": False, "findings": [{"message": str(error)}]}
        try:
            proposal = workflow.get_review(self.server.project_root, trust_path=self.server.trust_path)
            _proposal_id(proposal)
            review_error = None
        except Exception as error:
            proposal, review_error = None, str(error)
        nonce = secrets.token_urlsafe(24)
        body = _page(proposal, status, nonce, review_error).encode("utf-8")
        self._headers(200, "text/html; charset=utf-8", len(body), nonce)
        self.wfile.write(body)

    def do_POST(self) -> None:
        route = self._route()
        if route is None:
            return
        if route != "/api/accept":
            self._send_json(404, {"error": "Rota não encontrada."})
            return
        origins = self.headers.get_all("Origin", [])
        if len(origins) != 1 or origins[0] != self.server.base_url:
            self._send_json(403, {"error": "A decisão precisa vir da mesma origem da interface local."})
            return
        tokens = self.headers.get_all("X-SpecMD-Review-Token", [])
        if len(tokens) != 1 or not secrets.compare_digest(tokens[0].encode("utf-8"), self.server.review_token.encode("ascii")):
            self._send_json(403, {"error": "Token de revisão ausente ou inválido."})
            return
        if self.headers.get_content_type() != "application/json":
            self._send_json(415, {"error": "Envie a decisão como application/json."})
            return
        lengths = self.headers.get_all("Content-Length", [])
        if self.headers.get("Transfer-Encoding") or len(lengths) != 1:
            self._send_json(400, {"error": "Tamanho de requisição inválido."})
            return
        try:
            length = int(lengths[0])
            if length <= 0 or length > _MAX_REQUEST_BYTES:
                self._send_json(413, {"error": "Requisição fora do limite permitido."})
                return
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError("Corpo da requisição incompleto.")
            data = json.loads(raw.decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("A decisão precisa ser um objeto JSON.")
            identifier = data.get("proposal_id")
            reviewer = data.get("reviewer")
            if not isinstance(identifier, str) or not identifier or len(identifier) > 200:
                raise ValueError("Informe a identidade da versão apresentada.")
            if not isinstance(reviewer, str) or not reviewer.strip() or len(reviewer.strip()) > 160:
                raise ValueError("Informe explicitamente seu nome ou identificador.")
            reviewer = reviewer.strip()
            if any(ord(character) < 32 for character in reviewer):
                raise ValueError("O identificador não pode conter caracteres de controle.")
            if data.get("read_confirmed") is not True:
                raise ValueError("Confirme explicitamente a leitura para registrar sua decisão sobre esta versão.")
            decision = data.get("decision", "accept")
            if decision not in ("accept", "reject"):
                raise ValueError("A decisão precisa ser accept ou reject.")
        except (ValueError, UnicodeDecodeError, OSError) as error:
            self._send_json(400, {"error": str(error)})
            return
        workflow = _workflow()
        try:
            current = workflow.get_review(self.server.project_root, trust_path=self.server.trust_path)
            if _proposal_id(current) != identifier:
                self._send_json(409, {"error": "O contrato mudou. Recarregue e revise a nova versão antes de decidir."})
                return
            # The workflow rechecks the snapshot again when signing, closing the
            # race between this UI-level check and the actual acceptance write.
            result = workflow.accept_review(
                self.server.project_root, identifier, self.server.authority_dir,
                reviewer, decision=decision,
            )
        except (ValueError, OSError) as error:
            self._send_json(409, {"error": str(error)})
            return
        except Exception as error:
            self._send_json(500, {"error": str(error), "may_complete": False})
            return
        self._send_json(200, {"result": result, "message": "Decisão registrada para a versão apresentada. Aceite e rejeição não concluem a tarefa."})


def build_server(root: Path, authority_dir: Path, trust_path: Path | None = None,
                 host: str = "127.0.0.1", port: int = 0) -> HTTPServer:
    """Return a bound loopback-only server; no approval occurs during creation.

    ``review_url`` contains the random capability only in its URL fragment.
    ``base_url`` contains no token. ``review_token`` is exposed for harnesses.
    """
    try:
        address = ipaddress.ip_address(host)
    except ValueError as error:
        raise ValueError("O servidor aceita somente um endereço IP literal de loopback.") from error
    if not address.is_loopback:
        raise ValueError("O servidor de revisão não pode escutar em interface pública.")
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError("Porta inválida.")
    project_root = Path(root).resolve(strict=True)
    if not project_root.is_dir():
        raise ValueError("A raiz do projeto precisa ser um diretório.")
    authority_path = Path(authority_dir).resolve()
    trusted_path = Path(trust_path).resolve() if trust_path is not None else None
    server_class = _IPv6ReviewServer if address.version == 6 else _ReviewServer
    server = server_class((str(address), port), _Handler)
    server.project_root = project_root
    server.authority_dir = authority_path
    server.trust_path = trusted_path
    server.review_token = secrets.token_urlsafe(32)
    bound_host, bound_port = server.server_address[:2]
    authority = f"[{bound_host}]:{bound_port}" if address.version == 6 else f"{bound_host}:{bound_port}"
    server.expected_host = authority
    server.base_url = f"http://{authority}"
    server.review_url = server.base_url + "/#token=" + server.review_token
    return server


def serve_review(root: Path, authority_dir: Path, trust_path: Path | None = None,
                 host: str = "127.0.0.1", port: int = 0, open_browser: bool = True) -> None:
    """Open the local review link and block until interrupted by the operator."""
    server = build_server(root, authority_dir, trust_path, host, port)
    print("Revisão local: " + server.review_url, flush=True)
    print("Ctrl+C encerra o servidor. O aceite não conclui a tarefa.", flush=True)
    try:
        if open_browser:
            try:
                webbrowser.open(server.review_url, new=2)
            except (webbrowser.Error, OSError):
                print("Abra manualmente o link de revisão acima.", flush=True)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
