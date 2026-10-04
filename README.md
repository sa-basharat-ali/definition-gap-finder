# Definition gap finder

```
python3 run.py      # stdlib only, no install, under a second
```

The report a forward deployed analyst brings to a new customer's week-one review: every question
leadership is about to ask, computed under each definition a reasonable analyst might pick, ranked
by how far apart the answers are. The top of the list is the order in which definitions get
settled with the customer's data owner.

The customer is synthetic: a B2B SaaS company with 600 accounts, Stripe subscriptions and 2,607
invoices (discounts, trials, annual prepay, refunds, euros), 466 Salesforce opportunities with a
qualification date, and monthly product usage. Fixed seed, no real company.

## The report

| # | Question | Defensible answers | Spread |
|---|---|---|---|
| 1 | What was churn this month? | logo 2.1% · gross revenue 0.2% · net revenue −3.0% · logo incl. expired trials 4.3% | answers disagree on the sign |
| 2 | How many customers do we have? | 620 Stripe customer objects · 370 accounts ever paid · 301 active this month | 106% |
| 3 | How much pipeline did we create in Q3? | $40.9M by created date · $26.4M by qualified date | 55% |
| 4 | What's our net revenue retention? | 101.8% on subscription MRR · 95.0% on invoices spread over their period · 84.4% on cash billed | 17.4 pts |
| 5 | What's our trial conversion rate? | 67.8% at trial end · 60.0% still paying now | 7.8 pts |
| 6 | What's our ARR? | $54.3M subscriptions · $58.8M this month's invoices × 12 · $52.5M invoices spread · $53.1M euros unconverted | 12% |
| 7 | How many active users do we have? | 1,998 all accounts · 1,950 paying accounts | 2% |

Two things fall out. **Churn and NRR can each be told as good news or bad news** depending on the
definition, which is the conversation leadership least wants to have after launch. And **active
users barely moves**, so it doesn't need a meeting: the report also says where not to spend time.

Every row becomes one written definition, a golden answer the customer's data owner signs off, and a
test that runs nightly, before the first user asks.

## The part I got wrong

My first customer generator made churn a one-time coin flip: an account either churned in its first
paid month or never. This month's churn then read 0.0% under every definition, and a gap finder
would have marked churn as settled. Agreement between definitions can mean the data is broken, not
that the metric is clear, which is why an onboarding validates the data before it trusts the
agreement.

## Files

| | |
|---|---|
| `customer.py` | the synthetic customer: Stripe, Salesforce, usage |
| `run.py` | the questions, their definitions, and the ranked report |
| `index.html` | the onboarding playbook and the report, as one page |

Syed Ahmed Basharat Ali · sabasharat.ali@gmail.com · basharat.net
