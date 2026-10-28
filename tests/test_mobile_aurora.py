"""Static mobile Liquid Aurora accessibility contract; not an Android UI test."""
from pathlib import Path
import unittest

CSS = (Path(__file__).resolve().parents[1] /
       "branding/mobilewizard.aurora.css").read_text(encoding="utf-8")


def luminance(color):
    rgb = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4
              for v in rgb]
    return sum(a * b for a, b in zip(linear, (.2126, .7152, .0722)))


def contrast(a, b):
    x, y = luminance(a), luminance(b)
    return (max(x, y) + .05) / (min(x, y) + .05)


class MobileAuroraContract(unittest.TestCase):
    def test_readable_light_and_dark_headers(self):
        # Test both endpoints of each gradient, not just the easy endpoint.
        for ink, stops in (
            ("#16384d", ("#e9f8fc", "#d7f4f5")),
            ("#eafaff", ("#09273d", "#144459")),
        ):
            self.assertIn("color: " + ink + ";", CSS)
            for background in stops:
                self.assertIn(background, CSS)
                self.assertGreaterEqual(contrast(ink, background), 4.5)

    def test_mobile_controls_are_accessible_without_changing_document_canvas(self):
        self.assertIn("min-width: 44px;", CSS)
        self.assertIn("min-height: 44px;", CSS)
        self.assertIn("touch-action: manipulation;", CSS)
        self.assertIn("button:focus-visible", CSS)
        self.assertIn("prefers-reduced-motion: reduce", CSS)
        self.assertIn("transition: none;", CSS)
        self.assertIn("html[data-theme='dark']", CSS)
        self.assertNotIn("#map", CSS)
        self.assertNotIn("#document-container", CSS)


if __name__ == "__main__":
    unittest.main()
