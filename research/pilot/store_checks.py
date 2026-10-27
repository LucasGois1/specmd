"""Hidden checks of the store round: the intended behavior after each of the ten requests.

    python -I store_checks.py <stage> <project>

Stage 0 is the starting project; stage N is the behavior the developer wants
after request N. Each check also says whether its expected value changed with
request N, so a failure right after a change is not counted as a regression.
The agent never sees these checks. Prints one JSON line.
"""
import json
import sys
from pathlib import Path

STAGE, project = int(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(project))


def truth(stage, prices, coupon=None, balance=None):
    """Every amount the store should compute for one cart, after request `stage`."""
    subtotal = sum(prices)
    discounted = subtotal >= 1000 if stage >= 2 else subtotal > 1000
    items = subtotal - (subtotal // 10 if discounted else 0)
    if stage >= 8 and coupon == "SAVE5" and subtotal >= 3000:
        items = max(0, items - 500)
    fee = (150 if stage >= 10 else 100) if stage >= 1 and prices else 0
    total = items + fee
    limit = 8000 if stage >= 5 else 10000
    shipping = 0 if not prices or items > limit else 500
    points = items // 100 if items > 5000 else 0
    if stage >= 9 and items > 20000:
        points *= 2
    pays = total + shipping
    card = total if stage >= 7 else pays
    return {"subtotal": subtotal, "total": total, "shipping": shipping, "points": points, "refund": items,
            "invoice": pays, "card": min(card, balance) if balance is not None else card, "pays": pays}


def cart(prices, coupon=None):
    from app import Cart

    instance = Cart()
    for price in prices:
        instance.add(price)
    if coupon:
        instance.apply_coupon(coupon)
    return instance


def observe(what, prices, coupon=None, balance=None):
    instance = cart(prices, coupon)
    if what in {"subtotal", "total", "shipping"}:
        return getattr(instance, what)()
    if what == "points":
        import app

        if hasattr(app, "loyalty_points"):
            return app.loyalty_points(instance)
        return instance.summary()["points"]
    if what == "refund":
        from returns import refund_amount

        return refund_amount(instance)
    if what == "invoice":
        from invoices import invoice_total

        return invoice_total(instance)
    if what == "card":
        from gift_cards import GiftCard

        return GiftCard(balance).pay(instance)
    raise ValueError(what)


def amount_cases(stage):
    limit_pays = [4444, 4444] if stage >= 5 else [5555, 5556]
    above = [5000, 5000] if stage >= 5 else [6000, 6000]
    near = [4440, 4440] if stage >= 5 else [5550, 5550]
    cases = [
        ("subtotal adds the prices", "subtotal", [200, 300]),
        ("total of two items", "total", [200, 300]),
        ("empty cart total", "total", []),
        ("empty cart shipping", "shipping", []),
        ("discount above the threshold", "total", [600, 500]),
        ("no discount below the threshold", "total", [500, 499] if stage >= 2 else [500, 500]),
        ("discount rounded down", "total", [500, 505]),
        ("shipping below the limit", "shipping", [3000, 2000]),
        ("exactly the limit pays shipping", "shipping", limit_pays),
        ("free shipping above the limit", "shipping", above),
        ("loyalty points above 5000", "points", [3000, 3000]),
        ("no loyalty points at exactly 5000", "points", [2555, 3000]),
        ("refund of the items", "refund", [600, 500]),
        ("refund leaves shipping out", "refund", [3000, 2000]),
        ("invoice adds up to what the customer pays", "invoice", [3000, 2000]),
        ("invoice with free shipping adds up", "invoice", [6000, 6000]),
        ("gift card charge", "card", [3000, 2000], None, 20000),
        ("gift card limited to its balance", "card", [3000, 2000], None, 1000),
    ]
    if stage >= 1:
        cases += [("fee does not count for free shipping", "shipping", near),
                  ("total with the fee near the shipping limit", "total", near)]
    if stage >= 2:
        cases += [("discount at the threshold", "total", [500, 500])]
    if stage >= 3:
        cases += [("zero price allowed", "total", [500, 0]), ("no maximum price", "total", [10**7])]
    if stage >= 8:
        cases += [("coupon takes 500 off", "total", [3000, 2000], "SAVE5"),
                  ("coupon below 3000 gives nothing", "total", [2000, 500], "SAVE5"),
                  ("coupon lowers the free-shipping total", "shipping", [4650, 4650], "SAVE5"),
                  ("coupon lowers the loyalty points", "points", [3000, 3000], "SAVE5"),
                  ("coupon lowers the refund", "refund", [3000, 2000], "SAVE5"),
                  ("invoice with a coupon adds up", "invoice", [3000, 2000], "SAVE5")]
    if stage >= 9:
        cases += [("double points above 20000", "points", [12000, 12000]),
                  ("single points at exactly 20000", "points", [11111, 11111])]
    return cases


def expected(stage, case):
    _, what, prices, *extra = case
    coupon = extra[0] if extra else None
    balance = extra[1] if len(extra) > 1 else None
    return truth(stage, prices, coupon, balance)[what]


results = []


def record(name, check, changed):
    try:
        ok = bool(check())
    except Exception:  # noqa: BLE001 - a crash is a failed check
        ok = False
    results.append([name, ok, changed])


previous = {case[0]: case for case in amount_cases(STAGE - 1)} if STAGE else {}
for case in amount_cases(STAGE):
    name, what, prices, *extra = case
    old = previous.get(name)
    changed = old is None or old[2:] != case[2:] or expected(STAGE - 1, old) != expected(STAGE, case) if STAGE else False
    record(name, lambda: observe(what, prices, *extra) == expected(STAGE, case), changed)


def raises(function, error):
    try:
        function()
    except error:
        return True
    return False


def usernames():
    from users import valid_username

    return [valid_username("alice"), not valid_username("al"), not valid_username("alice!"),
            not valid_username("a" * 21)]


def changed_for(prices, keys, introduced=None):
    """Whether request STAGE changed what these amounts should be (or introduced the check)."""
    if not STAGE or STAGE == introduced:
        return bool(STAGE)
    before, after = truth(STAGE - 1, prices), truth(STAGE, prices)
    return any(before[key] != after[key] for key in keys)


record("usernames follow the rules", lambda: all(usernames()), False)
record("confirmation states the amount to pay",
       lambda: f"{truth(STAGE, [3000, 2000])['pays']} cents" in __import__("notifications").order_confirmation(
           cart([3000, 2000])), changed_for([3000, 2000], ["pays"]))
record("daily revenue adds the totals",
       lambda: __import__("reports").daily_revenue([cart([600]), cart([2000])])
       == truth(STAGE, [600])["total"] + truth(STAGE, [2000])["total"],
       changed_for([600], ["total"]) or changed_for([2000], ["total"]))
if STAGE >= 3:
    record("negative price rejected", lambda: raises(lambda: cart([-1]), ValueError), STAGE == 3)
if STAGE >= 4:
    record("summary has total, shipping and points",
           lambda: all(cart([3000, 3000]).summary()[key] == truth(STAGE, [3000, 3000])[key]
                       for key in ("total", "shipping", "points")),
           changed_for([3000, 3000], ["total", "shipping", "points"], introduced=4))
if STAGE >= 8:
    record("unknown coupon rejected", lambda: raises(lambda: cart([3000], "NOPE"), ValueError), STAGE == 8)
print(json.dumps({"stage": STAGE, "checks": results, "passed": all(ok for _, ok, _ in results)}))
