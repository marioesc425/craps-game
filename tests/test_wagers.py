import unittest
from dataclasses import replace

from craps.engine.bets import Bet, BetOutcome, BetType
from craps.engine.game import CrapsEngine
from craps.engine.player import Player, InvalidBetError
from craps.engine.settlement import settle_bet
from craps.engine.config import DEFAULT_TABLE_RULES


class WagerRulesTests(unittest.TestCase):
    def test_all_comeout_totals(self):
        outcomes = {
            2: BetOutcome.LOSE, 3: BetOutcome.LOSE, 4: BetOutcome.NO_ACTION,
            5: BetOutcome.NO_ACTION, 6: BetOutcome.NO_ACTION, 7: BetOutcome.WIN,
            8: BetOutcome.NO_ACTION, 9: BetOutcome.NO_ACTION, 10: BetOutcome.NO_ACTION,
            11: BetOutcome.WIN, 12: BetOutcome.LOSE,
        }
        pairs = {2:(1,1),3:(1,2),4:(1,3),5:(1,4),6:(1,5),7:(1,6),
                 8:(2,6),9:(3,6),10:(4,6),11:(5,6),12:(6,6)}
        for total, expected in outcomes.items():
            self.assertEqual(settle_bet(Bet(BetType.PASS_LINE, 10), pairs[total], None).outcome, expected)

    def test_dont_pass_comeout_and_point(self):
        cases = [((1,1), BetOutcome.WIN), ((1,2), BetOutcome.WIN),
                 ((3,4), BetOutcome.LOSE), ((5,6), BetOutcome.LOSE),
                 ((6,6), BetOutcome.PUSH)]
        for dice, outcome in cases:
            self.assertEqual(settle_bet(Bet(BetType.DONT_PASS, 10), dice, None).outcome, outcome)
        self.assertEqual(settle_bet(Bet(BetType.DONT_PASS, 10), (3,4), 8).outcome, BetOutcome.WIN)
        self.assertEqual(settle_bet(Bet(BetType.DONT_PASS, 10), (4,4), 8).outcome, BetOutcome.LOSE)

    def test_come_and_dont_come_move_then_resolve(self):
        come = Bet(BetType.COME, 10)
        self.assertEqual(settle_bet(come, (2,3), 6).outcome, BetOutcome.NO_ACTION)
        self.assertEqual(come.number, 5)
        self.assertEqual(settle_bet(come, (2,3), 6).amount, 20)
        dont_come = Bet(BetType.DONT_COME, 10)
        settle_bet(dont_come, (2,3), 6)
        self.assertEqual(dont_come.number, 5)
        self.assertEqual(settle_bet(dont_come, (2,3), 6).outcome, BetOutcome.LOSE)

    def test_place_payouts_and_seven(self):
        for number, (num, den) in {4:(9,5),5:(7,5),6:(7,6),8:(7,6),9:(7,5),10:(9,5)}.items():
            stake = den * 5
            self.assertEqual(settle_bet(Bet(BetType.PLACE, stake, number), (number//2, number-number//2), 6).amount,
                             stake + stake*num//den)
            self.assertEqual(settle_bet(Bet(BetType.PLACE, stake, number), (3,4), 6).outcome, BetOutcome.LOSE)

    def test_field_outcomes(self):
        pairs = {2:(1,1),3:(1,2),4:(1,3),9:(3,6),10:(4,6),11:(5,6)}
        for total, dice in pairs.items():
            r = settle_bet(Bet(BetType.FIELD, 5), dice, None)
            self.assertEqual(r.outcome, BetOutcome.WIN)
            self.assertEqual(r.amount, 15 if total == 2 else 10)
        for dice in ((1,4),(2,4),(1,6),(2,6)):
            self.assertEqual(settle_bet(Bet(BetType.FIELD, 5), dice, None).outcome, BetOutcome.LOSE)
        self.assertEqual(settle_bet(Bet(BetType.FIELD, 5), (6,6), None).outcome, BetOutcome.WIN)

    def test_configurable_field_and_twelve_rule(self):
        self.assertEqual(settle_bet(Bet(BetType.FIELD, 5), (1,1), None, 3).amount, 20)
        self.assertEqual(settle_bet(Bet(BetType.DONT_PASS, 5), (6,6), None, dont_pass_12_push=False).outcome,
                         BetOutcome.LOSE)

    def test_field_twelve_wins_with_configured_house_payout(self):
        self.assertEqual(settle_bet(Bet(BetType.FIELD, 5), (6,6), None).amount, 15)
        rules = replace(DEFAULT_TABLE_RULES, field_twelve_payout=3)
        self.assertEqual(settle_bet(Bet(BetType.FIELD, 5), (6,6), None, rules=rules).amount, 20)

    def test_exact_gross_returns_for_requested_examples(self):
        cases = [
            (Bet(BetType.PASS_LINE, 5), (3,4), None, 10),
            (Bet(BetType.PLACE, 10, 4), (1,3), 6, 28),
            (Bet(BetType.PLACE, 25, 5), (2,3), 6, 60),
            (Bet(BetType.PLACE, 30, 6), (3,3), 6, 65),
            (Bet(BetType.HARDWAY, 10, 4), (2,2), 6, 80),
            (Bet(BetType.PASS_LINE, 5, odds=10), (1,3), 4, 40),
            (Bet(BetType.DONT_PASS, 10), (6,6), None, 10),
        ]
        for bet, dice, point, gross_return in cases:
            with self.subTest(bet=bet):
                self.assertEqual(settle_bet(bet, dice, point).amount, gross_return)

    def test_one_dollar_stakes_have_exact_whole_dollar_returns(self):
        cases = [
            (BetType.PASS_LINE, None, (3, 4), None, 2),
            (BetType.FIELD, None, (1, 1), None, 3),
            (BetType.FIELD, None, (1, 2), None, 2),
            (BetType.HARDWAY, 4, (2, 2), 6, 8),
            (BetType.ANY_SEVEN, None, (3, 4), None, 5),
            (BetType.ACE_DEUCE, None, (1, 2), None, 16),
            (BetType.ACES, None, (1, 1), None, 31),
            (BetType.BOXCARS, None, (6, 6), None, 31),
            (BetType.YO_ELEVEN, None, (5, 6), None, 16),
            (BetType.ANY_CRAPS, None, (1, 2), None, 8),
        ]
        for bet_type, number, dice, point, gross in cases:
            with self.subTest(bet=bet_type):
                self.assertEqual(settle_bet(Bet(bet_type, 1, number), dice, point).amount, gross)

    def test_central_table_limits_and_no_split_bypass(self):
        rules = replace(DEFAULT_TABLE_RULES, starting_bankroll=1500)
        p = Player(rules=rules)
        self.assertEqual(rules.minimum_bet, 1)
        one_dollar = p.place_wager(BetType.PASS_LINE, 1)
        self.assertEqual((one_dollar.amount, p.bankroll), (1, 1499))
        p.undo_wager(one_dollar)
        wager = p.place_wager(BetType.PASS_LINE, 500)
        self.assertEqual((wager.amount, p.bankroll), (500, 1000))
        with self.assertRaises(InvalidBetError):
            p.increase_wager(wager, 1)
        with self.assertRaises(InvalidBetError):
            p.place_wager(BetType.PASS_LINE, 5)
        self.assertEqual((wager.amount, p.bankroll), (500, 1000))

    def test_bankroll_below_table_minimum_cannot_start_a_wager(self):
        p = Player()
        p.bankroll = 0
        self.assertFalse(p.can_play())
        with self.assertRaises(InvalidBetError):
            p.place_wager(BetType.FIELD, 1)
        self.assertEqual((p.bankroll, p.active_bets), (0, []))

    def test_all_five_standard_chip_denominations_place_exact_amounts(self):
        rules = replace(DEFAULT_TABLE_RULES, starting_bankroll=1500)
        for chip in rules.chip_denominations:
            with self.subTest(chip=chip):
                p = Player(rules=rules)
                wager = p.place_wager(BetType.PASS_LINE, chip)
                expected_total = chip
                self.assertEqual(wager.amount, expected_total)
                self.assertEqual(p.bankroll, 1500 - expected_total)

    def test_place_six_increment_rejected_without_deduction(self):
        p = Player()
        with self.assertRaises(InvalidBetError):
            p.place_wager(BetType.PLACE, 5, 6)
        self.assertEqual((p.bankroll, p.active_bets), (100, []))
        p.place_wager(BetType.PLACE, 6, 6)
        with self.assertRaises(InvalidBetError):
            p.increase_wager(p.active_bets[0], 1)
        self.assertEqual((p.bankroll, p.active_bets[0].amount), (94, 6))

    def test_place_reductions_must_preserve_exact_payout_compatibility(self):
        player = Player()
        bet = player.place_wager(BetType.PLACE, 6, 6)
        with self.assertRaises(InvalidBetError):
            player.reduce_wager(bet, 1)
        self.assertEqual((bet.amount, player.bankroll), (6, 94))
        with self.assertRaises(ValueError):
            settle_bet(Bet(BetType.PLACE, 1, 6), (3, 3), 6)

    def test_hardways(self):
        for number, pair, payout in ((4,(2,2),7),(6,(3,3),9),(8,(4,4),9),(10,(5,5),7)):
            self.assertEqual(settle_bet(Bet(BetType.HARDWAY, 5, number), pair, 6).amount, 5+5*payout)
            easy = {4:(1,3), 6:(2,4), 8:(3,5), 10:(4,6)}[number]
            self.assertEqual(settle_bet(Bet(BetType.HARDWAY, 5, number), easy, 6).outcome, BetOutcome.LOSE)
            self.assertEqual(settle_bet(Bet(BetType.HARDWAY, 5, number), (3,4), 6).outcome, BetOutcome.LOSE)

    def test_bankroll_deduct_credit_push_and_active_bets(self):
        player, game = Player(), CrapsEngine()
        player.place_wager(BetType.PASS_LINE, 10)
        self.assertEqual(player.bankroll, 90)
        player.settle(game.resolve_roll((1,1), player.active_bets))
        self.assertEqual(player.bankroll, 90)
        player.place_wager(BetType.PASS_LINE, 10)
        player.settle(game.resolve_roll((1,3), player.active_bets))
        win_result = game.resolve_roll((2,2), player.active_bets)
        player.settle(win_result)
        settled_bankroll = player.bankroll
        player.settle(win_result)
        self.assertEqual(player.bankroll, settled_bankroll)
        player.place_wager(BetType.DONT_PASS, 10)
        player.settle(game.resolve_roll((6,6), player.active_bets))
        self.assertEqual(player.bankroll, 100)
        self.assertFalse(player.active_bets)

    def test_odds_limits_and_exactness(self):
        p = Player()
        bet = p.place_wager(BetType.PASS_LINE, 10)
        with self.assertRaises(InvalidBetError): p.add_odds(bet, 5, None)
        engine = CrapsEngine()
        engine.resolve_roll((2,3), p.active_bets)
        p.add_odds(bet, 10, 5)
        self.assertEqual(bet.odds, 10)
        self.assertEqual(settle_bet(bet, (2,3), 5).amount, 20 + 25)
        with self.assertRaises(InvalidBetError): p.add_odds(bet, 25, 5)
        dont = Bet(BetType.DONT_PASS, 10, odds=6)
        # Don't Pass odds on 5 pay 2:3: a $6 odds stake returns $10.
        self.assertEqual(settle_bet(dont, (1,6), 5).amount, 20 + 10)

    def test_invalid_wagers_are_rejected(self):
        p = Player()
        for amount in (0, -1, 101):
            with self.assertRaises(InvalidBetError): p.place_wager(BetType.FIELD, amount)
        with self.assertRaises(InvalidBetError): p.place_wager(BetType.PLACE, 5, 6)
        with self.assertRaises(InvalidBetError): p.place_wager(BetType.COME, 5, odds=5, point=6)
        with self.assertRaises(InvalidBetError): p.place_wager(BetType.COME, 5)
        with self.assertRaises(InvalidBetError): p.place_wager(BetType.PASS_LINE, 5, point=6)

    def test_independent_simultaneous_bets_and_point_reset(self):
        player, game = Player(), CrapsEngine()
        pass_bet = player.place_wager(BetType.PASS_LINE, 10)
        field_bet = player.place_wager(BetType.FIELD, 5)
        player.settle(game.resolve_roll((1,1), player.active_bets))
        self.assertIsNone(game.point)
        self.assertEqual(player.bankroll, 100)  # Pass loses $10; Field 2 returns $15.
        self.assertFalse(player.active_bets)
        place = player.place_wager(BetType.PLACE, 5, 4)
        point = player.place_wager(BetType.PASS_LINE, 5)
        player.settle(game.resolve_roll((1,3), player.active_bets))
        player.settle(game.resolve_roll((1,3), player.active_bets))
        self.assertIsNone(game.point)
        self.assertNotIn(place, player.active_bets)
        self.assertNotIn(point, player.active_bets)

    def test_field_bet_expires_and_integrity(self):
        p, game = Player(), CrapsEngine()
        b = p.place_wager(BetType.FIELD, 5)
        p.settle(game.resolve_roll((2,3), p.active_bets))
        self.assertEqual(p.bankroll, 95)
        self.assertNotIn(b, p.active_bets)
        self.assertEqual(game.point, 5)

    def test_proposition_bets_lose_on_nonwinning_totals(self):
        losing_rolls = {
            BetType.ANY_SEVEN: (4,4), BetType.ACE_DEUCE: (1,1),
            BetType.ACES: (1,2), BetType.BOXCARS: (5,6),
            BetType.YO_ELEVEN: (3,4), BetType.ANY_CRAPS: (3,4),
        }
        for bet_type, dice in losing_rolls.items():
            with self.subTest(bet=bet_type):
                player, engine = Player(), CrapsEngine()
                bet = player.place_wager(bet_type, 5)
                player.settle(engine.resolve_roll(dice, player.active_bets))
                self.assertEqual(player.bankroll, 95)
                self.assertNotIn(bet, player.active_bets)


if __name__ == "__main__":
    unittest.main()
