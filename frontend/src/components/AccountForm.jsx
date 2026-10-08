import React, { useEffect, useRef, useState } from 'react';
import { apiRequest, ApiError } from '../lib/api';

function memberData(response) {
  if (typeof response.data?.user_id !== 'string' || typeof response.data?.display_name !== 'string'
      || !Number.isInteger(response.data?.profile?.first_boarding_buffer_seconds)) {
    throw new ApiError('INVALID_RESPONSE', { requestId: response.meta.request_id });
  }
  return response.data;
}

export default function AccountForm({ onSessionChange }) {
  const [mode, setMode] = useState('login');
  const [member, setMember] = useState(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [state, setState] = useState({ phase: 'loading' });
  const pending = useRef(null);

  async function load() {
    if (pending.current) return;
    const controller = new AbortController(); pending.current = controller;
    setState({ phase: 'loading' });
    try {
      const response = await apiRequest('/api/v1/me', { signal: controller.signal });
      if (!controller.signal.aborted) { setMember(memberData(response)); setState({ phase: 'ready' }); }
    } catch (error) {
      if (!controller.signal.aborted) {
        if (['AUTH_REQUIRED', 'SESSION_EXPIRED'].includes(error.code)) {
          setMember(null); setState({ phase: 'ready' });
        } else setState({ phase: 'error', message: error.message, requestId: error.requestId });
      }
    } finally { if (pending.current === controller) pending.current = null; }
  }
  useEffect(() => { load(); return () => { pending.current?.abort(); pending.current = null; }; }, []);

  async function submit(event, logout = false) {
    event.preventDefault();
    if (pending.current) return;
    const controller = new AbortController(); pending.current = controller;
    setState({ phase: 'loading' });
    try {
      const csrf = await apiRequest('/api/v1/auth/csrf', { signal: controller.signal });
      const endpoint = logout ? 'logout' : mode === 'register' ? 'register' : 'login';
      await apiRequest(`/api/v1/auth/${endpoint}`, {
        method: 'POST', signal: controller.signal, headers: { 'X-CSRF-Token': csrf.data.csrf_token },
        body: logout ? {} : { email, password, ...(mode === 'register' ? { display_name: name } : {}) },
      });
      if (controller.signal.aborted) return;
      setPassword('');
      if (logout) { onSessionChange?.(); setMember(null); setState({ phase: 'ready', message: '로그아웃했어요.' }); }
      else if (mode === 'register') {
        setMode('login'); setState({ phase: 'ready', message: '가입했어요. 비밀번호를 입력해 로그인해주세요.' });
      } else {
        const response = await apiRequest('/api/v1/me', { signal: controller.signal });
        if (!controller.signal.aborted) { setMember(memberData(response)); setState({ phase: 'ready' }); onSessionChange?.(); }
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        setPassword('');
        setState({ phase: 'error', message: error.message, requestId: error.requestId, fields: error.fields });
      }
    } finally { if (pending.current === controller) pending.current = null; }
  }
  const busy = state.phase === 'loading';
  return <div aria-busy={busy}>
    <div role="status" aria-live="polite">
      {busy && <p className="muted">계정을 확인하고 있어요…</p>}
      {state.message && <p id="account-feedback">{state.message}</p>}
    </div>
    {member ? <><h3>{member.display_name}님, 반가워요.</h3><p className="info-box">로그인했어요. 첫 탑승 여유는 {member.profile.first_boarding_buffer_seconds / 60}분이에요.</p><button className="secondary wide" disabled={busy} onClick={event => submit(event, true)}>로그아웃</button></> : <>
      <div className="auth-tabs"><button disabled={busy} aria-pressed={mode === 'login'} onClick={() => { setMode('login'); setPassword(''); setState({ phase: 'ready' }); }}>로그인</button><button disabled={busy} aria-pressed={mode === 'register'} onClick={() => { setMode('register'); setPassword(''); setState({ phase: 'ready' }); }}>회원가입</button></div>
      <form onSubmit={submit}>
        <label>이메일<input aria-invalid={state.fields?.includes('body.email') || undefined} aria-describedby={state.fields?.includes('body.email') ? 'account-feedback' : undefined} autoComplete="username" type="email" required maxLength={254} disabled={busy} value={email} onChange={e => setEmail(e.target.value)}/></label>
        {mode === 'register' && <label>이름<input aria-invalid={state.fields?.includes('body.display_name') || undefined} aria-describedby={state.fields?.includes('body.display_name') ? 'account-feedback' : undefined} autoComplete="nickname" required maxLength={30} disabled={busy} value={name} onChange={e => setName(e.target.value)}/></label>}
        <label>비밀번호<input aria-invalid={state.fields?.includes('body.password') || undefined} aria-describedby={state.fields?.includes('body.password') ? 'account-feedback' : undefined} autoComplete={mode === 'register' ? 'new-password' : 'current-password'} type="password" required minLength={15} maxLength={128} disabled={busy} value={password} onChange={e => setPassword(e.target.value)}/></label>
        <p className="muted small">비밀번호는 15~128자예요. 이메일 중복을 확인해 가입하며 메일 인증은 후속으로 제공할 예정이에요.</p>
        <button type="submit" className="primary wide" disabled={busy}>{mode === 'register' ? '계정 만들기' : '로그인하기'}</button>
      </form>
      {state.phase === 'error' && <button className="text-button" onClick={load}>계정 상태 다시 확인</button>}
    </>}
  </div>;
}
