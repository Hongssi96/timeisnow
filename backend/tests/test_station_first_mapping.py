import contextlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_gyeonggi_mapping as cli
from route_mapping_probe import boarding_candidates, station_route_scopes, scoped_matches


class StationScopeTests(unittest.TestCase):
    def station(self, sid='10', **overrides):
        return dict({'stationId': sid, 'stationName': '출발', 'x': 127.1, 'y': 37.4}, **overrides)

    def test_all_nearby_stops_are_kept_and_far_names_excluded(self):
        result = boarding_candidates('출발', [127.1, 37.4],
            [self.station(), self.station('11', x=127.1001), self.station('12', x=128)], 100)
        self.assertEqual(result['station_ids'], ['10', '11'])

    def test_missing_coordinate_and_conflicting_duplicates_are_not_silently_dropped(self):
        for rows in [[self.station(x=None)], [self.station(), self.station(x=128)], [None]]:
            self.assertEqual(boarding_candidates('출발', [127.1,37.4], rows, 100)['status'], 'station_unresolved')

    def test_station_limit_missing_name_and_no_match_stop_selection(self):
        for name, rows in [('출발', [self.station(str(i)) for i in range(1,4)]),
                           ('다른', [self.station()]), ('', [self.station()])]:
            self.assertEqual(boarding_candidates(name, [127.1,37.4], rows, 100)['station_ids'], [])

    def test_scope_deduplicates_exact_rows_but_preserves_repeat_visits(self):
        row = {'routeId': '99', 'routeName': '76', 'staOrder': 1, 'routeDestId': '30'}
        result = station_route_scopes('76', [('10', [row, row, dict(row, staOrder=5, routeDestId='10'),
                                                         dict(row, routeName='760')])])
        self.assertEqual(len(result), 2)
        self.assertEqual({s['board_order'] for s in result}, {1,5})

    def test_conflicting_or_malformed_direction_cannot_be_a_scope(self):
        row = {'routeId': '99', 'routeName': '76', 'staOrder': 1, 'routeDestId': '30'}
        for rows in [[row, dict(row, routeDestId='40')], [dict(row, staOrder=True)],
                     [dict(row, routeDestId=None)], [dict(row, staOrder=1001)]]:
            with self.assertRaises(ValueError): station_route_scopes('76', [('10', rows)])

    def test_scope_requires_exact_board_stop_route_and_order(self):
        scope = {'board_station_id':'10', 'route_id':'99', 'board_order':1, 'route_dest_id':'30'}
        match = {k:v for k,v in scope.items() if k!='route_dest_id'}
        self.assertEqual(scoped_matches({'matches':[match]}, [scope])['status'], 'candidate_unique')
        for key, value in [('board_station_id','11'), ('route_id','100'), ('board_order',5)]:
            self.assertEqual(scoped_matches({'matches':[dict(match, **{key:value})]}, [scope])['status'], 'no_match')


class StationFirstCliTests(unittest.TestCase):
    def execute(self, route_count=1, station_failure=False, empty=False, budget=10, info_missing=False, return_id="10"):
        stages=[]
        def wrapped(field, rows, code=0):
            return {'response':{'msgHeader':{'resultCode':code, 'queryTime':'request-time'}, 'msgBody':{field:rows}}}
        def fake(url, stage, headers=None):
            stages.append(stage)
            if stage=='kakao_route':
                return {'status':'OK','routes':[{'properties':{'type':'BUS','transfers':0}, 'steps':[
                    {'properties':{'type':'BUS', 'vehicles':[{'name':'76'}], 'stops':[{'name':'출발'},{'name':'도착'}]},
                     'path':{'points':[[127.1,37.4],[127.11,37.41]]}}]}]}
            if stage=='getBusStationListv2':
                if station_failure: raise cli.ProbeError(stage,403)
                return wrapped('busStationList', [] if empty else [
                    {'stationId':'10','stationName':'출발','x':127.1,'y':37.4}], 4 if empty else 0)
            if stage=='getBusStationViaRouteListv2':
                return wrapped('busRouteList',[{'routeId':str(99+i),'routeName':'76','staOrder':1,'routeDestId':'30'}
                                              for i in range(route_count)])
            if stage=='getBusRouteStationListv2':
                from urllib.parse import urlsplit, parse_qs
                rid=parse_qs(urlsplit(url).query)['routeId'][0]
                names=['출발' if rid=='99' else '다른','도착','회차','복귀','출발']
                rows=[{'stationId':sid,'stationSeq':i+1,'stationName':name,'turnSeq':3,
                       'turnYn':'Y' if i==2 else 'N','x':127.11 if i==1 else 127.1,'y':37.41 if i==1 else 37.4}
                      for i,(sid,name) in enumerate(zip(['10','20','30','40',return_id],names))]
                return wrapped('busRouteStationList', rows)
            if stage=='getBusRouteInfoItemv2':
                return wrapped('busRouteInfoItem',{} if info_missing else {'routeId':'99','startStationId':'10','endStationId':'30','turnStID':'30'})
            if stage=='getBusArrivalItemv2':
                return wrapped('busArrivalItem',{'stationId':'10','routeId':'99','staOrder':1,'routeDestId':'30'})
            raise AssertionError(stage)
        output=io.StringIO()
        with patch.object(cli,'dotenv_values',return_value={'KAKAO_REST_API_KEY':'private-kakao','DATA_GO_KR_SERVICE_KEY':'private-public'}), \
             patch.object(cli,'fetch',side_effect=fake), contextlib.redirect_stdout(output):
            code=cli.main(budget)
        self.assertNotIn('private-',output.getvalue())
        self.assertNotIn('routeDestId',output.getvalue())
        return code,json.loads(output.getvalue()),stages

    def test_station_scoped_route_succeeds_without_global_name_search(self):
        code,result,stages=self.execute()
        self.assertEqual(code,0)
        self.assertEqual(result['request_count'],6)
        self.assertTrue(result['arrival_direction_matches'])
        self.assertFalse(result['valid_for_guidance'])
        self.assertFalse(result['verified_generation_time_available'])
        self.assertNotIn('getBusRouteListv2',stages)

    def test_different_return_endpoint_uses_scoped_direction_and_stays_unfit_for_guidance(self):
        code,result,stages=self.execute(return_id='50')
        self.assertEqual(code,0)
        self.assertTrue(result['arrival_direction_matches'])
        self.assertEqual(result['direction_basis'],'station_route_scope')
        self.assertFalse(result['return_endpoint_matches_start'])
        self.assertFalse(result['valid_for_guidance'])
        self.assertFalse(result['production_mapping_validated'])

    def test_unresolved_direction_reason_is_preserved_without_claiming_conflict(self):
        code,result,stages=self.execute(info_missing=True)
        self.assertEqual(code,1)
        self.assertEqual(result['direction_reason'],'DIRECTION_FIELDS_UNCONFIRMED')
        self.assertFalse(result['arrival_direction_matches'])

    def test_ten_request_budget_includes_info_and_arrival(self):
        code,result,stages=self.execute(route_count=5)
        self.assertEqual(code,0)
        self.assertEqual(len(stages),10)
        self.assertEqual(result['request_count'],10)

    def test_all_candidates_exceeding_budget_are_rejected_before_partial_sampling(self):
        code,result,stages=self.execute(route_count=6)
        self.assertEqual(code,1)
        self.assertEqual(result['candidate_count'],6)
        self.assertEqual(len(stages),3)
        self.assertNotIn('getBusRouteStationListv2',stages)

    def test_remaining_eight_requests_reject_four_routes_and_allow_three(self):
        code,result,stages=self.execute(route_count=4,budget=8)
        self.assertEqual((code,len(stages)),(1,3))
        code,result,stages=self.execute(route_count=3,budget=8)
        self.assertEqual((code,len(stages),result['request_count']),(0,8,8))

    def test_invalid_budget_is_rejected_before_key_read_or_network(self):
        with patch.object(cli,'fetch') as fetch, patch.object(cli,'dotenv_values') as settings:
            for budget in [0,11,True,None]:
                with self.assertRaises(ValueError): cli.main(budget)
            fetch.assert_not_called(); settings.assert_not_called()

    def test_station_permission_failure_does_not_fallback_or_leak(self):
        code,result,stages=self.execute(station_failure=True)
        self.assertEqual((code,result['http_status'],len(stages)),(1,403,2))
        self.assertEqual(result['stage'],'getBusStationListv2')

    def test_normal_empty_station_search_stops_before_via_calls(self):
        code,result,stages=self.execute(empty=True)
        self.assertEqual((code,result['status'],len(stages)),(1,'station_disambiguation_required',2))


if __name__=='__main__': unittest.main()
