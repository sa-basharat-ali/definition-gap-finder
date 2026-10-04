"""python3 run.py  -- the definition gap report an FDA would bring to a customer's week-one review."""
from collections import defaultdict
from datetime import date

import customer as C

customers, subs, invoices, opps, usage = C.build()
MONTH = date(2026, 9, 1)            # "this month" for every question
PREV = date(2026, 8, 1)
Q3 = (date(2026, 7, 1), date(2026, 9, 30))


def usd(x, cur):
    return x * C.FX[cur]


def active_at(s, m):
    return s["status"] != "trial_expired" and s["start"] <= m and (s["end"] is None or s["end"] > m)


def mrr_sub(s, m, fx=True):
    extra = sum(k for d, k in s.get("upgrades", []) if d <= m)
    v = C.PLANS[s["plan"]] * (1 - s["discount"]) * (s["seats"] + extra)
    return usd(v, s["currency"]) if fx else v


# ---- the questions leadership asks, each with the definitions a reasonable analyst might pick ----
def q_customers():
    return {
        "Stripe customer objects": sum(len(c["stripe_ids"]) for c in customers),
        "accounts with any paid invoice": len({i["customer_id"] for i in invoices}),
        "accounts active this month": sum(1 for s in subs if active_at(s, MONTH)),
    }


def q_arr():
    return {
        "subscription MRR x 12 (list, after discount)": sum(mrr_sub(s, MONTH) for s in subs if active_at(s, MONTH)) * 12,
        "this month's invoices x 12": sum(usd(i["amount"], i["currency"]) for i in invoices if i["date"] == MONTH and not i["refunded"]) * 12,
        "invoices spread over their period x 12": sum(usd(i["amount"], i["currency"]) / i["period_months"]
                                                      for i in invoices if i["date"] <= MONTH and
                                                      (i["date"].year * 12 + i["date"].month) + i["period_months"] >
                                                      (MONTH.year * 12 + MONTH.month) and not i["refunded"]) * 12,
        "subscription MRR x 12, EUR not converted": sum(mrr_sub(s, MONTH, fx=False) for s in subs if active_at(s, MONTH)) * 12,
    }


def q_churn():
    start = [s for s in subs if active_at(s, PREV)]
    lost = [s for s in start if not active_at(s, MONTH)]
    lost_mrr = sum(mrr_sub(s, PREV) for s in lost)
    start_mrr = sum(mrr_sub(s, PREV) for s in start)
    expand = sum(mrr_sub(s, MONTH) - mrr_sub(s, PREV) for s in start if active_at(s, MONTH))
    trials = [s for s in subs if s["status"] == "trial_expired" and PREV <= s["end"] < MONTH]
    return {
        "logo churn (paid accounts lost / paid at start)": len(lost) / len(start) * 100,
        "gross revenue churn (MRR lost / MRR at start)": lost_mrr / start_mrr * 100,
        "net revenue churn (lost minus expansion)": (lost_mrr - expand) / start_mrr * 100,
        "logo churn counting expired trials": (len(lost) + len(trials)) / (len(start) + len(trials)) * 100,
    }


def q_nrr():
    year_ago = date(2025, 9, 1)
    cohort = [s for s in subs if active_at(s, year_ago)]
    ids = {s["customer_id"] for s in cohort}
    base = sum(mrr_sub(s, year_ago) for s in cohort)
    now = sum(mrr_sub(s, MONTH) for s in cohort if active_at(s, MONTH))

    def cash(m):  # invoice value recognised in month m, annual prepay spread over 12
        t = m.year * 12 + m.month
        return sum(usd(i["amount"], i["currency"]) / i["period_months"] for i in invoices
                   if i["customer_id"] in ids and not i["refunded"]
                   and i["date"].year * 12 + i["date"].month <= t < i["date"].year * 12 + i["date"].month + i["period_months"])

    def billed(m):  # cash invoiced in month m, no spreading
        return sum(usd(i["amount"], i["currency"]) for i in invoices
                   if i["customer_id"] in ids and i["date"] == m and not i["refunded"])
    return {
        "NRR on subscription MRR": now / base * 100 if base else 0,
        "NRR on invoices, spread over their period": cash(MONTH) / cash(year_ago) * 100 if cash(year_ago) else 0,
        "NRR on cash billed in the month": billed(MONTH) / billed(year_ago) * 100 if billed(year_ago) else 0,
    }


def q_pipeline():
    a, b = Q3
    return {
        "opportunities created in Q3 ($)": sum(o["amount"] for o in opps if a <= o["created"] <= b),
        "opportunities qualified in Q3 ($)": sum(o["amount"] for o in opps if o["qualified_at"] and a <= o["qualified_at"] <= b),
    }


def q_active_users():
    rows = [u for u in usage if u["month"] == MONTH]
    paying = {s["customer_id"] for s in subs if active_at(s, MONTH)}
    return {
        "active users, all accounts with usage": sum(u["active_users"] for u in rows),
        "active users, paying accounts only": sum(u["active_users"] for u in rows if u["customer_id"] in paying),
    }


def q_trial_conversion():
    started = [s for s in subs if C.date(2026, 6, 1) <= s["trial_end"] < C.date(2026, 9, 1)]
    conv = [s for s in started if s["status"] != "trial_expired"]
    conv_kept = [s for s in conv if active_at(s, C.date(2026, 9, 1))]
    return {
        "converted at trial end": len(conv) / len(started) * 100,
        "converted and still paying this month": len(conv_kept) / len(started) * 100,
    }


QUESTIONS = [
    ("How many customers do we have?", q_customers, "count"),
    ("What's our ARR?", q_arr, "money"),
    ("What was churn this month?", q_churn, "pct"),
    ("What's our net revenue retention?", q_nrr, "pct"),
    ("How much pipeline did we create in Q3?", q_pipeline, "money"),
    ("How many active users do we have?", q_active_users, "count"),
    ("What's our trial conversion rate?", q_trial_conversion, "pct"),
]


def fmt(v, kind):
    return f"${v / 1e6:,.2f}M" if kind == "money" else (f"{v:.1f}%" if kind == "pct" else f"{v:,.0f}")


print("=" * 78)
print("Definition gap report: synthetic SaaS customer, week one of onboarding")
print("=" * 78)
paid = len({i['customer_id'] for i in invoices})
print(f"accounts {len(customers)} | subscriptions {len(subs)} | invoices {len(invoices)} | "
      f"opportunities {len(opps)} | usage rows {len(usage)}")

report = []
for q, fn, kind in QUESTIONS:
    ans = fn()
    vals = list(ans.values())
    lo, hi = min(vals), max(vals)
    spread = (hi - lo) / abs(lo) * 100 if lo else float("inf")
    # one comparable score: gap as a share of the largest answer; sign flips score above 100
    score = (hi - lo) / max(abs(hi), abs(lo)) * 100
    spread_txt = f"{hi - lo:.1f} pts" if kind == "pct" else f"{spread:.0f}%"
    if lo < 0 < hi:
        spread_txt += ", answers disagree on the sign"
    report.append((score, q, kind, ans, spread_txt))

print("\nRanked by how far apart the defensible answers are (settle the top ones first):\n")
for i, (score, q, kind, ans, st) in enumerate(sorted(report, key=lambda r: -r[0]), 1):
    print(f"{i}. {q}   spread {st}")
    for k, v in ans.items():
        print(f"     {fmt(v, kind):>10}  {k}")
    print()

print("Every one of these is a decision for the customer's data owner, not a bug to fix silently.")
print("Each gets one written definition, a golden answer they sign off, and a test that runs nightly.")
