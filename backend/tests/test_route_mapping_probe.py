import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from route_mapping_probe import match_route


class RouteMappingTests(unittest.TestCase):
    points = [[127.1, 37.4], [127.11, 37.41]]
    stops = [{'name': '출발역'}, {'name': '중간'}, {'name': '도착역'}]

    def rows(self):
        return [{'stationId': 'a', 'stationSeq': 1, 'stationName': '출발역', 'x': 127.1, 'y': 37.4},
                {'stationId': 'b', 'stationSeq': 2, 'stationName': '중간', 'x': 127.105, 'y': 37.405},
                {'stationId': 'c', 'stationSeq': 3, 'stationName': '도착역', 'x': 127.11, 'y': 37.41}]

    def test_names_sequence_and_coordinates_make_one_candidate(self):
        result = match_route(self.stops, self.points, [('route', self.rows())], 100)
        self.assertEqual(result['status'], 'candidate_unique')
        self.assertEqual(result['matches'][0]['board_order'], 1)

    def test_reverse_direction_is_rejected(self):
        rows = self.rows()
        rows[0]['stationSeq'], rows[2]['stationSeq'] = 3, 1
        self.assertEqual(match_route(self.stops, self.points, [('route', rows)], 100)['status'], 'no_match')

    def test_far_same_name_stop_is_rejected(self):
        rows = self.rows()
        rows[0]['x'] = 128
        self.assertEqual(match_route(self.stops, self.points, [('route', rows)], 100)['status'], 'no_match')

    def test_multiple_routes_are_not_silently_selected(self):
        result = match_route(self.stops, self.points, [('one', self.rows()), ('two', self.rows())], 100)
        self.assertEqual(result['status'], 'ambiguous')
        self.assertEqual(len(result['matches']), 2)

    def test_repeated_station_visit_keeps_both_orders(self):
        rows = self.rows()
        repeated = dict(rows[0], stationSeq=0)
        result = match_route(self.stops, self.points, [('route', [repeated] + rows)], 100)
        self.assertEqual(result['status'], 'ambiguous')

    def test_missing_coordinate_or_intermediate_stop_rejects_candidate(self):
        rows = self.rows()
        rows[0]['x'] = None
        self.assertEqual(match_route(self.stops, self.points, [('route', rows)], 100)['status'], 'no_match')
        self.assertEqual(match_route(self.stops, self.points, [('route', [self.rows()[0], self.rows()[2]])], 100)['status'], 'no_match')

    def test_duplicate_order_is_rejected(self):
        rows = self.rows()
        rows[1]['stationSeq'] = 1
        self.assertEqual(match_route(self.stops, self.points, [('route', rows)], 100)['status'], 'no_match')


if __name__ == '__main__':
    unittest.main()
