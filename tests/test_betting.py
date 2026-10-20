import unittest

from craps.engine.bets import BetType
from craps.engine.game import CrapsEngine
from craps.engine.player import InvalidBetError, Player
from craps.ui.betting import ZONES, place_chip, stack_at, stack_center, zone_at


class TableHitTestingTests(unittest.TestCase):
    def test_each_drawn_zone_maps_to_its_wager(self):
        samples = {
            "pass_line": (700,540), "dont_pass_side": (145,230),
            "dont_pass_bottom": (600,470), "come": (500,280),
            "dont_come": (230,190), "field": (790,350),
            "place_4": (340,150), "place_5": (450,150), "place_6": (550,150),
            "place_8": (650,150), "place_9": (760,150), "place_10": (860,150),
            "hard_6": (1060,340), "hard_10": (1260,340),
            "hard_8": (1060,418), "hard_4": (1260,418),
        }
        for name, point in samples.items():
            with self.subTest(zone=name):
                self.assertEqual(zone_at(point).name, name)
        self.assertIsNone(zone_at((950, 600)))
        self.assertEqual(len(ZONES), 16)

    def test_click_places_once_and_uses_selected_chip_amount(self):
        player, engine = Player(), CrapsEngine()
        zone = zone_at((550,150))  # Place 6
        bet, action = place_chip(player, engine, zone, 6)
        self.assertEqual((bet.bet_type, bet.number, bet.amount), (BetType.PLACE, 6, 6))
        self.assertEqual(action, "new")
        self.assertEqual(player.bankroll, 94)

    def test_repeated_click_increases_same_area_and_stack_is_wager_backed(self):
        player, engine = Player(), CrapsEngine()
        zone = zone_at((550,150))
        bet, _ = place_chip(player, engine, zone, 6)
        same, action = place_chip(player, engine, zone, 6)
        self.assertIs(same, bet)
        self.assertEqual((action, bet.amount, player.bankroll), ("increase", 12, 88))
        self.assertIs(stack_at(stack_center(bet), player.active_bets), bet)

    def test_phase_and_invalid_chip_rejections_do_not_charge_bankroll(self):
        player, engine = Player(), CrapsEngine()
        bankroll = player.bankroll
        with self.assertRaises(InvalidBetError):
            place_chip(player, engine, zone_at((500,280)), 5)  # Come before point
        with self.assertRaises(InvalidBetError):
            place_chip(player, engine, zone_at((340,150)), 1)  # sub-minimum and fractional Place 4
        with self.assertRaises(InvalidBetError):
            place_chip(player, engine, zone_at((700,540)), 500)
        self.assertEqual(player.bankroll, bankroll)
        engine.resolve_roll((2,2), [])
        with self.assertRaises(InvalidBetError):
            place_chip(player, engine, zone_at((700,540)), 5)  # Pass Line after point
        self.assertEqual(player.bankroll, bankroll)

    def test_click_outside_does_not_place_and_undo_refunds_exact_stake(self):
        player, engine = Player(), CrapsEngine()
        self.assertIsNone(zone_at((950, 600)))
        self.assertFalse(player.active_bets)
        bet, action = place_chip(player, engine, zone_at((700, 540)), 5)
        self.assertEqual((action, player.bankroll), ("new", 95))
        player.increase_wager(bet, 5)
        self.assertEqual((bet.amount, player.bankroll), (10, 90))
        player.reduce_wager(bet, 5)
        self.assertEqual((bet.amount, player.bankroll), (5, 95))
        player.undo_wager(bet)
        self.assertEqual((player.active_bets, player.bankroll), ([], 100))

    def test_contextual_odds_undo_refunds_odds_only(self):
        player, engine = Player(), CrapsEngine()
        bet, _ = place_chip(player, engine, zone_at((700, 540)), 5)
        engine.resolve_roll((3, 3), player.active_bets)
        player.add_odds(bet, 5, engine.point)
        self.assertEqual((bet.amount, bet.odds, player.bankroll), (5, 5, 90))
        player.reduce_odds(bet, 5)
        self.assertEqual((bet.amount, bet.odds, player.bankroll), (5, 0, 95))

    def test_odds_attach_to_the_clicked_underlying_bet(self):
        from craps.ui.betting import odds_eligible
        player, engine = Player(), CrapsEngine()
        bet, _ = place_chip(player, engine, zone_at((700,540)), 5)
        engine.resolve_roll((3,3), player.active_bets)
        self.assertTrue(odds_eligible(bet, engine.point))
        self.assertIs(stack_at(stack_center(bet), player.active_bets), bet)
        player.add_odds(bet, 5, engine.point)
        result = engine.resolve_roll((3,3), player.active_bets)
        player.settle(result)
        self.assertEqual(player.bankroll, 111)
        self.assertFalse(player.active_bets)


if __name__ == "__main__":
    unittest.main()
