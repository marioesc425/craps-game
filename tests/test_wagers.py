import unittest

from craps.engine.bets import Bet, BetOutcome, BetType
from craps.engine.game import CrapsEngine
from craps.engine.player import Player, InvalidBetError
from craps.engine.settlement import settle_bet


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
        for dice in ((1,4),(2,4),(1,6),(2,6),(6,6)):
            self.assertEqual(settle_bet(Bet(BetType.FIELD, 5), dice, None).outcome, BetOutcome.LOSE)

    def test_configurable_field_and_twelve_rule(self):
        self.assertEqual(settle_bet(Bet(BetType.FIELD, 5), (1,1), None, 3).amount, 20)
        self.assertEqual(settle_bet(Bet(BetType.DONT_PASS, 5), (6,6), None, dont_pass_12_push=False).outcome,
                         BetOutcome.LOSE)

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


if __name__ == "__main__":
    unittest.main()
