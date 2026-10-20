import unittest

from craps.engine.bets import Bet, BetOutcome, BetType
from craps.engine.dice import roll_dice
from craps.engine.game import CrapsEngine
from craps.engine.outcomes import RollOutcome
from craps.engine.player import Player


class CrapsFlowTests(unittest.TestCase):
    def setUp(self):
        self.game = CrapsEngine()
        self.bet = [Bet(BetType.PASS_LINE, 10)]

    def test_come_out_categories(self):
        for dice in ((3, 4), (5, 6)):
            self.assertEqual(self.game.resolve_roll(dice, self.bet).outcome, RollOutcome.WIN)
        for dice in ((1, 1), (1, 2), (6, 6)):
            self.assertEqual(self.game.resolve_roll(dice, self.bet).outcome, RollOutcome.LOSE)
        for dice, point in (((1, 3), 4), ((1, 4), 5), ((1, 5), 6),
                            ((2, 6), 8), ((3, 6), 9), ((4, 6), 10)):
            result = self.game.resolve_roll(dice, self.bet)
            self.assertEqual((result.outcome, result.point), (RollOutcome.POINT_ESTABLISHED, point))
            self.game.reset()

    def test_point_win_loss_and_continuation(self):
        self.game.resolve_roll((3, 3), self.bet)
        self.assertEqual(self.game.resolve_roll((1, 2), self.bet).outcome, RollOutcome.CONTINUE)
        self.assertEqual(self.game.resolve_roll((2, 4), self.bet).outcome, RollOutcome.WIN)
        self.assertIsNone(self.game.point)
        self.game.resolve_roll((3, 3), self.bet)
        self.assertEqual(self.game.resolve_roll((1, 6), self.bet).outcome, RollOutcome.LOSE)
        self.assertIsNone(self.game.point)

    def test_bankroll_settlement(self):
        player = Player()
        player.place_bet(10)
        result = self.game.resolve_roll((3, 4), player.active_bets)
        player.settle(result)
        self.assertEqual(player.bankroll, 110)
        self.assertIsNone(player.current_bet)
        player.place_bet(10)
        result = self.game.resolve_roll((1, 1), player.active_bets)
        player.settle(result)
        self.assertEqual(player.bankroll, 100)

    def test_invalid_roll_and_repeated_resolution_guard(self):
        for dice in ((0, 2), (1, 7), (1,), (1, 2, 3)):
            with self.assertRaises(ValueError):
                self.game.resolve_roll(dice, self.bet)

    def test_dice_range(self):
        for _ in range(1000):
            self.assertTrue(all(1 <= die <= 6 for die in roll_dice()))


if __name__ == "__main__":
    unittest.main()
