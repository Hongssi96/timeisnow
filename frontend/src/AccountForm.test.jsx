import React from 'react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AccountForm from './AccountForm';
import { apiRequest, ApiError } from './api';
vi.mock('./api', async original => ({ ...await original(), apiRequest: vi.fn() }));
afterEach(() => vi.resetAllMocks());
const reply = data => ({ data, meta: { request_id: 'req_test' } });
const password = 'A test passphrase with spaces';
async function open() {
  apiRequest.mockRejectedValueOnce(new ApiError('AUTH_REQUIRED'));
  render(<AccountForm/>);
  await waitFor(() => expect(screen.getByLabelText('이메일').disabled).toBe(false));
  return userEvent.setup();
}
describe('실제 계정 폼', () => {
  it('비밀번호 검증 오류에 조건과 해당 필드를 안내한다', async () => {
    const u = await open(); await u.click(screen.getByRole('button', {name:'회원가입'}));
    await u.type(screen.getByLabelText('이메일'),'test@example.invalid');
    await u.type(screen.getByLabelText('이름'),'테스트');
    await u.type(screen.getByLabelText('비밀번호'),'passwordpassword');
    apiRequest.mockResolvedValueOnce(reply({csrf_token:'csrf_test'})).mockRejectedValueOnce(new ApiError('VALIDATION_ERROR', {fields:['body.password'],requestId:'req_validation'}));
    await u.click(screen.getByRole('button',{name:'계정 만들기'}));
    expect(await screen.findByText('비밀번호는 15~128자여야 하며, 흔한 비밀번호는 사용할 수 없어요.')).toBeTruthy();
    expect(screen.getByLabelText('비밀번호').getAttribute('aria-invalid')).toBe('true');
    expect(screen.getByLabelText('비밀번호').getAttribute('aria-describedby')).toBe('account-feedback');
    expect(screen.getByText('req_validation')).toBeTruthy();
  });
  it('StrictMode 재마운트에서도 계정 확인 로딩이 끝난다', async () => {
    apiRequest.mockRejectedValue(new ApiError('AUTH_REQUIRED'));
    render(<React.StrictMode><AccountForm/></React.StrictMode>);
    await waitFor(() => expect(screen.getByLabelText('이메일').disabled).toBe(false));
    expect(apiRequest.mock.calls.length).toBe(2);
  });
  it('가입 후 자동 로그인하지 않고 로그인으로 전환한다', async () => {
    const u = await open(); await u.click(screen.getByRole('button', { name: '회원가입' }));
    await u.type(screen.getByLabelText('이메일'), 'member@example.invalid');
    await u.type(screen.getByLabelText('이름'), '테스트');
    await u.type(screen.getByLabelText('비밀번호'), password);
    apiRequest.mockResolvedValueOnce(reply({ csrf_token: 'csrf_test' })).mockResolvedValueOnce(reply({ user_id: 'u_test' }));
    await u.click(screen.getByRole('button', { name: '계정 만들기' }));
    expect(await screen.findByText('가입했어요. 비밀번호를 입력해 로그인해주세요.')).toBeTruthy();
    expect(screen.getByLabelText('비밀번호').value).toBe('');
    expect(screen.getByRole('button', { name: '로그인하기' })).toBeTruthy();
    expect(apiRequest.mock.calls[2][1].headers['X-CSRF-Token']).toBe('csrf_test');
  });
  it('중복 가입 오류와 요청 ID를 표시한다', async () => {
    const u=await open(); await u.click(screen.getByRole('button', { name: '회원가입' }));
    await u.type(screen.getByLabelText('이메일'),'member@example.invalid');
    await u.type(screen.getByLabelText('이름'),'테스트');
    await u.type(screen.getByLabelText('비밀번호'),password);
    apiRequest.mockResolvedValueOnce(reply({ csrf_token: 'csrf_test' })).mockRejectedValueOnce(new ApiError('EMAIL_UNAVAILABLE',{requestId:'req_duplicate'}));
    await u.click(screen.getByRole('button', { name:'계정 만들기' }));
    expect(await screen.findByText('이미 가입된 이메일이에요. 로그인해주세요.')).toBeTruthy();
    expect(screen.getByText('req_duplicate')).toBeTruthy();
  });
  it('로그인과 로그아웃을 연결한다', async () => {
    const u=await open(); await u.type(screen.getByLabelText('이메일'),'member@example.invalid');
    await u.type(screen.getByLabelText('비밀번호'),password);
    apiRequest.mockResolvedValueOnce(reply({csrf_token:'csrf_test'})).mockResolvedValueOnce(reply({user_id:'u_test'})).mockResolvedValueOnce(reply({user_id:'u_test',display_name:'테스트',profile:{first_boarding_buffer_seconds:300}}));
    await u.click(screen.getByRole('button',{name:'로그인하기'}));
    expect(await screen.findByText('테스트님, 반가워요.')).toBeTruthy();
    apiRequest.mockResolvedValueOnce(reply({csrf_token:'csrf_new'})).mockResolvedValueOnce(reply(null));
    await u.click(screen.getByRole('button',{name:'로그아웃'}));
    expect(await screen.findByText('로그아웃했어요.')).toBeTruthy();
  });
  it('연결 실패 후 계정 상태를 다시 확인한다', async () => {
    apiRequest.mockRejectedValueOnce(new ApiError('NETWORK_ERROR'));
    render(<AccountForm/>); const u=userEvent.setup();
    expect(await screen.findByText(/서버에 연결할 수 없어요/)).toBeTruthy();
    apiRequest.mockRejectedValueOnce(new ApiError('AUTH_REQUIRED'));
    await u.click(screen.getByRole('button',{name:'계정 상태 다시 확인'}));
    await waitFor(() => expect(screen.queryByText(/서버에 연결할 수 없어요/)).toBeNull());
  });
});
