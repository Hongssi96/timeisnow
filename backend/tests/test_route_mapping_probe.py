import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from route_mapping_probe import match_route, direction_candidate, arrival_direction_matches


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




class DirectionProbeTests(unittest.TestCase):
    def fixture(self, board=1, alight=2):
        ids = ['10', '20', '30', '40', '10']
        rows = [{'stationSeq': i + 1, 'stationId': sid, 'turnSeq': 3,
                 'turnYn': 'Y' if i == 2 else 'N'} for i, sid in enumerate(ids)]
        info = {'routeId': '99', 'startStationId': '10', 'endStationId': '30', 'turnStID': '30'}
        match = {'route_id': '99', 'board_order': board, 'alight_order': alight,
                 'board_station_id': ids[board - 1], 'alight_station_id': ids[alight - 1]}
        return match, rows, info

    def test_outbound_and_return_have_distinct_destinations(self):
        self.assertEqual(direction_candidate(*self.fixture())['route_dest_id'], '30')
        self.assertEqual(direction_candidate(*self.fixture(4, 5))['route_dest_id'], '10')

    def test_crossing_or_boarding_turn_is_not_inferred(self):
        for board, alight in [(2, 4), (3, 4)]:
            self.assertEqual(direction_candidate(*self.fixture(board, alight))['status'], 'turnaround_unresolved')

    def test_inconsistent_turn_and_multiple_markers_are_rejected(self):
        for modify in [lambda r: r[0].update(turnSeq=2), lambda r: r[0].update(turnYn='Y'),
                       lambda r: r[2].update(turnYn='N')]:
            match, rows, info = self.fixture(); modify(rows)
            self.assertEqual(direction_candidate(match, rows, info)['status'], 'direction_unresolved')

    def test_gaps_duplicate_and_boolean_orders_are_rejected(self):
        for value in [4, 2, True, '1.0', 0]:
            match, rows, info = self.fixture(); rows[2]['stationSeq'] = value
            self.assertEqual(direction_candidate(match, rows, info)['status'], 'direction_unresolved')

    def test_endpoint_route_and_station_identity_conflicts_are_rejected(self):
        for key in ['routeId', 'startStationId', 'endStationId', 'turnStID']:
            match, rows, info = self.fixture(); info[key] = '999'
            self.assertEqual(direction_candidate(match, rows, info)['status'], 'direction_unresolved')
        match, rows, info = self.fixture(); match['board_station_id'] = '999'
        self.assertEqual(direction_candidate(match, rows, info)['status'], 'direction_unresolved')

    def test_missing_malformed_and_circular_route_are_unresolved(self):
        self.assertEqual(direction_candidate({}, [], {})['status'], 'direction_unresolved')
        for value in [None, '0', 'unknown', True]:
            match, rows, info = self.fixture(); info['turnStID'] = value
            self.assertEqual(direction_candidate(match, rows, info)['status'], 'direction_unresolved')
        match, rows, info = self.fixture(); info['endStationId'] = '10'
        self.assertEqual(direction_candidate(match, rows, info)['status'], 'direction_unresolved')

    def test_exact_unique_arrival_direction_is_required(self):
        match, rows, info = self.fixture(); direction = direction_candidate(match, rows, info)
        arrival = {'stationId': '10', 'routeId': '99', 'staOrder': 1, 'routeDestId': '30'}
        self.assertTrue(arrival_direction_matches(match, direction, [arrival]))
        for key in arrival:
            self.assertFalse(arrival_direction_matches(match, direction, [dict(arrival, **{key: '999'})]))
        self.assertFalse(arrival_direction_matches(match, direction, [arrival, arrival]))
        self.assertFalse(arrival_direction_matches(match, direction, []))
        self.assertFalse(arrival_direction_matches(match, {'status': 'direction_unresolved'}, [arrival]))


if __name__ == '__main__':
    unittest.main()
