# Plan: paper market maker

1. Failing tests for the zero-spread case, the symmetric spread identity, and quoting without mutation.
2. Failing tests for the Bayes update: a buy lands on the quoted ask, a sell on the quoted bid, a run of buys is monotone, an impossible buy is rejected, and one asymmetric case matches the hand calculation.
3. Failing tests for the book: cash and inventory at the quote, duplicate fill ids, the inventory cap, a stale price, and a round trip that keeps the captured spread.
4. Implement `GlostenMilgrom` so the quote tests and the update tests pass, with the posterior changed only in `observe`.
5. Implement `MarketMaker.apply` so a fill is applied at the pre-update quote, the posterior moves only after cash and inventory move, and every refusal returns before any write.
6. Add a scripted tape printer that never opens a socket.
7. Run `python -m unittest discover -s tests -t .` from the repository root.
