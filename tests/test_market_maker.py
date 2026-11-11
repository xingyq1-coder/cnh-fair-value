"""Glosten–Milgrom market maker: Bayes update of fair value after each fill."""

import unittest

from market_maker.bot import MarketMaker, Fill
from market_maker.model import GlostenMilgrom, InconsistentObservation


class QuoteTests(unittest.TestCase):
    def test_no_informed_flow_quotes_a_zero_spread_at_fair_value(self):
        book = GlostenMilgrom(p_high=0.5, informed_fraction=0.0, value_high=101.0, value_low=99.0)
        quote = book.quote()
        self.assertAlmostEqual(quote.fair_value, 100.0)
        self.assertAlmostEqual(quote.bid, 100.0)
        self.assertAlmostEqual(quote.ask, 100.0)
        self.assertEqual(book.p_high, 0.5)

    def test_symmetric_prior_spread_equals_informed_fraction_times_value_range(self):
        value_high, value_low = 101.0, 99.0
        for pi in (0.0, 0.05, 0.1, 0.2, 0.4, 0.8):
            book = GlostenMilgrom(
                p_high=0.5, informed_fraction=pi, value_high=value_high, value_low=value_low
            )
            quote = book.quote()
            self.assertAlmostEqual(quote.ask - quote.bid, pi * (value_high - value_low))
            self.assertAlmostEqual(quote.fair_value, 100.0)
            self.assertLessEqual(quote.bid, quote.fair_value)
            self.assertGreaterEqual(quote.ask, quote.fair_value)

    def test_quoting_does_not_change_the_posterior(self):
        book = GlostenMilgrom(p_high=0.35, informed_fraction=0.25, value_high=110.0, value_low=90.0)
        before = book.p_high
        book.quote()
        book.quote()
        self.assertEqual(book.p_high, before)


class BayesUpdateTests(unittest.TestCase):
    def test_buy_fill_moves_fair_value_to_the_ask_that_was_quoted(self):
        book = GlostenMilgrom(p_high=0.5, informed_fraction=0.2, value_high=101.0, value_low=99.0)
        quoted = book.quote()
        book.observe("buy")
        self.assertAlmostEqual(book.fair_value, quoted.ask)
        self.assertGreater(book.p_high, 0.5)

    def test_sell_fill_moves_fair_value_to_the_bid_that_was_quoted(self):
        book = GlostenMilgrom(p_high=0.5, informed_fraction=0.2, value_high=101.0, value_low=99.0)
        quoted = book.quote()
        book.observe("sell")
        self.assertAlmostEqual(book.fair_value, quoted.bid)
        self.assertLess(book.p_high, 0.5)

    def test_repeated_buys_walk_the_posterior_up_monotonically(self):
        book = GlostenMilgrom(p_high=0.5, informed_fraction=0.3, value_high=101.0, value_low=99.0)
        previous = book.p_high
        for _ in range(6):
            book.observe("buy")
            self.assertGreater(book.p_high, previous)
            self.assertLess(book.p_high, 1.0)
            previous = book.p_high

    def test_impossible_buy_when_value_cannot_be_high_is_rejected(self):
        book = GlostenMilgrom(p_high=0.0, informed_fraction=1.0, value_high=101.0, value_low=99.0)
        with self.assertRaises(InconsistentObservation):
            book.observe("buy")
        self.assertEqual(book.p_high, 0.0)

    def test_asymmetric_prior_matches_bayes_by_hand(self):
        p, pi = 0.25, 0.4
        book = GlostenMilgrom(p_high=p, informed_fraction=pi, value_high=104.0, value_low=96.0)
        p_buy_high = pi + (1 - pi) / 2
        p_buy_low = (1 - pi) / 2
        expected = (p * p_buy_high) / (p * p_buy_high + (1 - p) * p_buy_low)
        book.observe("buy")
        self.assertAlmostEqual(book.p_high, expected)


class BotTests(unittest.TestCase):
    def setUp(self):
        self.maker = MarketMaker(
            p_high=0.5,
            informed_fraction=0.2,
            value_high=101.0,
            value_low=99.0,
            max_abs_inventory=1.0,
        )

    def test_buy_fill_sells_inventory_at_the_ask_and_updates_once(self):
        quoted = self.maker.quote()
        result = self.maker.apply(Fill(fill_id="f1", aggressor_side="buy", size=1.0))
        self.assertEqual(result.status, "applied")
        self.assertAlmostEqual(result.cash, quoted.ask)
        self.assertAlmostEqual(result.inventory, -1.0)
        self.assertAlmostEqual(result.fair_value, quoted.ask)
        self.assertAlmostEqual(self.maker.fair_value, quoted.ask)

    def test_duplicate_fill_id_does_not_update_again(self):
        self.maker.apply(Fill(fill_id="f1", aggressor_side="buy", size=1.0))
        after = (self.maker.fair_value, self.maker.inventory, self.maker.cash)
        result = self.maker.apply(Fill(fill_id="f1", aggressor_side="buy", size=1.0))
        self.assertEqual(result.status, "duplicate")
        self.assertEqual((self.maker.fair_value, self.maker.inventory, self.maker.cash), after)

    def test_inventory_limit_refuses_the_fill_and_leaves_the_posterior(self):
        self.maker.apply(Fill(fill_id="f1", aggressor_side="buy", size=1.0))
        held = self.maker.fair_value
        result = self.maker.apply(Fill(fill_id="f2", aggressor_side="buy", size=1.0))
        self.assertEqual(result.status, "rejected_inventory")
        self.assertAlmostEqual(self.maker.fair_value, held)
        self.assertAlmostEqual(self.maker.inventory, -1.0)
        self.assertNotIn("f2", self.maker.applied_ids)

    def test_stale_price_is_refused(self):
        result = self.maker.apply(
            Fill(fill_id="f1", aggressor_side="buy", size=1.0, price=0.0)
        )
        self.assertEqual(result.status, "rejected_stale_price")
        self.assertAlmostEqual(self.maker.fair_value, 100.0)
        self.assertEqual(self.maker.inventory, 0.0)

    def test_sell_then_buy_round_trip_cash_is_the_spread_captured(self):
        first = self.maker.quote()
        self.maker.apply(Fill(fill_id="sell-1", aggressor_side="sell", size=1.0))
        self.maker.apply(Fill(fill_id="buy-1", aggressor_side="buy", size=1.0))
        self.assertAlmostEqual(self.maker.inventory, 0.0)
        self.assertGreater(self.maker.cash, 0.0)
        self.assertLess(first.bid, first.ask)


if __name__ == "__main__":
    unittest.main()
