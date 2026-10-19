import { ApiError,apiRequest,isServerTime } from './api';
import { safeJourneyId } from './journeys';
import { validateArrivalEvidence } from './arrivals';
function adjustedWalk(seconds,factor){
  const [whole,fraction='']=String(factor).split('.');
  const denominator=10n**BigInt(fraction.length);
  return Number((BigInt(seconds)*BigInt(whole+fraction)+denominator-1n)/denominator);
}
export function validPersonalWalk(p,at){
  return p&&safeJourneyId(p.estimate_id)&&safeJourneyId(p.revision_id)
    &&Number.isSafeInteger(p.base_seconds)&&p.base_seconds>0&&p.base_seconds<=86400
    &&Number.isFinite(p.applied_duration_factor)&&p.applied_duration_factor>=.5&&p.applied_duration_factor<=2
    &&Number.isSafeInteger(p.estimated_seconds)&&p.estimated_seconds===adjustedWalk(p.base_seconds,p.applied_duration_factor)
    &&Number.isSafeInteger(p.profile_version)&&p.profile_version>0&&['ai_estimate','profile_recalculation'].includes(p.source)
    &&typeof p.reused==='boolean'&&isServerTime(p.expires_at)&&Date.parse(p.expires_at)>Date.parse(at);
}
export async function getFirstDeparture(searchId,candidateId,signal) {
  if (!safeJourneyId(searchId)||!safeJourneyId(candidateId)) throw new ApiError('INVALID_RESPONSE');
  const result=await apiRequest(`/api/v1/journey-searches/${searchId}/candidates/${candidateId}/first-departure?include_connections=true`,{signal,timeoutMs:25000});
  return readFirstDeparture(result,searchId,candidateId);
}
export function readFirstDeparture(result,searchId,candidateId) {
  const d=result.data;
  if(d?.model_version!=='first.departure.v1'||d.search_id!==searchId||d.candidate_id!==candidateId
    ||!['ready','insufficient_data','not_enough_time','stale','unsupported'].includes(d.status)
    ||!['recommended','now'].includes(d.departure_basis)||typeof d.valid_for_guidance!=='boolean'
    ||!isServerTime(d.calculated_at)||!isServerTime(d.valid_until)||!Number.isInteger(d.profile_version)||d.profile_version<1
    ||!Number.isInteger(d.buffer_seconds)||d.buffer_seconds<0||d.buffer_seconds>1800
    ||!['meets_buffer','below_buffer','unreachable','unknown'].includes(d.slack_status)) throw new ApiError('INVALID_RESPONSE');
  validateArrivalEvidence(d.arrival_evidence,searchId,candidateId);
  if(d.guidance_id!==undefined&&d.guidance_id!==null&&!safeJourneyId(d.guidance_id))throw new ApiError('INVALID_RESPONSE');
  if(d.departure_state!==undefined&&!['unconfirmed','reported_departed'].includes(d.departure_state))throw new ApiError('INVALID_RESPONSE');
  if(d.departure_state==='reported_departed'&&(d.valid_for_guidance||d.guidance_id!==null||d.status!=='insufficient_data'
    ||[d.recommended_departure_at,d.selected_departure_at,d.vehicle_arrival_at,d.arrival_candidate_id,d.slack_seconds,d.estimated_final_alighting_at].some(value=>value!==null)))throw new ApiError('INVALID_RESPONSE');
  if(d.first_leg_id!==d.arrival_evidence.first_leg_id||d.timing_basis!==d.arrival_evidence.timing_basis
    ||Date.parse(d.valid_until)>Date.parse(d.arrival_evidence.expires_at)) throw new ApiError('INVALID_RESPONSE');
  if(d.provider_approach_source!==undefined && ![null,'transit_segment','boarding_walk'].includes(d.provider_approach_source)) throw new ApiError('INVALID_RESPONSE');
  if(d.provider_approach_source==='boarding_walk' && (!isServerTime(d.approach_fetched_at)||!isServerTime(d.approach_valid_until)
    ||Date.parse(d.approach_fetched_at)>Date.parse(d.calculated_at)||Date.parse(d.approach_valid_until)<Date.parse(d.valid_until)
    ||Date.parse(d.approach_valid_until)<=Date.parse(d.approach_fetched_at))) throw new ApiError('INVALID_RESPONSE');
  if(d.personal_walk!==undefined&&d.personal_walk!==null&&(!validPersonalWalk(d.personal_walk,d.calculated_at)||Date.parse(d.personal_walk.expires_at)<Date.parse(d.valid_until)))throw new ApiError('INVALID_RESPONSE');
  if(d.approach_basis==='ai_validated'&&(!d.personal_walk||d.personal_walk.estimated_seconds!==d.approach_seconds
    ||d.personal_walk.base_seconds!==d.provider_approach_seconds||d.personal_walk.profile_version!==d.profile_version
    ||d.personal_walk.applied_duration_factor!==d.applied_duration_factor))throw new ApiError('INVALID_RESPONSE');
  if(d.valid_for_guidance && (d.status!=='ready'||!d.arrival_evidence.valid_for_guidance||!['provider_personalized','ai_validated'].includes(d.approach_basis)
    ||!Number.isSafeInteger(d.approach_seconds)||d.approach_seconds<=0
    ||!Number.isSafeInteger(d.provider_approach_seconds)||d.provider_approach_seconds<=0
    ||!Number.isFinite(d.applied_duration_factor)||d.applied_duration_factor<.5||d.applied_duration_factor>2
    ||!Number.isInteger(d.slack_seconds)||d.slack_seconds<0
    ||![d.recommended_departure_at,d.selected_departure_at,d.vehicle_arrival_at].every(isServerTime)
    ||Date.parse(d.recommended_departure_at)!==Date.parse(d.vehicle_arrival_at)-(d.approach_seconds+d.buffer_seconds)*1000
    ||!d.arrival_evidence.candidates.some(c=>c.candidate_id===d.arrival_candidate_id&&c.predicted_arrival_at===d.vehicle_arrival_at))) throw new ApiError('INVALID_RESPONSE');
  if(d.supplemental_walks!==undefined&&(!Array.isArray(d.supplemental_walks)||d.supplemental_walks.length>3))throw new ApiError('INVALID_RESPONSE');
  if(d.connection_status!==undefined && (!['not_checked','estimated_feasible','unavailable','unknown','stale'].includes(d.connection_status)
    ||!Array.isArray(d.transfers)||d.transfers.length>2
    ||d.transfers.some(c=>!safeJourneyId(c.connection_id)||!safeJourneyId(c.from_leg_id)||!safeJourneyId(c.to_leg_id)
      ||!['estimated_feasible','unavailable','unknown'].includes(c.feasibility)
      ||!['none','source_generation','receipt_estimate'].includes(c.time_source)
      ||!Number.isInteger(c.transfer_buffer_seconds)||c.transfer_buffer_seconds<0||c.transfer_buffer_seconds>1800
      ||(c.transfer_walk_seconds!==null&&(!Number.isSafeInteger(c.transfer_walk_seconds)||c.transfer_walk_seconds<0
        ||(c.transfer_walk_seconds===0&&!d.supplemental_walks?.some(w=>w?.role==='transfer'&&w.source==='same_stop'&&w.connection_id===c.connection_id))))
      ||[c.estimated_alighting_at,c.minimum_boarding_at,c.next_boarding_at].some(t=>t!==null&&!isServerTime(t))
      ||(c.feasibility==='estimated_feasible'&&(!isServerTime(c.next_boarding_at)||!isServerTime(c.minimum_boarding_at)||Date.parse(c.next_boarding_at)<Date.parse(c.minimum_boarding_at)))))) throw new ApiError('INVALID_RESPONSE');
  if(d.supplemental_walks!==undefined){
    const seen=new Set();
    for(const w of d.supplemental_walks){
      if(!w||!['transfer','egress'].includes(w.role)||!['walking_route','same_stop'].includes(w.source)||!safeJourneyId(w.from_leg_id)
        ||!Number.isSafeInteger(w.provider_seconds)||w.provider_seconds<0||w.provider_seconds>86400
        ||!Number.isFinite(w.applied_duration_factor)||w.applied_duration_factor<.5||w.applied_duration_factor>2
        ||(d.valid_for_guidance&&w.applied_duration_factor!==d.applied_duration_factor)
        ||!Number.isSafeInteger(w.walking_seconds)||w.walking_seconds<0||w.walking_seconds>172800
        ||(w.source==='same_stop'&&(w.role!=='transfer'||w.provider_seconds!==0||w.walking_seconds!==0))
        ||(w.source==='walking_route'&&(w.provider_seconds===0||w.walking_seconds===0))
        ||w.walking_seconds!==adjustedWalk(w.provider_seconds,w.applied_duration_factor)
        ||!isServerTime(w.fetched_at)||!isServerTime(w.valid_until)
        ||Date.parse(w.fetched_at)>Date.parse(d.calculated_at)||Date.parse(w.valid_until)<=Date.parse(w.fetched_at)
        ||Date.parse(w.valid_until)<Date.parse(d.valid_until)
        ||(w.role==='egress'&&(w.connection_id!==null||w.to_leg_id!==null))
        ||(w.role==='transfer'&&(!safeJourneyId(w.connection_id)||!safeJourneyId(w.to_leg_id)
          ||!d.transfers?.some(c=>c.connection_id===w.connection_id&&c.from_leg_id===w.from_leg_id&&c.to_leg_id===w.to_leg_id))))throw new ApiError('INVALID_RESPONSE');
      const key=w.role==='egress'?'egress':w.connection_id;
      if(seen.has(key))throw new ApiError('INVALID_RESPONSE');seen.add(key);
    }
  }
  if(d.personal_segment_walks!==undefined){
    if(!Array.isArray(d.personal_segment_walks)||d.personal_segment_walks.length>5)throw new ApiError('INVALID_RESPONSE');
    const seen=new Set();
    for(const w of d.personal_segment_walks){
      const key=w?.kind+':'+w?.leg_id;
      if(!w||!['station_internal','transfer'].includes(w.kind)||!safeJourneyId(w.leg_id)||w.source!=='manual_history'
        ||typeof w.label!=='string'||!w.label.trim()||w.label.length>60
        ||!Number.isSafeInteger(w.profile_version)||w.profile_version!==d.profile_version
        ||typeof w.basis_key!=='string'||!/^[a-f0-9]{64}$/.test(w.basis_key)
        ||!Number.isInteger(w.sample_count)||w.sample_count<5||w.sample_count>20
        ||!Number.isInteger(w.estimate_seconds)||w.estimate_seconds<1||w.estimate_seconds>7200
        ||!isServerTime(w.valid_until)||Date.parse(w.valid_until)<Date.parse(d.valid_until)||seen.has(key))throw new ApiError('INVALID_RESPONSE');
      seen.add(key);
    }
  }
  const target=d.target_evaluation;
  if(target!==undefined&&target!==null){
    if(target.model_version!=='target.arrival.v1'||target.scope!=='selected_routine_candidate'||!['not_configured','estimated_meets','estimated_late','target_passed','unknown','stale'].includes(target.status)||!isServerTime(target.evaluated_at)
      ||(target.target_arrival_at!==null&&!isServerTime(target.target_arrival_at))||!['none','provider_timeline'].includes(target.timing_basis))throw new ApiError('INVALID_RESPONSE');
    const numeric=['estimated_meets','estimated_late'].includes(target.status);
    if(numeric){
      if(!d.valid_for_guidance||d.connection_status!=='estimated_feasible'||!isServerTime(target.target_arrival_at)||!isServerTime(target.estimated_destination_arrival_at)||target.timing_basis!=='provider_timeline'
        ||!Number.isSafeInteger(target.egress_seconds)||target.egress_seconds<=0||!Number.isSafeInteger(target.margin_seconds)
        ||target.margin_seconds!==Math.floor((Date.parse(target.target_arrival_at)-Date.parse(target.estimated_destination_arrival_at))/1000)
        ||(target.status==='estimated_meets')!==(Date.parse(target.estimated_destination_arrival_at)<=Date.parse(target.target_arrival_at))
        ||!isServerTime(d.estimated_final_alighting_at)||Date.parse(target.estimated_destination_arrival_at)!==Date.parse(d.estimated_final_alighting_at)+target.egress_seconds*1000)throw new ApiError('INVALID_RESPONSE');
    }else if(target.estimated_destination_arrival_at!==null||target.margin_seconds!==null||target.egress_seconds!==null||target.timing_basis!=='none')throw new ApiError('INVALID_RESPONSE');
    if((target.status==='not_configured')!==(target.target_arrival_at===null))throw new ApiError('INVALID_RESPONSE');
  }
  return result;
}
