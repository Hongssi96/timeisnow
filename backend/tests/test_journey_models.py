"""Common transit/walking semantics, missing evidence, and legacy compatibility."""
import copy
import json
import unittest
import sys
from pathlib import Path
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import auth, journey_provider
from app.journey_models import Candidate, LegacyCandidate, LegacyLeg, common_candidate
import test_journeys


def fixture(kinds=('BUS','SUBWAY'), walks=True):
    prototype=test_journeys.route()['steps']
    steps=[]
    if walks:steps.append(copy.deepcopy(prototype[0]))
    for index,kind in enumerate(kinds):
        if index and walks:
            walk=copy.deepcopy(prototype[0]);walk['properties']['time']=40;steps.append(walk)
        step=copy.deepcopy(prototype[1]);step['properties']['type']=kind
        step['properties']['stops']=[{'name':'합성 승차 '+str(index)},{'name':'합성 하차 '+str(index)}]
        step['properties']['vehicles']=[{'name':'합성 차량 '+str(index),'type':'새로운 분류'}]
        steps.append(step)
    if walks:steps.append(copy.deepcopy(prototype[-1]))
    return {'properties':{'type':'BUS_AND_SUBWAY' if len(set(kinds))==2 else kinds[0],
        'totalTime':sum(step['properties']['time'] for step in steps),
        'totalDistance':sum(step['properties']['distance'] for step in steps),'transfers':len(kinds)-1},'steps':steps}


def normalized(route):
    return journey_provider.normalize({'status':'OK','routes':[route]},'balanced')[0][0]


def legacy(candidate):
    data={key:copy.deepcopy(candidate[key]) for key in LegacyCandidate.model_fields}
    data['ordered_legs']=[{key:copy.deepcopy(leg[key]) for key in LegacyLeg.model_fields} for leg in candidate['ordered_legs']]
    return data


class CommonModelTests(unittest.TestCase):
    def test_direct_and_all_transfer_pairs_preserve_order_roles_and_names(self):
        for kinds in [('BUS',),('SUBWAY',),('BUS','BUS'),('BUS','SUBWAY'),('SUBWAY','BUS'),('SUBWAY','SUBWAY')]:
            with self.subTest(kinds=kinds):
                data=normalized(fixture(kinds));legs=data['ordered_legs']
                self.assertEqual([leg['sequence'] for leg in legs],list(range(len(legs))))
                self.assertEqual([leg['walking_role'] for leg in legs if leg['type']=='WALKING'],['access','egress'] if len(kinds)==1 else ['access','transfer','egress'])
                transit=[leg for leg in legs if leg['type']!='WALKING']
                self.assertEqual([leg['type'] for leg in transit],list(kinds));self.assertEqual(data['transfer_count_computed'],len(kinds)-1)
                for leg in transit:
                    self.assertEqual(leg['boarding']['name'],leg['stops'][0]);self.assertIsNone(leg['boarding']['public_id'])
                    self.assertEqual(leg['direction']['source'],'provider_stop_order');self.assertIsNone(leg['direction']['public_direction_id'])
                    self.assertEqual(leg['vehicle_options'][0]['provider_type'],'새로운 분류')
                self.assertEqual(len(data['connections']),len(kinds)-1)
                if data['connections']:
                    self.assertEqual(data['connections'][0]['walking_seconds'],40)
                    self.assertEqual(data['connections'][0]['feasibility'],'unknown')
                self.assertEqual(data['timing_breakdown']['status'],'consistent');Candidate.model_validate(data)

    def test_missing_walk_is_unknown_while_explicit_zero_is_zero(self):
        data=normalized(fixture(walks=False))
        self.assertIsNone(data['connections'][0]['walking_seconds']);self.assertEqual(data['connections'][0]['walking_leg_ids'],[])
        for reason in ['ACCESS_WALK_MISSING','EGRESS_WALK_MISSING','TRANSFER_WALK_MISSING']:self.assertIn(reason,data['missing_segments'])
        explicit=fixture();explicit['steps'][2]['properties']['time']=0;explicit['properties']['totalTime']-=40
        data=normalized(explicit);self.assertEqual(data['connections'][0]['walking_seconds'],0)
        self.assertNotIn('TRANSFER_WALK_MISSING',data['missing_segments'])

    def test_adjacent_walking_steps_keep_their_scope(self):
        value=fixture();value['steps'].insert(1,copy.deepcopy(value['steps'][0]));value['steps'].insert(4,copy.deepcopy(value['steps'][3]))
        data=normalized(value)
        roles=[leg['walking_role'] for leg in data['ordered_legs'] if leg['type']=='WALKING']
        self.assertEqual(roles,['access','access','transfer','transfer','egress'])
        self.assertEqual(data['connections'][0]['walking_seconds'],80)

    def test_unallocated_time_is_not_claimed_as_waiting_and_inconsistency_is_visible(self):
        for delta,status,unallocated in [(100,'unallocated',100),(-10,'inconsistent',None)]:
            value=fixture();value['properties']['totalTime']+=delta;data=normalized(value)
            self.assertEqual(data['timing_breakdown']['status'],status);self.assertEqual(data['timing_breakdown']['unallocated_seconds'],unallocated)
            self.assertEqual(data['total_seconds'],value['properties']['totalTime']);self.assertIsNone(data['estimated_arrival_at'])
            self.assertEqual('DURATION_TOTAL_MISMATCH' in data['missing_segments'],delta<0)

    def test_transfer_mismatch_is_visible_and_observed_limit_is_not_bypassed(self):
        value=fixture();value['properties']['transfers']=0;data=normalized(value)
        self.assertEqual(data['transfer_count'],0);self.assertEqual(data['transfer_count_computed'],1)
        self.assertIn('TRANSFER_COUNT_MISMATCH',data['missing_segments'])
        value=fixture(('BUS','BUS','BUS','BUS'));value['properties']['transfers']=0
        candidates,reasons=journey_provider.normalize({'status':'OK','routes':[value]},'balanced')
        self.assertEqual(candidates,[]);self.assertIn('TRANSFER_LIMIT',reasons)

    def test_legacy_upgrade_is_stable_and_retains_existing_fields(self):
        new=normalized(fixture());old=legacy(new)
        first=common_candidate(old);second=common_candidate(old)
        self.assertEqual(first,second)
        for key in ['candidate_id','transfer_count','total_seconds','walking_seconds','type']:
            self.assertEqual(first[key],old[key])
        for before,after in zip(old['ordered_legs'],first['ordered_legs']):
            for key in LegacyLeg.model_fields:self.assertEqual(before[key],after[key])
        self.assertIsNone(first['ordered_legs'][1]['vehicle_options'][0]['provider_type'])
        self.assertEqual(common_candidate(new),new)

    def test_corrupt_sequence_identity_connection_and_raw_fields_are_rejected(self):
        valid=normalized(fixture());bad=[]
        for mutate in [lambda v:v['ordered_legs'][1].update(sequence=0),
                       lambda v:v['ordered_legs'][1].update(leg_id=v['ordered_legs'][0]['leg_id']),
                       lambda v:v['connections'][0].update(from_leg_id=str(uuid4())),
                       lambda v:v['ordered_legs'][0].update(walking_role='egress'),
                       lambda v:v['ordered_legs'][1]['boarding'].update(public_id='guessed'),
                       lambda v:v.update(latitude=37.5),lambda v:v.update(total_seconds=True),
                       lambda v:v['timing_breakdown'].update(unallocated_seconds=999)]:
            item=copy.deepcopy(valid);mutate(item);bad.append(item)
        old=legacy(valid);old['ordered_legs'][0]['seconds']=-1;bad.append(old)
        for item in bad:
            with self.assertRaises(auth.AuthError) as error:common_candidate(item)
            self.assertEqual(error.exception.code,'PROVIDER_RESPONSE_INVALID')

    def test_route_type_mismatch_and_invalid_vehicle_category_are_rejected(self):
        for modify in [lambda v:v['properties'].update(type='BUS'),
                       lambda v:v['steps'][1]['properties']['vehicles'][0].update(type=123)]:
            value=fixture();modify(value)
            with self.assertRaises(auth.AuthError):normalized(value)
        self.assertNotIn('127.0276',json.dumps(normalized(fixture())))
