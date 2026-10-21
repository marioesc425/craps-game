import unittest

from craps.engine.bets import BetType
from craps.engine.game import CrapsEngine
from craps.engine.player import InvalidBetError, Player
from craps.ui.betting import (ZONES, place_chip, stack_at, stack_center, zone_at,
                              WagerAccumulator, wager_available)


class TableHitTestingTests(unittest.TestCase):
    def test_each_drawn_zone_maps_to_its_wager(self):
        samples = {
            "pass_line": (700,540), "dont_pass_side": (145,230),
            "dont_pass_bottom": (600,470), "come": (500,280),
            "dont_come": (230,190), "field": (790,350),
            "place_4": (340,150), "place_5": (450,150), "place_6": (550,150),
            "place_8": (650,150), "place_9": (760,150), "place_10": (860,150),
            "hard_6": (1060,300), "hard_10": (1260,300),
            "hard_8": (1060,380), "hard_4": (1260,380),
            "ace_deuce": (1060,459), "aces": (1260,459), "boxcars": (1060,537),
            "yo_eleven": (1260,537), "any_seven": (1060,616),
            "any_craps": (1260,616),
        }
        for name, point in samples.items():
            with self.subTest(zone=name):
                self.assertEqual(zone_at(point).name, name)
        self.assertIsNone(zone_at((950, 600)))
        self.assertEqual(len(ZONES), 22)

    def test_each_side_bet_zone_center_and_inner_edges_maps_only_to_itself(self):
        from craps.ui.board import PROP_CELLS, _box
        names = ["hard_6", "hard_10", "hard_8", "hard_4", "ace_deuce", "aces",
                 "boxcars", "any_seven", "yo_eleven", "any_craps"]
        for name in names:
            rect = _box(*PROP_CELLS[name])
            for point in (rect.center, (rect.left + 2, rect.top + 2),
                          (rect.right - 2, rect.bottom - 2)):
                with self.subTest(zone=name, point=point):
                    self.assertEqual(zone_at(point).name, name)
        outer_left = _box(*PROP_CELLS["hard_6"]).left
        self.assertIsNone(zone_at((outer_left - 2, rect.centery)))

    def test_every_printed_bottom_bet_places_and_settles_to_its_labeled_rule(self):
        cases = {
            "hard_6": ((3,3), 9), "hard_10": ((5,5), 7),
            "hard_8": ((4,4), 9), "hard_4": ((2,2), 7),
            "ace_deuce": ((1,2), 15), "aces": ((1,1), 30),
            "boxcars": ((6,6), 30), "any_seven": ((3,4), 4),
            "yo_eleven": ((5,6), 15), "any_craps": ((1,2), 7),
        }
        for name, (winning_roll, net_payout) in cases.items():
            with self.subTest(zone=name):
                player, engine = Player(), CrapsEngine()
                engine.resolve_roll((3,3), [])  # Establish point 6 for Place/Hardway play.
                zone = next(zone for zone in ZONES if zone.name == name)
                builder = WagerAccumulator()
                bet, kind, amount = builder.add_chip(player, engine, zone, 5)
                self.assertEqual((bet.amount, kind, player.bankroll), (5, "new", 95))
                self.assertEqual(amount, 5)
                self.assertTrue(zone.contains(stack_center(bet)))
                self.assertIs(stack_at(stack_center(bet), player.active_bets), bet)
                result = engine.resolve_roll(winning_roll, player.active_bets)
                player.settle(result)
                self.assertEqual(player.bankroll, 100 + 5 * net_payout)
                self.assertFalse(player.active_bets)

    def test_one_dollar_pass_line_wager_places_and_undo_refunds_exactly(self):
        player, engine, builder = Player(), CrapsEngine(), WagerAccumulator()
        zone = zone_at((700,540))
        bet, action, amount = builder.add_chip(player, engine, zone, 1)
        self.assertEqual((bet.amount, action, amount, player.bankroll), (1, "new", 1, 99))
        player.undo_wager(bet)
        self.assertEqual(player.bankroll, 100)
        bet, action, amount = builder.add_chip(player, engine, zone, 1)
        self.assertEqual((bet.amount, action, amount, player.bankroll), (1, "new", 1, 99))
        self.assertFalse(builder.pending)

    def test_one_dollar_wagers_are_accepted_for_each_compatible_bet_type(self):
        cases = [
            ("pass_line", BetType.PASS_LINE, None, None),
            ("dont_pass_side", BetType.DONT_PASS, None, None),
            ("field", BetType.FIELD, None, None),
            ("come", BetType.COME, None, 6),
            ("dont_come", BetType.DONT_COME, None, 6),
            ("hard_4", BetType.HARDWAY, 4, 6),
            ("hard_6", BetType.HARDWAY, 6, 6),
            ("hard_8", BetType.HARDWAY, 8, 6),
            ("hard_10", BetType.HARDWAY, 10, 6),
            ("any_seven", BetType.ANY_SEVEN, None, None),
            ("ace_deuce", BetType.ACE_DEUCE, None, None),
            ("aces", BetType.ACES, None, None),
            ("boxcars", BetType.BOXCARS, None, None),
            ("yo_eleven", BetType.YO_ELEVEN, None, None),
            ("any_craps", BetType.ANY_CRAPS, None, None),
        ]
        for name, bet_type, number, point in cases:
            with self.subTest(zone=name):
                player, engine = Player(), CrapsEngine()
                if point is not None:
                    engine.resolve_roll((3, 3), [])
                zone = next(z for z in ZONES if z.name == name)
                bet, action = place_chip(player, engine, zone, 1)
                self.assertEqual((bet.bet_type, bet.number, bet.amount, action, player.bankroll),
                                 (bet_type, number, 1, "new", 99))

    def test_one_dollar_place_increment_is_enforced_by_its_paytable(self):
        player = Player()
        for number in (4, 5, 6, 8, 9, 10):
            with self.subTest(number=number), self.assertRaises(InvalidBetError):
                player.place_wager(BetType.PLACE, 1, number)
        for number, amount in ((4, 5), (5, 5), (6, 6), (8, 6), (9, 5), (10, 5)):
            bet = player.place_wager(BetType.PLACE, amount, number)
            self.assertEqual(bet.amount, amount)
            player.undo_wager(bet)

    def test_payout_safe_accumulation_for_place_six_and_minimum_feedback(self):
        player, engine, builder = Player(), CrapsEngine(), WagerAccumulator()
        zone = zone_at((550,150))
        self.assertTrue(wager_available(player, engine, zone, 5))
        _, action, amount = builder.add_chip(player, engine, zone, 5)
        self.assertEqual((action, amount, builder.amount_to_complete(player, zone)),
                         ("pending", 5, 1))
        bet, action, amount = builder.add_chip(player, engine, zone, 1)
        self.assertEqual((bet.amount, action, amount, player.bankroll), (6, "new", 6, 94))

    def test_accumulated_chips_cannot_cross_maximum_or_exceed_bankroll(self):
        from dataclasses import replace
        from craps.engine.config import DEFAULT_TABLE_RULES
        rules = replace(DEFAULT_TABLE_RULES, starting_bankroll=1000)
        player, engine, builder = Player(rules=rules), CrapsEngine(rules=rules), WagerAccumulator()
        zone = zone_at((700,540))
        bet, _ = place_chip(player, engine, zone, 499)
        builder.add_chip(player, engine, zone, 1)
        self.assertEqual((bet.amount, player.bankroll), (500, 500))
        with self.assertRaises(InvalidBetError):
            builder.add_chip(player, engine, zone, 1)
        self.assertEqual((bet.amount, player.bankroll, builder.amount_for(zone)), (500, 500, 0))

    def test_click_places_once_and_uses_selected_chip_amount(self):
        player, engine = Player(), CrapsEngine()
        zone = zone_at((550,150))  # Place 6
        bet, action = place_chip(player, engine, zone, 6)
        self.assertEqual((bet.bet_type, bet.number, bet.amount), (BetType.PLACE, 6, 6))
        self.assertEqual(action, "new")
        self.assertEqual(player.bankroll, 94)

    def test_chip_values_match_five_standard_denominations(self):
        from craps.engine.config import DEFAULT_TABLE_RULES
        rules = DEFAULT_TABLE_RULES
        self.assertEqual(rules.chip_denominations, (1, 5, 25, 100, 500))
        player = Player(rules=__import__('dataclasses').replace(rules, starting_bankroll=1500))
        engine = CrapsEngine(rules=player.rules)
        builder = WagerAccumulator()
        zone = zone_at((550,150))
        builder.add_chip(player, engine, zone, 5)
        bet, action, _ = builder.add_chip(player, engine, zone, 1)
        self.assertEqual(action, "new")
        self.assertEqual((bet.amount, player.bankroll), (6, 1494))

    def test_zone_maximum_and_chip_affordability_are_enforced(self):
        from dataclasses import replace
        from craps.engine.config import DEFAULT_TABLE_RULES
        rules = replace(DEFAULT_TABLE_RULES, starting_bankroll=1000)
        player, engine = Player(rules=rules), CrapsEngine(rules=rules)
        zone = zone_at((700,540))
        wager, _ = place_chip(player, engine, zone, 500)
        self.assertFalse(__import__('craps.ui.betting', fromlist=['wager_available']).wager_available(player, engine, zone, 1))
        with self.assertRaises(InvalidBetError):
            place_chip(player, engine, zone, 1)
        self.assertEqual((wager.amount, player.bankroll), (500, 500))

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
            place_chip(player, engine, zone_at((340,150)), 1)  # fractional Place 4 payout
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

    def test_traveled_come_bets_move_to_their_number_on_table(self):
        from craps.ui.board import PLACE_RECTS
        for bet_type, zone_name, expected_side in (
                (BetType.COME, "come", "left"),
                (BetType.DONT_COME, "dont_come", "right")):
            with self.subTest(bet_type=bet_type):
                player, engine = Player(), CrapsEngine()
                engine.resolve_roll((2, 2), [])  # Point 4; Come bets are now available.
                zone = next(zone for zone in ZONES if zone.name == zone_name)
                bet, action = place_chip(player, engine, zone, 5)
                self.assertEqual((bet.number, action), (None, "new"))
                self.assertTrue(zone.contains(stack_center(bet)))

                result = engine.resolve_roll((3, 3), player.active_bets)  # Travel to 6.
                player.settle(result)
                rect = PLACE_RECTS[6]
                expected_x = rect.left + 22 if expected_side == "left" else rect.right - 22
                self.assertEqual(bet.number, 6)
                self.assertEqual(stack_center(bet), (expected_x, rect.centery - 36))
                self.assertFalse(zone.contains(stack_center(bet)))
                self.assertIs(stack_at(stack_center(bet), player.active_bets), bet)

    def test_multiple_come_bets_on_the_same_number_keep_separate_click_targets(self):
        player, engine = Player(), CrapsEngine()
        engine.resolve_roll((2, 2), [])
        zone = next(zone for zone in ZONES if zone.name == "come")
        first, _ = place_chip(player, engine, zone, 5)
        second, _ = place_chip(player, engine, zone, 5)
        engine.resolve_roll((3, 3), player.active_bets)

        first_center = stack_center(first, 0)
        second_center = stack_center(second, 1)
        self.assertNotEqual(first_center, second_center)
        self.assertIs(stack_at(first_center, player.active_bets), first)
        self.assertIs(stack_at(second_center, player.active_bets), second)


if __name__ == "__main__":
    unittest.main()
