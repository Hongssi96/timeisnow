import { ApiError, apiRequest, isServerTime } from './api';
import { safeJourneyId } from './journeys';

export async function getFirstArrivals(searchId, candidateId, signal) {
  if (!safeJourneyId(searchId) || !safeJourneyId(candidateId)) throw new ApiError('INVALID_RESPONSE');
  const result = await apiRequest(`/api/v1/journey-searches/${searchId}/candidates/${candidateId}/first-arrivals`, { signal });
  validateArrivalEvidence(result.data,searchId,candidateId);
  return result;
}

export function validateArrivalEvidence(d,searchId,candidateId) {
  const states = ['mapping_required','unsupported','no_arrivals','insufficient_data','fresh','estimated','expired'];
  if (d?.model_version !== 'arrival.evidence.v2' || d.search_id !== searchId || d.candidate_id !== candidateId
    || !states.includes(d.status) || !['none','source_generation','receipt_estimate'].includes(d.timing_basis)
    || !['unknown','fresh','stale','clock_mismatch'].includes(d.source_status) || typeof d.valid_for_guidance !== 'boolean'
    || !isServerTime(d.expires_at) || (d.received_at !== null && !isServerTime(d.received_at))
    || (d.generated_at !== null && !isServerTime(d.generated_at)) || !Array.isArray(d.candidates) || d.candidates.length > 2
    || d.candidates.some(c => !safeJourneyId(c.candidate_id) || !Number.isInteger(c.provider_prediction_seconds)
      || c.provider_prediction_seconds <= 0 || c.provider_prediction_seconds > 86400
      || (c.predicted_arrival_at !== null && !isServerTime(c.predicted_arrival_at)))) throw new ApiError('INVALID_RESPONSE');
  if (d.valid_for_guidance && (!(d.status === 'estimated' && d.source_status === 'unknown' && d.timing_basis === 'receipt_estimate' && d.generated_at === null)
    && !(d.status === 'fresh' && d.source_status === 'fresh' && d.timing_basis === 'source_generation' && isServerTime(d.generated_at)))) throw new ApiError('INVALID_RESPONSE');
  if (d.valid_for_guidance && (!isServerTime(d.received_at) || !d.candidates.length || d.candidates.some(c=>!isServerTime(c.predicted_arrival_at)))) throw new ApiError('INVALID_RESPONSE');
  return d;
}
