"""A synthetic high-growth B2B SaaS customer: what a forward deployed analyst finds on day one.

Stripe (subscriptions, invoices with discounts, trials, annual prepay, refunds, two currencies),
Salesforce (opportunities with stage history), and product usage. Fixed seed, no real company.
"""
import random
from datetime import date, timedelta

SEED = 42
START, END = date(2025, 10, 1), date(2026, 9, 30)
FX = {"USD": 1.0, "EUR": 1.08}
PLANS = {"starter": 99, "team": 499, "business": 1999}


def month_iter(a, b):
    y, m = a.year, a.month
    while (y, m) <= (b.year, b.month):
        yield date(y, m, 1)
        m += 1
        if m == 13:
            y, m = y + 1, 1


def C_months(a, b):
    return list(month_iter(date(a.year, a.month, 1), b))


def build(n=600):
    rng = random.Random(SEED)
    customers, subs, invoices, opps, usage = [], [], [], [], []
    for cid in range(1, n + 1):
        seg = rng.choices(["smb", "mid", "ent"], [0.6, 0.3, 0.1])[0]
        signup = START + timedelta(days=rng.randint(-200, 330))
        cur = "EUR" if rng.random() < 0.18 else "USD"
        customers.append({"customer_id": cid, "segment": seg, "signup": signup, "currency": cur,
                          # 4% of customers exist twice in Stripe (re-signed up with another card)
                          "stripe_ids": [f"cus_{cid}"] + ([f"cus_{cid}b"] if rng.random() < 0.04 else [])})
        plan = {"smb": "starter", "mid": rng.choice(["team", "starter"]), "ent": "business"}[seg]
        trial_end = signup + timedelta(days=14)
        converted = rng.random() < {"smb": 0.55, "mid": 0.7, "ent": 0.85}[seg]
        if not converted:
            for m in C_months(signup, trial_end):
                usage.append({"customer_id": cid, "month": m, "active_users": rng.randint(1, 3)})
            subs.append({"customer_id": cid, "plan": plan, "status": "trial_expired", "start": signup,
                         "trial_end": trial_end, "end": trial_end, "interval": "month", "seats": 1,
                         "discount": 0.0, "currency": cur})
            continue
        annual = seg != "smb" and rng.random() < 0.45
        seats = {"smb": rng.randint(1, 3), "mid": rng.randint(3, 15), "ent": rng.randint(15, 80)}[seg]
        discount = rng.choice([0, 0, 0, 0.1, 0.2]) if seg != "smb" else 0.0
        churn_rate = {"smb": 0.035, "mid": 0.018, "ent": 0.008}[seg]  # monthly
        end = None
        s = {"customer_id": cid, "plan": plan, "status": "active", "start": trial_end, "trial_end": trial_end,
             "end": None, "interval": "year" if annual else "month", "seats": seats, "discount": discount,
             "currency": cur, "upgrades": []}
        # walk months: churn, seat expansion
        for m in month_iter(trial_end, END):
            if m <= trial_end:
                continue
            if rng.random() < (0.10 if seg != "smb" else 0.03):
                s["upgrades"].append((m, rng.randint(1, max(2, seats // 3))))
            if rng.random() < churn_rate * (1 if not annual else 0.4):
                end = m
                break
        if end:
            s["status"], s["end"] = "canceled", end
        subs.append(s)
        # invoices
        unit = PLANS[plan] * (1 - discount)
        for m in month_iter(trial_end, END):
            if m < date(trial_end.year, trial_end.month, 1) or (end and m >= end):
                continue
            extra = sum(k for d, k in s["upgrades"] if d <= m)
            amt = unit * (seats + extra) / (1 if annual else 1)
            if annual:
                if (m.month - trial_end.month) % 12 == 0:
                    invoices.append({"customer_id": cid, "stripe_id": customers[-1]["stripe_ids"][-1],
                                     "date": m, "amount": round(amt * 12, 2), "currency": cur,
                                     "period_months": 12, "refunded": False})
            else:
                invoices.append({"customer_id": cid, "stripe_id": rng.choice(customers[-1]["stripe_ids"]),
                                 "date": m, "amount": round(amt, 2), "currency": cur, "period_months": 1,
                                 "refunded": rng.random() < 0.015})
        # usage: active users per month
        for m in month_iter(trial_end, END):
            if end and m >= end:
                continue
            usage.append({"customer_id": cid, "month": m,
                          "active_users": max(0, int(rng.gauss(seats * 0.7, seats * 0.3)))})
    # salesforce opportunities: customers and prospects who never signed, on their own timeline
    pool = [c["customer_id"] for c in customers if c["segment"] != "smb"] + [None] * 220
    for oid, cust in enumerate(pool, 1):
        created = START + timedelta(days=rng.randint(0, (END - START).days))
        qualified = created + timedelta(days=rng.randint(3, 50)) if rng.random() < 0.65 else None
        if qualified and qualified > END:
            qualified = None
        opps.append({"opp_id": oid, "customer_id": cust, "created": created, "qualified_at": qualified,
                     "amount": PLANS[rng.choice(["team", "business"])] * rng.randint(5, 40) * 12,
                     "source": rng.choice(["outbound", "inbound", "partner"])})
    return customers, subs, invoices, opps, usage
