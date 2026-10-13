import copy,unittest
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from test_arrival_mapping_connection import context,query_fixture
from app.arrivals import mapping
from app.arrivals.matching import diagnose_match,match_route


class OrderedMappingTests(unittest.TestCase):
    def resolve(self,rows,ctx=None,via=None,trace=None):
        def query(kind,params,deadline):
            if kind=='stops':return copy.deepcopy(rows)
            if kind=='via' and via is not None:return copy.deepcopy(via)
            if kind=='info':return [dict(query_fixture(kind,params,deadline)[0],routeId=params['routeId'])]
            return query_fixture(kind,params,deadline)
        with patch.object(mapping,'query',side_effect=query) as call:
            result=mapping.resolve(ctx or context(),datetime.now(timezone.utc)+timedelta(seconds=200),diagnostics=trace)
        return result,call

    def rows(self):return query_fixture('stops',{},0)

    def insert(self,rows,index,row):
        rows.insert(index,dict(row))
        turn=next(i+1 for i,r in enumerate(rows) if r['turnYn']=='Y')
        for i,r in enumerate(rows):r['stationSeq']=i+1;r['turnSeq']=turn

    def test_repeat_after_turn_is_rejected_before_final_uniqueness(self):
        rows=self.rows();self.insert(rows,4,dict(rows[1],turnYn='N'))
        trace={};value,call=self.resolve(rows,trace=trace)
        self.assertIsNotNone(value);self.assertEqual(trace['matched_count'],2)
        self.assertEqual(value.route_dest_id,'30')
        self.assertEqual(sum(c.args[0]=='info' for c in call.call_args_list),1)

    def test_two_visits_before_turn_stay_ambiguous(self):
        rows=self.rows();self.insert(rows,2,dict(rows[1],turnYn='N'))
        trace={};value,_=self.resolve(rows,trace=trace)
        self.assertIsNone(value);self.assertEqual(trace['reason'],'DIRECTION_MATCH_AMBIGUOUS')

    def test_two_public_routes_stay_ambiguous_without_info_request(self):
        via=[dict(query_fixture('via',{},0)[0],routeId=rid) for rid in ('99','98')]
        trace={};value,call=self.resolve(self.rows(),via=via,trace=trace)
        self.assertIsNone(value);self.assertEqual(trace['reason'],'ROUTE_MATCH_AMBIGUOUS')
        self.assertFalse(any(c.args[0]=='info' for c in call.call_args_list))

    def test_every_provided_name_must_remain_in_order(self):
        rows=self.rows()
        self.insert(rows,1,dict(rows[0],stationId='70',stationName='먼저',turnYn='N'))
        self.insert(rows,2,dict(rows[0],stationId='71',stationName='나중',turnYn='N'))
        for middle in ([{'name':'누락'}],[{'name':'나중'},{'name':'먼저'}]):
            ctx=context();ctx['stops'][1:1]=middle
            self.assertIsNone(self.resolve(rows,ctx)[0])
        ctx=context();ctx['stops'][1:1]=[{'name':'먼저'},{'name':'나중'}]
        self.assertIsNotNone(self.resolve(rows,ctx)[0])

    def test_extra_stops_do_not_relax_coordinates_or_official_order(self):
        rows=self.rows();self.insert(rows,1,dict(rows[0],stationId='70',stationName='추가',turnYn='N'))
        for field,value in [('x',None),('x',127.028),('stationId','999')]:
            bad=copy.deepcopy(rows);bad[0][field]=value
            self.assertIsNone(self.resolve(bad)[0])
        via=[dict(query_fixture('via',{},0)[0],staOrder=2)]
        self.assertIsNone(self.resolve(rows,via=via)[0])

    def test_turn_and_sequence_integrity_still_required(self):
        for change in ('gap','duplicate','turn_conflict','turn_id','marker'):
            rows=self.rows()
            if change=='gap':rows[-1]['stationSeq']=7
            if change=='duplicate':rows[-1]['stationSeq']=4
            if change=='turn_conflict':rows[-1]['turnSeq']=4
            if change=='turn_id':rows[2]['stationId']='999'
            if change=='marker':rows[0]['turnYn']='Y'
            self.assertIsNone(self.resolve(rows)[0],change)

    def test_candidate_limit_rejects_all_instead_of_first_subset(self):
        rows=self.rows()
        for _ in range(32):self.insert(rows,2,dict(rows[1],turnYn='N'))
        trace={};value,call=self.resolve(rows,trace=trace)
        self.assertIsNone(value);self.assertEqual(trace['reason'],'VISIT_CANDIDATE_LIMIT')
        self.assertFalse(any(c.args[0]=='info' for c in call.call_args_list))
        result=match_route(context()['stops'],context()['points'],[('99',rows)],30,max_matches=32)
        self.assertEqual(result,{'status':'candidate_limit','matches':[]})

    def test_exact_candidate_limit_is_allowed_but_remains_ambiguous(self):
        rows=self.rows()
        for _ in range(31):self.insert(rows,2,dict(rows[1],turnYn='N'))
        trace={};value,call=self.resolve(rows,trace=trace)
        self.assertIsNone(value);self.assertEqual(trace['matched_count'],32)
        self.assertEqual(trace['reason'],'DIRECTION_MATCH_AMBIGUOUS')
        self.assertEqual(sum(c.args[0]=='info' for c in call.call_args_list),1)

    def test_ordered_diagnostic_checks_gap_endpoint_coordinates(self):
        rows=self.rows();self.insert(rows,1,dict(rows[0],stationId='70',stationName='추가',turnYn='N'))
        ctx=context();scopes=[{'route_id':'99','board_station_id':'10','board_order':1}]
        result=diagnose_match(ctx['stops'],ctx['points'],[('99',rows)],scopes,require_contiguous=False)
        self.assertEqual(result['contiguous_name_pairs'],0);self.assertEqual(result['passing_pairs'],1)
        rows[0]['x']+=0.0004
        self.assertEqual(diagnose_match(ctx['stops'],ctx['points'],[('99',rows)],scopes,require_contiguous=False)['detail_reason'],'COORDINATE_LIMIT_EXCEEDED')
        trace={};self.assertIsNone(self.resolve(rows,trace=trace)[0])
        self.assertEqual(trace['match_checks']['detail_reason'],'COORDINATE_LIMIT_EXCEEDED')

if __name__=='__main__':unittest.main()
