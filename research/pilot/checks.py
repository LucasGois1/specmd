"""Hidden acceptance checks of the pilot: the developer's real intent, never shown to the agent.

    python -I checks.py <task> <project>

Prints {"passed": bool, "checks": [[name, ok], ...]}. The project's code runs
in this process, so call it in a subprocess.
"""
import json
from pathlib import Path
import sys

TASK, PROJECT = sys.argv[1], Path(sys.argv[2]).resolve()
sys.path.insert(0, str(PROJECT))
results = []


def check(name, condition):
    try:
        ok = bool(condition())
    except Exception as error:  # noqa: BLE001 - any failure is a failed check
        ok, name = False, f"{name} ({type(error).__name__}: {error})"
    results.append([name, ok])


def total(*prices):
    from app import Cart

    cart = Cart()
    for price in prices:
        cart.add(price)
    return cart.total()


def raises(action, kind):
    try:
        action()
    except kind:
        return True
    return False


if TASK == "T1":
    check("600 + 500 = 990 (10% acima de 1000)", lambda: total(600, 500) == 990)
    check("500 + 500 = 1000 (limite sem desconto)", lambda: total(500, 500) == 1000)
    check("500 + 505 = 905 (desconto arredondado para baixo)", lambda: total(500, 505) == 905)
    check("carrinho vazio = 0", lambda: total() == 0)
elif TASK == "T2":
    check("200 + 300 = 501 (taxa com itens)", lambda: total(200, 300) == 501)
    check("100 = 101", lambda: total(100) == 101)
    check("carrinho vazio = 0 (sem taxa)", lambda: total() == 0)
elif TASK == "T3":
    check("preço negativo levanta ValueError", lambda: raises(lambda: total(-1), ValueError))
    check("preço zero é aceito", lambda: total(0) == 0)
    check("preço alto é aceito", lambda: total(10 ** 9) == 10 ** 9)
    check("soma normal continua", lambda: total(200, 300) == 500)
elif TASK == "T4":
    from pagamentos import pode_estornar, solicitar_estorno

    check("7 dias: aprovado", lambda: solicitar_estorno(7) == "aprovado")
    check("8 dias: recusado", lambda: solicitar_estorno(8) == "recusado")
    check("0 dias: aprovado", lambda: solicitar_estorno(0) == "aprovado")
    check("pode_estornar segue os 7 dias", lambda: pode_estornar(7) and not pode_estornar(8))
elif TASK == "T5":
    check("300 + 300 = 540 (desconto acima de 500)", lambda: total(300, 300) == 540)
    check("250 + 250 = 500 (limite sem desconto)", lambda: total(250, 250) == 500)
    check("600 + 500 = 990", lambda: total(600, 500) == 990)
    check("carrinho vazio = 0", lambda: total() == 0)
elif TASK == "T6":
    def cart(*prices):
        from app import Cart

        value = Cart()
        for price in prices:
            value.add(price)
        return value

    check("10000 exatos pagam 500 de frete", lambda: cart(5000, 5000).frete() == 500)
    check("acima de 10000, frete grátis", lambda: cart(5000, 5001).frete() == 0)
    check("10 itens são aceitos", lambda: cart(*[1] * 10).total() == 10)
    check("o 11º item levanta ValueError", lambda: raises(lambda: cart(*[1] * 11), ValueError))
    check("total continua a soma", lambda: total(200, 300) == 500)
else:
    raise SystemExit(f"tarefa desconhecida: {TASK}")

print(json.dumps({"passed": all(ok for _, ok in results), "checks": results}, ensure_ascii=False))
