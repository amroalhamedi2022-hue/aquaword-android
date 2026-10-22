"""Prevent falsely reporting Android UI success from black/off-screen captures."""
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "quality"))
from check_screen import verify


class DisplayEvidenceTests(unittest.TestCase):
    def test_black_screen_fails(self):
        with TemporaryDirectory() as folder:
            p=Path(folder)/"blank.png"
            Image.new("RGB",(1080,2340),(0,0,0)).save(p)
            with self.assertRaisesRegex(ValueError,"Black/blank"):
                verify(p)

    def test_visible_phone_passes(self):
        with TemporaryDirectory() as folder:
            p=Path(folder)/"phone.png"
            im=Image.new("RGB",(1080,2340),(250,252,255))
            draw=ImageDraw.Draw(im)
            draw.rectangle((0,300,1080,600),fill=(0,100,145))
            im.save(p)
            self.assertEqual(verify(p),(1080,2340))

    def test_real_tablet_ratio_required(self):
        with TemporaryDirectory() as folder:
            p=Path(folder)/"tablet.png"
            im=Image.new("RGB",(2560,1600),"white")
            ImageDraw.Draw(im).rectangle((80,80,2480,480),fill=(20,130,165))
            im.save(p)
            self.assertEqual(verify(p,1.6),(2560,1600))
            with self.assertRaisesRegex(ValueError,"Wrong orientation"):
                verify(p,0.625)


if __name__=="__main__":
    unittest.main()
