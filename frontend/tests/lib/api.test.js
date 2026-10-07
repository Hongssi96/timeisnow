import { afterEach, describe, expect, it, vi } from 'vitest';
import { apiRequest } from '../../src/lib/api';

const meta = { request_id: 'req_1', server_time: '2026-10-06T00:00:00Z' };
const response = (status = 200, body = { data: { status: 'ok' }, meta }, id = 'req_1') => ({
  status, ok: status >= 200 && status < 300,
  headers: new Headers(id ? { 'X-Request-ID': id } : {}), json: async () => body,
});
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });

describe('공통 API 응답과 실패 처리', () => {
  it('가입 입력 오류는 허용된 필드만 고정 문구로 안내한다', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => response(422, { error: { code: 'VALIDATION_ERROR', message: 'private-input', details: [
      { field: 'body.password', reason: 'private-password' },
      { field: 'body.private-input', reason: 'private-input' },
      { field: { raw: 'private-input' } },
      { field: 'body.password', reason: 'another-private-input' },
    ] }, meta })));
    const error = await apiRequest('/api/v1/auth/register').catch(error => error);
    expect(error.fields).toEqual(['body.password']);
    expect(error.message).toContain('15~128자');
    expect(error.message).not.toContain('private');
  });
  it('JSON 본문과 전달받은 요청 헤더를 유지한다', async () => {
    const fetchMock = vi.fn(async () => response()); vi.stubGlobal('fetch', fetchMock);
    await apiRequest('/api/v1/place-searches', { method: 'POST', body: { query: 'public example' }, headers: new Headers({ 'X-CSRF-Token': 'test-csrf' }) });
    const options = fetchMock.mock.calls[0][1];
    expect(options.body).toBe(JSON.stringify({ query: 'public example' }));
    expect(options.headers.get('Content-Type')).toBe('application/json');
    expect(options.headers.get('X-CSRF-Token')).toBe('test-csrf');
  });
  it('성공 데이터·요청 ID와 접수 202를 구분해 반환한다', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => response(202, { data: { job_id: 'job_1' }, meta })));
    const result = await apiRequest('/api/v1/jobs/job_1');
    expect(result.status).toBe(202);
    expect(result.data).toEqual({ job_id: 'job_1' });
    expect(result.meta.request_id).toBe('req_1');
  });
  it('204는 JSON 파싱 없이 헤더의 요청 ID를 반환한다', async () => {
    const res = response(204); res.json = vi.fn();
    vi.stubGlobal('fetch', vi.fn(async () => res));
    expect((await apiRequest('/api/v1/places/1')).data).toBeNull();
    expect(res.json).not.toHaveBeenCalled();
    vi.stubGlobal('fetch', vi.fn(async () => response(204, null, null)));
    await expect(apiRequest('/api/v1/places/1')).rejects.toMatchObject({ code: 'INVALID_RESPONSE' });
  });
  it('실패의 ID는 보존하고 서버가 보낸 원문/상세는 노출하지 않는다', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => response(500, { error: { code: 'INTERNAL_ERROR', message: 'secret-address' }, meta })));
    const error = await apiRequest('/api/v1/health').catch(error => error);
    expect(error.requestId).toBe('req_1');
    expect(error.status).toBe(500);
    expect(error.message).not.toContain('secret-address');
  });
  it('성공 상태라도 깨진 JSON이나 응답 형식은 성공으로 처리하지 않는다', async () => {
    const res = response(); res.json = async () => { throw new SyntaxError('secret-payload'); };
    vi.stubGlobal('fetch', vi.fn(async () => res));
    await expect(apiRequest('/api/v1/health')).rejects.toMatchObject({ code: 'INVALID_RESPONSE' });
    vi.stubGlobal('fetch', vi.fn(async () => response(200, { unrelated: true })));
    await expect(apiRequest('/api/v1/health')).rejects.toMatchObject({ code: 'INVALID_RESPONSE' });
  });
  it('헤더/본문 요청 ID 불일치를 성공으로 처리하지 않는다', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => response(200, { data: {}, meta }, 'req_other')));
    await expect(apiRequest('/api/v1/health')).rejects.toMatchObject({ code: 'INVALID_RESPONSE', requestId: 'req_other' });
  });
  it('네트워크 실패에 요청 ID를 만들거나 자동 재시도하지 않는다', async () => {
    const fetchMock = vi.fn(async () => { throw new TypeError('secret-url'); });
    vi.stubGlobal('fetch', fetchMock);
    await expect(apiRequest('/api/v1/health')).rejects.toMatchObject({ code: 'NETWORK_ERROR', requestId: null });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
  it('시간초과와 화면 이탈 취소를 구분한다', async () => {
    vi.useFakeTimers();
    vi.stubGlobal('fetch', vi.fn((_, { signal }) => new Promise((_, reject) => {
      signal.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')));
    })));
    const timeout = expect(apiRequest('/api/v1/health', { timeoutMs: 10 })).rejects.toMatchObject({ code: 'TIMEOUT' });
    await vi.advanceTimersByTimeAsync(11); await timeout;
    const controller = new AbortController();
    const cancelled = expect(apiRequest('/api/v1/health', { signal: controller.signal })).rejects.toMatchObject({ name: 'AbortError' });
    controller.abort(); await cancelled;
  });
  it('외부 주소로 앱 요청을 보내지 않는다', async () => {
    const fetchMock = vi.fn(); vi.stubGlobal('fetch', fetchMock);
    await expect(apiRequest('https://example.com/api/v1/health')).rejects.toMatchObject({ code: 'INVALID_RESPONSE' });
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
