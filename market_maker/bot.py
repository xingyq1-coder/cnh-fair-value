"""Paper book: one Bayesian update per new fill, at the quote that was live."""

from dataclasses import dataclass

from market_maker.model import GlostenMilgrom, InconsistentObservation, Quote


@dataclass(frozen=True)
class Fill:
    """Aggressor side is the counterparty's direction. ``buy`` lifts our ask."""

    fill_id: str
    aggressor_side: str
    size: float = 1.0
    price: float | None = None


@dataclass(frozen=True)
class ApplyResult:
    status: str
    quote: Quote
    inventory: float
    cash: float
    fair_value: float


class MarketMaker:
    def __init__(
        self,
        *,
        p_high: float,
        informed_fraction: float,
        value_high: float,
        value_low: float,
        max_abs_inventory: float,
    ) -> None:
        if max_abs_inventory <= 0:
            raise ValueError("max_abs_inventory must be positive")
        self._book = GlostenMilgrom(
            p_high=p_high,
            informed_fraction=informed_fraction,
            value_high=value_high,
            value_low=value_low,
        )
        self.max_abs_inventory = float(max_abs_inventory)
        self.inventory = 0.0
        self.cash = 0.0
        self.applied_ids: set[str] = set()

    @property
    def fair_value(self) -> float:
        return self._book.fair_value

    @property
    def p_high(self) -> float:
        return self._book.p_high

    def quote(self) -> Quote:
        return self._book.quote()

    def apply(self, fill: Fill) -> ApplyResult:
        if fill.fill_id in self.applied_ids:
            return self._result("duplicate")
        if fill.aggressor_side not in ("buy", "sell"):
            raise ValueError("aggressor_side must be 'buy' or 'sell'")
        if fill.size <= 0:
            raise ValueError("size must be positive")

        quote = self._book.quote()
        trade_price = quote.ask if fill.aggressor_side == "buy" else quote.bid
        if fill.price is not None and abs(fill.price - trade_price) > 1e-9:
            return self._result("rejected_stale_price")

        next_inventory = self.inventory - fill.size if fill.aggressor_side == "buy" else self.inventory + fill.size
        if abs(next_inventory) > self.max_abs_inventory + 1e-12:
            return self._result("rejected_inventory")

        try:
            updated = self._book.posterior_after(fill.aggressor_side)
        except InconsistentObservation:
            return self._result("rejected_inconsistent")

        self.inventory = next_inventory
        if fill.aggressor_side == "buy":
            self.cash += trade_price * fill.size
        else:
            self.cash -= trade_price * fill.size
        self._book.p_high = updated
        self.applied_ids.add(fill.fill_id)
        return self._result("applied")

    def _result(self, status: str) -> ApplyResult:
        return ApplyResult(
            status=status,
            quote=self._book.quote(),
            inventory=self.inventory,
            cash=self.cash,
            fair_value=self._book.fair_value,
        )
