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
    check("600 + 500 = 990 (10% above 1000)", lambda: total(600, 500) == 990)
    check("500 + 500 = 1000 (limit without discount)", lambda: total(500, 500) == 1000)
    check("500 + 505 = 905 (discount rounded down)", lambda: total(500, 505) == 905)
    check("empty cart = 0", lambda: total() == 0)
elif TASK == "T2":
    check("200 + 300 = 501 (fee with items)", lambda: total(200, 300) == 501)
    check("100 = 101", lambda: total(100) == 101)
    check("empty cart = 0 (no fee)", lambda: total() == 0)
elif TASK == "T3":
    check("negative price raises ValueError", lambda: raises(lambda: total(-1), ValueError))
    check("zero price is accepted", lambda: total(0) == 0)
    check("high price is accepted", lambda: total(10 ** 9) == 10 ** 9)
    check("plain sum still works", lambda: total(200, 300) == 500)
elif TASK == "T4":
    from payments import can_refund, request_refund

    check("7 days: approved", lambda: request_refund(7) == "approved")
    check("8 days: refused", lambda: request_refund(8) == "refused")
    check("0 days: approved", lambda: request_refund(0) == "approved")
    check("can_refund follows the 7 days", lambda: can_refund(7) and not can_refund(8))
elif TASK == "T5":
    check("300 + 300 = 540 (discount above 500)", lambda: total(300, 300) == 540)
    check("250 + 250 = 500 (limit without discount)", lambda: total(250, 250) == 500)
    check("600 + 500 = 990", lambda: total(600, 500) == 990)
    check("empty cart = 0", lambda: total() == 0)
elif TASK == "T6":
    def cart(*prices):
        from app import Cart

        value = Cart()
        for price in prices:
            value.add(price)
        return value

    check("exactly 10000 pays 500 shipping", lambda: cart(5000, 5000).shipping() == 500)
    check("above 10000, free shipping", lambda: cart(5000, 5001).shipping() == 0)
    check("10 items are accepted", lambda: cart(*[1] * 10).total() == 10)
    check("the 11th item raises ValueError", lambda: raises(lambda: cart(*[1] * 11), ValueError))
    check("total is still the sum", lambda: total(200, 300) == 500)
else:
    raise SystemExit(f"unknown task: {TASK}")

print(json.dumps({"passed": all(ok for _, ok in results), "checks": results}, ensure_ascii=False))
