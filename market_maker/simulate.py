"""Run a scripted paper tape and print the posterior after each fill.

Nothing here talks to an exchange. The true value is fixed and hidden; informed
arrivals trade in its direction, and the maker only sees the fill.
"""

from market_maker.bot import Fill, MarketMaker


def main() -> None:
    maker = MarketMaker(
        p_high=0.5,
        informed_fraction=0.3,
        value_high=101.0,
        value_low=99.0,
        max_abs_inventory=20.0,
    )
    print("scripted tape, hidden value high. next_bid and next_ask are quoted after the fill.")
    print(f"{'n':<4}{'side':<6}{'trade':>10}{'p_after':>10}{'fair':>10}{'next_bid':>10}{'next_ask':>10}{'inv':>6}")
    for i, side in enumerate(("buy", "buy", "sell", "buy", "buy", "buy"), start=1):
        cash_before = maker.cash
        result = maker.apply(Fill(fill_id=f"t{i}", aggressor_side=side, size=1.0))
        trade = result.cash - cash_before
        quote = result.quote
        print(
            f"{i:<4}{side:<6}{trade:10.4f}{maker.p_high:10.4f}{result.fair_value:10.4f}"
            f"{quote.bid:10.4f}{quote.ask:10.4f}{result.inventory:6.0f}"
        )


if __name__ == "__main__":
    main()
