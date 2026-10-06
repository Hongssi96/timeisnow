import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_seoul_mapping import candidates


class CandidateTests(unittest.TestCase):
    def row(self, name='역', x='127', ars='001'):
        return {'stId': '1', 'stNm': name, 'tmX': x, 'tmY': '37', 'arsId': ars}

    def test_exact_name_and_coordinate_required(self):
        self.assertEqual(len(candidates([self.row()], '역', [127, 37])), 1)
        self.assertEqual(candidates([self.row(name='역(7번승강장)')], '역', [127, 37]), [])
        self.assertEqual(candidates([self.row(x='128')], '역', [127, 37]), [])

    def test_invalid_ars_and_coordinates_excluded(self):
        self.assertEqual(candidates([self.row(ars='00000')], '역', [127, 37]), [])
        self.assertEqual(candidates([self.row(x='nan')], '역', [127, 37]), [])

    def test_duplicate_identity_deduplicated(self):
        self.assertEqual(len(candidates([self.row(), self.row()], '역', [127, 37])), 1)
