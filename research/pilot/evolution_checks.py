"""Hidden checks of the evolution round: the intended behavior after each step.

    python -I evolution_checks.py <stage> <project>

Stage 0 is the starting project; stage N is the behavior the developer wants
after request N. The agent never sees these checks. Prints one JSON line.
"""
import json
import sys
from pathlib import Path

stage, project = int(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(project))
FEE = 100


def item_total(prices):
    subtotal = sum(prices)
    discounted = subtotal >= 1000 if stage >= 2 else subtotal > 1000
    return subtotal - subtotal // 10 if discounted else subtotal


def expected(prices, what):
    items = item_total(prices)
    limit = 8000 if stage >= 5 else 10000
    return {"total": items + (FEE if stage >= 1 and prices else 0),
            "shipping": 0 if not prices or items > limit else 500,
            "points": items // 100 if items > 5000 else 0}[what]


def cart(prices):
    from app import Cart

    instance = Cart()
    for price in prices:
        instance.add(price)
    return instance


def observed(prices, what):
    instance = cart(prices)
    if what == "points":
        if stage >= 4:
            return instance.summary()["points"]
        import app

        return app.loyalty_points(instance)
    return getattr(instance, what)()


limit_pays = [4444, 4444] if stage >= 5 else [5555, 5556]
above_limit = [5000, 5000] if stage >= 5 else [6000, 6000]
fee_near_limit = [4440, 4440] if stage >= 5 else [5550, 5550]
CASES = [
    ("add up items", [200, 300], "total"),
    ("empty cart total", [], "total"),
    ("empty cart shipping", [], "shipping"),
    ("discount above the threshold", [600, 500], "total"),
    ("no discount below the threshold", [500, 499] if stage >= 2 else [500, 500], "total"),
    ("discount rounded down", [500, 505], "total"),
    ("shipping below the limit", [3000, 2000], "shipping"),
    ("exactly the limit pays shipping", limit_pays, "shipping"),
    ("free shipping above the limit", above_limit, "shipping"),
    ("loyalty points above 5000", [3000, 3000], "points"),
    ("no loyalty points at exactly 5000", [2555, 3000], "points"),
]
if stage >= 1:
    CASES += [("fee does not count for free shipping", fee_near_limit, "shipping"),
              ("total with the fee near the shipping limit", fee_near_limit, "total")]
if stage >= 2:
    CASES += [("discount at the threshold", [500, 500], "total")]
if stage >= 3:
    CASES += [("zero price allowed", [500, 0], "total"), ("no maximum price", [10**7], "total")]

results = []
for name, prices, what in CASES:
    try:
        results.append([name, observed(prices, what) == expected(prices, what)])
    except Exception:  # noqa: BLE001 - a crash is a failed check
        results.append([name, False])
if stage >= 3:
    try:
        cart([-1])
        results.append(["negative price rejected", False])
    except ValueError:
        results.append(["negative price rejected", True])
    except Exception:  # noqa: BLE001
        results.append(["negative price rejected", False])
if stage >= 4:
    try:
        summary = cart([3000, 3000]).summary()
        results.append(["summary has total, shipping and points",
                        all(summary[key] == expected([3000, 3000], key) for key in ("total", "shipping", "points"))])
    except Exception:  # noqa: BLE001
        results.append(["summary has total, shipping and points", False])
print(json.dumps({"stage": stage, "checks": results, "passed": all(ok for _, ok in results)}))
