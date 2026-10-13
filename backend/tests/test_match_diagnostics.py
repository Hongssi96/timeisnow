import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.arrivals.matching import diagnose_match

class MatchDiagnosticTests(unittest.TestCase):
    def fixture(self):
        stops=[{'name':'PRIVATE_START'},{'name':'PRIVATE_MID'},{'name':'PRIVATE_END'}]
        points=[[127.1,37.4],[127.11,37.41]]
        rows=[{'stationName':s['name'],'stationSeq':i+1,'stationId':str(101+i),
               'x':points[0 if i<2 else 1][0],'y':points[0 if i<2 else 1][1]} for i,s in enumerate(stops)]
        scopes=[{'route_id':'99','board_station_id':'101','board_order':1,'route_dest_id':'103'}]
        return stops,points,[('99',rows)],scopes

    def test_noncontiguous_stops_are_distinct_from_missing_order(self):
        stops,points,routes,scopes=self.fixture()
        rows=routes[0][1];rows.insert(1,dict(rows[0],stationId='200',stationName='EXTRA'))
        for i,row in enumerate(rows):row['stationSeq']=i+1
        result=diagnose_match(stops,points,routes,scopes)
        self.assertEqual(result['detail_reason'],'STOPS_NOT_CONTIGUOUS')
        self.assertEqual(result['scoped_ordered_name_pairs'],1)
        rows[2]['stationName']='DIFFERENT'
        self.assertEqual(diagnose_match(stops,points,routes,scopes)['detail_reason'],'INTERMEDIATE_ORDER_UNMATCHED')

    def test_coordinate_limit_and_missing_coordinate_are_separate(self):
        stops,points,routes,scopes=self.fixture();routes[0][1][0]['x']+=0.0004
        self.assertEqual(diagnose_match(stops,points,routes,scopes)['detail_reason'],'COORDINATE_LIMIT_EXCEEDED')
        routes[0][1][0]['x']=None
        self.assertEqual(diagnose_match(stops,points,routes,scopes)['detail_reason'],'COORDINATES_UNCONFIRMED')

    def test_scope_order_and_station_route_conflicts_are_detected(self):
        for key,value in [('board_order',2),('board_station_id','999'),('route_id','999')]:
            stops,points,routes,scopes=self.fixture();scopes[0][key]=value
            self.assertEqual(diagnose_match(stops,points,routes,scopes)['detail_reason'],'VISIT_SCOPE_UNMATCHED')

    def test_endpoint_names_and_duplicate_sequences_are_separate(self):
        stops,points,routes,scopes=self.fixture();routes[0][1][0]['stationName']='DIFFERENT'
        self.assertEqual(diagnose_match(stops,points,routes,scopes)['detail_reason'],'ENDPOINT_NAMES_UNMATCHED')
        routes[0][1][1]['stationSeq']=1
        self.assertEqual(diagnose_match(stops,points,routes,scopes)['detail_reason'],'SEQUENCE_DATA_UNCONFIRMED')
        routes[0][1].clear()
        self.assertEqual(diagnose_match(stops,points,routes,scopes)['detail_reason'],'SEQUENCE_DATA_UNCONFIRMED')

    def test_only_counts_and_fixed_reason_are_returned(self):
        result=diagnose_match(*self.fixture())
        self.assertEqual(result['detail_reason'],'MATCH_CHECKS_PASSED')
        self.assertNotIn('PRIVATE',str(result));self.assertNotIn('127.1',str(result));self.assertNotIn('101',str(result))
        self.assertTrue(all(type(v) is int for k,v in result.items() if k!='detail_reason'))

    def test_size_guard_avoids_diagnostic_work_without_changing_mapping(self):
        stops,points,routes,scopes=self.fixture()
        self.assertEqual(diagnose_match(stops*100,points,routes,scopes),{'detail_reason':'DIAGNOSTIC_SIZE_LIMIT'})

    def test_mapper_attaches_details_only_to_explicit_internal_diagnostic(self):
        from unittest.mock import patch
        from datetime import datetime,timedelta,timezone
        from app.arrivals import mapping
        from test_arrival_mapping_connection import context,query_fixture
        def fake(kind,params,deadline):
            rows=query_fixture(kind,params,deadline)
            if kind=='stops':
                rows[0]['x']+=0.0004
            return rows
        trace={};expires=datetime.now(timezone.utc)+timedelta(seconds=200)
        with patch.object(mapping,'query',side_effect=fake):
            self.assertIsNone(mapping.resolve(context(),expires,diagnostics=trace))
        self.assertEqual(trace['match_checks']['detail_reason'],'COORDINATE_LIMIT_EXCEEDED')
        with patch.object(mapping,'query',side_effect=fake),patch.object(mapping,'diagnose_match') as diagnostic:
            self.assertIsNone(mapping.resolve(context(),expires))
            diagnostic.assert_not_called()

if __name__=='__main__':unittest.main()
