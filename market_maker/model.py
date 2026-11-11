"""Zero-profit quotes from a two-point Glosten–Milgrom posterior.

The latent value is ``value_high`` with probability ``p_high`` and
``value_low`` otherwise. A fraction ``informed_fraction`` of counterparties
know the value and trade in that direction. The rest buy or sell with equal
probability. The maker cannot tell which kind just arrived, so Bayes' rule
is the whole update.
"""

from dataclasses import dataclass


class InconsistentObservation(Exception):
    """A fill has probability zero under the current posterior."""


@dataclass(frozen=True)
class Quote:
    bid: float
    ask: float
    fair_value: float
    p_high: float


class GlostenMilgrom:
    def __init__(
        self,
        *,
        p_high: float,
        informed_fraction: float,
        value_high: float,
        value_low: float,
    ) -> None:
        if not 0.0 <= p_high <= 1.0:
            raise ValueError("p_high must be between 0 and 1")
        if not 0.0 <= informed_fraction <= 1.0:
            raise ValueError("informed_fraction must be between 0 and 1")
        if value_high <= value_low:
            raise ValueError("value_high must exceed value_low")
        self.p_high = float(p_high)
        self.informed_fraction = float(informed_fraction)
        self.value_high = float(value_high)
        self.value_low = float(value_low)

    @property
    def fair_value(self) -> float:
        return self.p_high * self.value_high + (1.0 - self.p_high) * self.value_low

    def quote(self) -> Quote:
        """Bid is E[V | sell], ask is E[V | buy]. Does not change the posterior."""
        return Quote(
            bid=self._expectation(self._posterior("sell")),
            ask=self._expectation(self._posterior("buy")),
            fair_value=self.fair_value,
            p_high=self.p_high,
        )

    def observe(self, aggressor_side: str) -> float:
        """Replace the posterior with the belief conditional on this fill."""
        self.p_high = self.posterior_after(aggressor_side)
        return self.fair_value

    def posterior_after(self, aggressor_side: str) -> float:
        """Probability of the high value if this fill were observed. Does not write."""
        return self._posterior(aggressor_side)

    def _posterior(self, aggressor_side: str) -> float:
        if aggressor_side not in ("buy", "sell"):
            raise ValueError("aggressor_side must be 'buy' or 'sell'")
        likelihood = self._buy_likelihood if aggressor_side == "buy" else self._sell_likelihood
        numerator = self.p_high * likelihood(True)
        denominator = numerator + (1.0 - self.p_high) * likelihood(False)
        if denominator == 0.0:
            raise InconsistentObservation(
                f"a {aggressor_side} has probability zero at p_high={self.p_high}"
            )
        return numerator / denominator

    def _expectation(self, p_high: float) -> float:
        return p_high * self.value_high + (1.0 - p_high) * self.value_low

    def _buy_likelihood(self, high: bool) -> float:
        pi = self.informed_fraction
        if high:
            return pi + (1.0 - pi) / 2.0
        return (1.0 - pi) / 2.0

    def _sell_likelihood(self, high: bool) -> float:
        return 1.0 - self._buy_likelihood(high)
