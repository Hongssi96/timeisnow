"""Explicit bounded live check: public route, isolated DB, summaries only."""
import argparse,asyncio,json,sys,urllib.request,urllib.parse,urllib.error
from pathlib import Path
from unittest.mock import patch
from app.common import request_logging
from app.arrivals import cache,service,mapping

# This CLI intentionally reuses the repository's isolated-schema ASGI harness.
sys.path.insert(0,str(Path(__file__).resolve().parent/'tests'))
from test_auth import AuthTests
from app.common.database import database
from test_auth import connect_db
from psycopg import sql
import re

PUBLIC_BODY={'origin':{'type':'map_pin','longitude':127.11119217,'latitude':37.39477123},
             'destination':{'type':'map_pin','longitude':127.12628814,'latitude':37.41993056},
             'timing':{'mode':'depart_now','timezone':'Asia/Seoul'}}

class Budget:
    def __init__(self,maximum):
        if type(maximum) is not int or not 1<=maximum<=10:raise ValueError('Invalid request budget')
        self.maximum=maximum;self.count=0;self.exhausted=False
    def before(self,url):
        address=url.full_url if isinstance(url,urllib.request.Request) else url
        parsed=urllib.parse.urlsplit(address)
        if parsed.scheme!='https' or parsed.hostname not in ('dapi.kakao.com','apis.data.go.kr') or parsed.port not in (None,443) or parsed.username or parsed.password:
            raise urllib.error.URLError('Probe destination rejected')
        if self.count>=self.maximum:
            self.exhausted=True
            raise urllib.error.URLError('Probe request budget exhausted')
        self.count+=1


def eligible(candidates):
    for candidate in candidates:
        first=next((l for l in candidate['ordered_legs'] if l['type']!='WALKING'),None)
        if first and first['type']=='BUS' and candidate['transfer_count']==0 and len(first['vehicles'])==1:
            return candidate
    return None


def same_evidence(one,two):
    # Countdown/elapsed-candidate projection is intentionally reevaluated per GET.
    def stable(value):
        return {key:value.get(key) for key in ('model_version','search_id','candidate_id','first_leg_id',
                'source_status','timing_basis','received_at','generated_at','expires_at')}
    return stable(one)==stable(two)


async def run(maximum):
    budget=Budget(maximum)
    original_open=urllib.request.OpenerDirector.open
    original_resolve=mapping.resolve
    diagnostics={}
    def traced_resolve(context,expires_at):
        return original_resolve(context,expires_at,diagnostics=diagnostics)
    def guarded_open(opener,url,*args,**kwargs):
        budget.before(url)
        return original_open(opener,url,*args,**kwargs)
    case=AuthTests(methodName='test_signup_login_me_logout_and_storage')
    summary={'status':'not_started','request_count':0,'valid_for_guidance':False}
    ready=False;disabled=request_logging.logger.disabled
    try:
        request_logging.logger.disabled=True
        case.setUp();ready=True;cache.clear()
        await case.signup_login()
        with patch.object(urllib.request.OpenerDirector,'open',guarded_open),patch.object(mapping,'resolve',traced_resolve):
            accepted=await case.call('/journey-searches',PUBLIC_BODY)
            if accepted[0]!=202:return dict(summary,status='search_rejected',http_status=accepted[0],request_count=budget.count,budget_exhausted=budget.exhausted)
            search_id=accepted[2]['data']['search_id']
            result=await case.call('/journey-searches/'+search_id)
            data=result[2].get('data') or {}
            if data.get('status')!='succeeded':return dict(summary,status='search_failed',error_code=(data.get('error') or {}).get('code'),request_count=budget.count,budget_exhausted=budget.exhausted)
            candidate=eligible(data.get('candidates') or [])
            if candidate is None:return dict(summary,status='no_eligible_bus',request_count=budget.count,budget_exhausted=budget.exhausted)
            path='/journey-searches/'+search_id+'/candidates/'+candidate['candidate_id']+'/first-arrivals'
            with database() as connection:before=connection.execute('SELECT * FROM journey_searches WHERE id=%s',(search_id,)).fetchone()
            response=await case.call(path)
            summary.update(http_status=response[0],request_count=budget.count,budget_exhausted=budget.exhausted,mapping_diagnostics=diagnostics.copy())
            if response[0]!=200:
                summary.update(status='arrival_error',error_code=response[2].get('error',{}).get('code'))
                return summary
            evidence=response[2]['data']
            count_before_replay=budget.count
            replay=await case.call(path)
            with database() as connection:after=connection.execute('SELECT * FROM journey_searches WHERE id=%s',(search_id,)).fetchone()
            summary.update(status='connection_verified' if evidence.get('received_at') else 'mapping_unconfirmed',
                           arrival_status=evidence['status'],source_status=evidence['source_status'],
                           candidate_count=len(evidence['candidates']),generated_at_present=evidence['generated_at'] is not None,
                           predicted_arrival_available=any(c['predicted_arrival_at'] is not None for c in evidence['candidates']),
                           valid_for_guidance=evidence['valid_for_guidance'],second_get_no_upstream=budget.count==count_before_replay,
                           second_get_same_evidence=replay[0]==200 and same_evidence(replay[2]['data'],evidence),
                           stored_search_unchanged=before==after,request_count=budget.count)
            return summary
    except Exception as error:
        return dict(summary,status='probe_failed',exception_type=type(error).__name__,request_count=budget.count,budget_exhausted=budget.exhausted)
    finally:
        cache.clear()
        try:
            if ready:case.tearDown()
            elif hasattr(case,'schema'):
                for name in ('db_patch','env_patch'):
                    if hasattr(case,name):getattr(case,name).stop()
                if not re.fullmatch(r'auth_test_[0-9a-f]{32}',case.schema):raise ValueError('Unexpected isolated schema')
                with connect_db() as connection:
                    connection.execute(sql.SQL('DROP SCHEMA IF EXISTS {} CASCADE').format(sql.Identifier(case.schema)))
        except Exception as error:
            return dict(summary,status='cleanup_failed',exception_type=type(error).__name__,request_count=budget.count)
        finally:request_logging.logger.disabled=disabled


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max-requests',type=int,choices=range(1,11),default=10)
    args=parser.parse_args()
    result=asyncio.run(run(args.max_requests))
    print(json.dumps(result))
    return 0 if result['status']=='connection_verified' else 1

if __name__=='__main__':raise SystemExit(main())
