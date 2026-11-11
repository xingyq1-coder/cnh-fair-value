# Spec: paper market maker with a Bayesian fair value

## Problem

Quote a two-sided market in a hidden value, and after every fill replace the fair value with the conditional expectation given that fill.

## Scope

- One instrument. Latent value is one of two numbers.
- Counterparties are a mixture of informed traders and noise. The maker does not observe the type.
- Fair value is the posterior mean. Bid is the expectation conditional on a sell, ask conditional on a buy. That is the Glosten–Milgrom zero-profit quote.
- A fill updates the posterior once. Repeating the same fill id does not update again.
- A fill whose price is not the live quote is refused, and the posterior stays put.
- Inventory is capped. A fill that would breach the cap is refused, and the posterior stays put.
- A fill with probability zero under the current belief is refused.
- Paper only. No exchange session, no credentials, no order gateway.

## Out of scope

- Inventory skew of the Avellaneda–Stoikov kind. The fair value stays a pure posterior.
- Live or paper brokerage. This book does not submit orders.
- A continuous prior, a full order book, or the AI-complex signal card.

## Acceptance

- With no informed flow, bid and ask equal the prior mean.
- With a symmetric prior, the spread equals the informed fraction times the gap between the two values.
- After a buy, fair value equals the ask that was just lifted. After a sell, it equals the bid that was just hit.
- Quoting alone does not move the posterior.
- Duplicate ids, stale prices, inventory breaches, and impossible fills leave cash, inventory, and the posterior unchanged.
