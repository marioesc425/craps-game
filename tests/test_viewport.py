import unittest

from craps.ui.viewport import design_position, viewport


class ViewportTransformTests(unittest.TestCase):
    def test_normal_resolution_has_identity_coordinates(self):
        scale, size, offset = viewport((1400, 700), (1400, 700))
        self.assertEqual((scale, size, offset), (1.0, (1400, 700), (0, 0)))
        self.assertEqual(design_position((1260, 616), (1400, 700), (1400, 700)), (1260, 616))

    def test_resized_window_uses_same_letterboxed_transform_for_clicks(self):
        scale, size, offset = viewport((1120, 560), (1400, 700))
        self.assertEqual((scale, size, offset), (0.8, (1120, 560), (0, 0)))
        self.assertEqual(design_position((1008, 493), (1120, 560), (1400, 700)), (1260, 616))

    def test_letterbox_offset_does_not_turn_bar_clicks_into_table_clicks(self):
        scale, size, offset = viewport((1200, 700), (1400, 700))
        self.assertAlmostEqual(scale, 6/7)
        self.assertEqual(offset, (0, 50))
        self.assertLess(design_position((400, 20), (1200, 700), (1400, 700))[1], 0)


if __name__ == "__main__":
    unittest.main()
