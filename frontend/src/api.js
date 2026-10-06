// App APIs only. Never log URLs, headers, bodies, or raw exceptions here.
const messages = {
  NETWORK_ERROR: '서버에 연결할 수 없어요. 백엔드가 실행 중인지 확인하고 다시 시도해주세요.',
  TIMEOUT: '응답이 늦어 확인을 중지했어요. 잠시 후 다시 시도해주세요.',
  INVALID_RESPONSE: '서버 응답을 확인할 수 없어요. 다시 시도해주세요.',
  AUTH_REQUIRED: '로그인이 필요해요.',
  INVALID_CREDENTIALS: '이메일 또는 비밀번호를 확인해주세요.',
  EMAIL_UNAVAILABLE: '이미 가입된 이메일이에요. 로그인해주세요.',
  CSRF_INVALID: '화면을 새로고침하고 다시 시도해주세요.',
  SERVICE_UNAVAILABLE: '인증 서버에 연결할 수 없어요. 잠시 후 다시 시도해주세요.',
  SESSION_EXPIRED: '로그인이 만료됐어요. 다시 로그인해주세요.',
  RESOURCE_NOT_FOUND: '요청한 정보를 찾을 수 없어요.',
  METHOD_NOT_ALLOWED: '이 요청을 처리할 수 없어요.',
  VALIDATION_ERROR: '입력값을 확인해주세요.',
  RATE_LIMITED: '요청이 많아요. 잠시 후 다시 시도해주세요.',
  HTTP_ERROR: '요청을 처리하지 못했어요. 잠시 후 다시 시도해주세요.',
  INTERNAL_ERROR: '서버에서 처리하지 못했어요. 잠시 후 다시 시도해주세요.',
};

export class ApiError extends Error {
  constructor(code, { status = 0, requestId = null } = {}) {
    super(messages[code] || messages.HTTP_ERROR);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.requestId = requestId;
  }
}

const safeId = value => typeof value === 'string' && /^[A-Za-z0-9_-]{1,128}$/.test(value) ? value : null;
export const isServerTime = value => typeof value === 'string'
  && /T.*(?:Z|[+-]\d{2}:\d{2})$/.test(value) && Number.isFinite(Date.parse(value));

export async function apiRequest(path, { signal, timeoutMs = 10000, body: input, ...options } = {}) {
  let url;
  try {
    if (typeof path !== 'string') throw new TypeError();
    url = new URL(path, window.location.origin);
  } catch { throw new ApiError('INVALID_RESPONSE'); }
  if (url.origin !== window.location.origin || !url.pathname.startsWith('/api/v1/')
      || !path.startsWith('/api/v1/') || !Number.isFinite(timeoutMs) || timeoutMs <= 0) {
    throw new ApiError('INVALID_RESPONSE');
  }
  const controller = new AbortController();
  const cancel = () => controller.abort();
  signal?.addEventListener('abort', cancel, { once: true });
  if (signal?.aborted) controller.abort();
  let timedOut = false;
  let status = 0;
  let requestId = null;
  const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeoutMs);
  try {
    const headers = new Headers(options.headers);
    headers.set('Accept', 'application/json');
    if (input !== undefined) headers.set('Content-Type', 'application/json');
    const response = await fetch(path, {
      ...options, credentials: 'same-origin', redirect: 'error', signal: controller.signal,
      headers, ...(input !== undefined ? { body: JSON.stringify(input) } : {}),
    });
    status = response.status;
    const headerId = safeId(response.headers?.get('X-Request-ID'));
    requestId = headerId;
    if (status === 204) {
      if (!headerId) throw new ApiError('INVALID_RESPONSE', { status });
      return { data: null, meta: { request_id: headerId }, status };
    }
    let body;
    try { body = await response.json(); }
    catch { throw new ApiError(response.ok ? 'INVALID_RESPONSE' : 'HTTP_ERROR', { status, requestId }); }
    const bodyId = safeId(body?.meta?.request_id);
    requestId = headerId || bodyId;
    if (headerId && bodyId && headerId !== bodyId) throw new ApiError('INVALID_RESPONSE', { status, requestId });
    if (!response.ok) {
      const code = typeof body?.error?.code === 'string' && /^[A-Z][A-Z0-9_]{0,63}$/.test(body.error.code)
        ? body.error.code : 'HTTP_ERROR';
      throw new ApiError(code, { status, requestId });
    }
    if (!body || !Object.hasOwn(body, 'data') || !bodyId || !isServerTime(body.meta.server_time)) {
      throw new ApiError('INVALID_RESPONSE', { status, requestId });
    }
    return { data: body.data, meta: body.meta, status };
  } catch (error) {
    if (signal?.aborted) throw new DOMException('Cancelled', 'AbortError');
    if (timedOut) throw new ApiError('TIMEOUT', { status, requestId });
    if (error instanceof ApiError) throw error;
    throw new ApiError('NETWORK_ERROR', { status, requestId });
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', cancel);
  }
}
