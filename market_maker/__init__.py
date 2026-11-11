"""Paper market maker. Fair value is a Glosten–Milgrom posterior."""

from market_maker.bot import Fill, MarketMaker
from market_maker.model import GlostenMilgrom, InconsistentObservation, Quote

__all__ = [
    "Fill",
    "GlostenMilgrom",
    "InconsistentObservation",
    "MarketMaker",
    "Quote",
]
