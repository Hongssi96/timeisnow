import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from provider_freshness import assess_source_age


class FreshnessTests(unittest.TestCase):
    received = datetime(2026, 10, 6, 0, 1, 0, tzinfo=timezone.utc)

    def test_exact_expiry_boundary_and_over_limit(self):
        self.assertEqual(assess_source_age('2026-10-06T00:00:00+00:00', self.received, 60)['status'], 'fresh')
        self.assertEqual(assess_source_age('2026-10-05T23:59:59+00:00', self.received, 60)['status'], 'stale')

    def test_missing_time_is_not_zero_age(self):
        result = assess_source_age(None, self.received, 60)
        self.assertEqual(result['status'], 'unknown')
        self.assertIsNone(result['age_seconds'])

    def test_future_time_is_not_fresh(self):
        self.assertEqual(assess_source_age('2026-10-06T00:02:00Z', self.received, 60)['status'], 'clock_mismatch')

    def test_naive_time_requires_explicit_source_zone(self):
        self.assertEqual(assess_source_age('2026-10-06 09:00:00', self.received, 60)['status'], 'unknown')
        result = assess_source_age('2026-10-06 09:00:00', self.received, 60, timezone(timedelta(hours=9)))
        self.assertEqual(result['age_seconds'], 60)

    def test_invalid_source_timestamp(self):
        self.assertEqual(assess_source_age('not-a-date', self.received, 60)['status'], 'unknown')

    def test_invalid_age_policy_is_rejected(self):
        for value in (True, 0, -1, float('nan'), float('inf'), None):
            with self.assertRaises(ValueError):
                assess_source_age('2026-10-06T00:00:00Z', self.received, value)


if __name__ == '__main__':
    unittest.main()
