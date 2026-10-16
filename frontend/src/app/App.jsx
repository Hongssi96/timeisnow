import RoutineDeparture from '../components/RoutineDeparture';
import React, { useState, useRef, useEffect } from 'react';

import { ArrowUpRight, ArrowRight, Home, Repeat2, History, SlidersHorizontal, Footprints, X, Check, Clock3, ChevronRight, CircleHelp, Navigation, Leaf, Sun, RefreshCw, LogIn } from 'lucide-react';
import '../styles/styles.css';
import { apiRequest, ApiError, isServerTime } from '../lib/api';
import AccountForm from '../components/AccountForm';
import PlacesCard from '../components/PlacesCard';
import PersonalizationCard from '../components/PersonalizationCard';
import TripRecords from '../components/TripRecords';
import OriginSelector from '../components/OriginSelector';
import JourneyComparison from '../components/JourneyComparison';
import RoutinesPanel, { RoutineSummary, RoutineStatus } from '../components/RoutinesPanel';
import { useRoutines, needsRoutineRecovery } from '../lib/routines';

const log = (event, requestId) => { if (import.meta.env.DEV) console.info(JSON.stringify({ timestamp: new Date().toISOString(), event, mode: 'ui_demo', ...(requestId ? { request_id: requestId } : {}) })); };
export default function App() {
  const [page, setPage] = useState('home');
  const [revision, setRevision] = useState(0);
  const { state: routineState, load: loadRoutines, clear: clearRoutines } = useRoutines(['home','routines'].includes(page), revision);
  const routines = routineState.items;
  const [routineToReplace, setRoutineToReplace] = useState(null);
  const [selected, setSelected] = useState(null);
  const [buffer, setBuffer] = useState(5);
  const [modal, setModal] = useState(null);
  const [toast, setToast] = useState('');


  const [origin, setOrigin] = useState(null);
  const [originExpired, setOriginExpired] = useState(false);
  useEffect(() => { if (modal === 'account') { setOrigin(null); setOriginExpired(false); } }, [modal]);
  useEffect(() => {
    if (!origin) return;
    const timer = setTimeout(() => setOriginExpired(true), Math.max(0, origin.deadline - Date.now()));
    return () => clearTimeout(timer);
  }, [origin]);
  const routine = routines.find(r => r.routine_id === selected) || routines[0];
  function accountChanged() { clearRoutines(); setSelected(null); setRoutineToReplace(null); setRevision(value => value + 1); }
  function refreshRoutines() { setRevision(value => value + 1); }
  function changeRoute(value) { setRoutineToReplace(value); navigate('journeys'); }
  function addRoutine() { setRoutineToReplace(null); navigate('journeys'); }
  function savedRoutine(data) { setSelected(data.routine_id); if(routineToReplace)navigate('home'); setRoutineToReplace(null); refreshRoutines(); notify(`${data.name} 루틴을 저장했어요.`); }
  const notify = (message) => setToast(message);
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(''), 4000); return () => clearTimeout(t); }, [toast]);
  function navigate(next) { setPage(next); log('ui.navigation'); window.scrollTo({ top: 0, behavior: 'smooth' }); }
  const navItems = [['home', Home, '오늘의 출발'], ['routines', Repeat2, '내 루틴'], ['history', History, '이동 기록'], ['settings', SlidersHorizontal, '내 설정']];
  return <div className="app">
    <aside className="sidebar">
      <a href="#" className="brand" onClick={e => { e.preventDefault(); navigate('home'); }}><span className="brand-icon"><Clock3 size={25}/></span>지금이니<span className="brand-q">?</span></a>
      <p className="brand-caption">여유 있게, 딱 맞게.</p>
      <div className="nav-label">MY EVERYDAY</div>
      <nav aria-label="주 메뉴">{navItems.map(([key,Icon,label]) => <button key={key} className={'nav-item '+(page===key?'active':'')} aria-current={page===key?'page':undefined} onClick={() => navigate(key)}><Icon size={20}/><span>{label}</span>{page===key&&<span className="active-dot"/>}</button>)}</nav>
      <div className="sidebar-note"><Leaf size={25}/><h3>기다림은 편안한 곳에서.</h3><p>매일 걷던 그 길,<br/>이제 시간을 맞춰 나가요.</p></div>
      <button className="profile" onClick={() => { clearRoutines(); setSelected(null); setModal('account'); }}><span className="avatar">나</span><span><strong>나의 하루</strong><small>회원가입 · 로그인</small></span><ChevronRight size={17}/></button>
    </aside>
    <div className="workspace">
      <header className="topbar"><span className="breadcrumb">나의 일상 <ChevronRight size={14}/> {page==='journeys'?'경로 후보 비교':navItems.find(n=>n[0]===page)?.[2]}</span><span className="preview-label"><span/> {['home','routines','journeys'].includes(page)?'저장한 루틴 · 경로 예상값':page==='history'?'본인 이동 기록 · 직접 확인':'설정 · 본인 저장 정보'}</span><button className="icon-button" aria-label="미리보기 도움말" onClick={() => setModal('help')}><CircleHelp size={20}/></button></header>
      <main id="main">
        {page === 'home' && <>
          <div className="page-heading"><div><p className="eyebrow">YOUR DAILY DEPARTURE</p><h1>오늘도, 여유 있게 출발해요<span>.</span></h1><p>밖에서 기다리는 시간 대신, 집에서 조금 더 편안하게.</p></div><div className="morning"><Sun size={23}/><span>좋은 아침이에요</span></div></div>
          <div className="routine-toolbar"><div className="tabs" aria-label="출발 루틴">{routines.map(item => <button key={item.routine_id} className={routine?.routine_id === item.routine_id ? 'selected' : ''} aria-pressed={routine?.routine_id === item.routine_id} onClick={() => { setSelected(item.routine_id); setOrigin(null); setOriginExpired(false); }}>{item.name}</button>)}</div><button className="text-button" onClick={()=>setModal('location')}><Navigation size={16}/> 다른 곳에서 출발 <ArrowUpRight size={15}/></button></div>
          <button className="secondary comparison-entry" onClick={addRoutine}><Navigation size={17}/>경로 후보 비교 <ArrowRight size={17}/></button>
          {origin ? <section className="card origin-summary" aria-live="polite"><span className="soft-icon"><Navigation size={24}/></span>
            <h2>{originExpired ? '출발지를 다시 확인해주세요' : `${origin.label}에서 출발 준비`}</h2><p>{origin.location_address}</p>
            {origin.origin.type === 'current_location' && <p className="small muted">측정 시각 {new Date(origin.origin.captured_at).toLocaleTimeString('ko-KR')} · 측정 정확도 약 {Math.round(origin.origin.accuracy_meters)}m · 위치 직접 확인 · GPS 품질 자동 판정 보류</p>}
            <div className="info-box">{originExpired ? '출발지 선택이 만료됐어요. 다시 선택해주세요.' : '출발지를 확인했어요. 경로 후보를 비교할 수 있으며 출발 시간 안내는 준비 중이에요.'}</div>
            <div className="button-row"><button className="primary" onClick={()=>setModal('location')}>출발지 다시 선택</button><button className="secondary" onClick={()=>{setOrigin(null);setOriginExpired(false);}}>저장한 루틴으로 돌아가기</button></div>
          </section> : <>
            <RoutineStatus state={routineState} onRetry={()=>loadRoutines()} onLogin={()=>setModal('account')} onAdd={addRoutine}/>
            {routine && <section className="card routine-home"><div className="section-heading"><h2>{routine.name}</h2><span className="tag">저장한 루틴</span></div><RoutineSummary routine={routine}/>{!modal&&<RoutineDeparture key={routine.routine_id+":"+routine.version} routine={routine} onRouteChange={changeRoute}/>}<div className="button-row"><button className="primary" onClick={()=>navigate('routines')}>내 루틴 관리 <ArrowRight size={16}/></button><button className="secondary" onClick={()=>changeRoute(routine)}>{needsRoutineRecovery(routine)?'루틴 복구하기':'경로 다시 선택'}</button></div></section>}
            {routineState.next && <button className="secondary" disabled={routineState.phase==='more'} onClick={()=>loadRoutines(true)}>루틴 더 보기</button>}
          </>}
        </>}
        {page==='routines'&&<><PageHeading eyebrow="MY ROUTINES" title="매일 가는 길을 기억해요." description="한 번 저장한 경로로, 내일 아침은 조금 더 간단하게."/><RoutinesPanel state={routineState} onRetry={()=>loadRoutines()} onMore={()=>loadRoutines(true)} onLogin={()=>setModal('account')} onAdd={addRoutine} onSelect={value=>{setSelected(value.routine_id);setOrigin(null);setOriginExpired(false);navigate('home');}} onRouteChange={changeRoute} onChanged={message=>{refreshRoutines();notify(message);}} onAuthError={()=>{clearRoutines();setSelected(null);}}/></>}
        {page==='history'&&<><PageHeading eyebrow="MY JOURNEYS" title="내 걸음이 쌓이는 곳." description="이동 기록을 확인하고 잘못된 입력을 바로잡아요."/>{modal!=='account'&&<TripRecords onLogin={()=>setModal('account')}/>}</>}
        {page==='journeys'&&<JourneyComparison initialOrigin={originExpired?null:origin} onBack={()=>navigate('home')} onLogin={()=>setModal('account')} onAuthError={()=>{setOrigin(null);setOriginExpired(false);clearRoutines();setSelected(null);setRoutineToReplace(null);}} routineToReplace={routineToReplace} onRoutineSaved={savedRoutine} onRoutineReload={()=>{setRoutineToReplace(null);refreshRoutines();navigate('routines');}}/>}
        {page==='settings'&&<><PageHeading eyebrow="MADE FOR YOU" title="나에게 맞는 작은 설정." description="익숙한 장소와 편안한 여유를 기억해둘게요."/><div className="settings-grid">{modal!=='account'&&<PlacesCard onLogin={()=>setModal('account')}/>}<section className="card"><h2>첫 탑승 여유</h2><p className="muted">정류장에 얼마나 여유 있게 도착할까요?</p><div className="buffer-control"><button aria-label="여유 1분 줄이기" disabled={buffer<=1} onClick={()=>setBuffer(b=>b-1)}>−</button><strong>{buffer}<small>분</small></strong><button aria-label="여유 1분 늘리기" disabled={buffer>=10} onClick={()=>setBuffer(b=>b+1)}>+</button></div><p className="small muted">처음에는 5분으로 시작해요.<br/>내 걸음을 학습해도 여유는 자동으로 줄이지 않아요.</p><p className="small">화면 체험 범위: 1~10분 · 서버 저장 전</p></section>{modal!=='account'&&<PersonalizationCard/>}<section className="card"><h2>계정과 알림</h2><button className="place-row" onClick={()=>{clearRoutines();setSelected(null);setModal('account');}}><LogIn size={20}/><span>회원가입 · 로그인</span><ChevronRight size={18}/></button><p className="muted small">백그라운드 출발 알림은 아직 제공하지 않아요. 이 화면을 닫으면 알림이 오지 않습니다.</p></section><section className="card"><h2>서버 연결</h2><p className="muted small">이 화면이 백엔드 서버와 통신되는지 확인해요. 화면 체험용 예시와는 별개예요.</p><ServerCheck/></section></div></>}
        <footer><span>지금이니? <span className="footer-dot">·</span> 기다림을 줄이는 작은 습관</span><span>{page==='journeys'?'경로와 첫 승차 출발은 공급자 근거에 따른 추정입니다.':'첫 승차 출발은 추정 안내이며 이동 기록은 본인 신고입니다.'}</span></footer>
      </main>
    </div>
    <nav className="mobile-nav" aria-label="모바일 메뉴">{navItems.map(([key,Icon,label])=><button key={key} className={page===key?'active':''} aria-current={page===key?'page':undefined} onClick={()=>navigate(key)}><Icon size={21}/><span>{label}</span></button>)}</nav>
    {toast&&<div className="toast" role="status"><Check size={18}/>{toast}</div>}
    {modal&&<Modal title={({route:'오늘의 경로',location:'출발 장소 확인',help:'화면 미리보기 안내',account:'나의 일상을 기억하려면'})[modal]} onClose={()=>{if(modal==='account')refreshRoutines();setModal(null);}}>
      {modal==='location'?<OriginSelector onSelect={value=>{setOrigin(value);setOriginExpired(false);setModal(null);navigate('home');}} onLogin={()=>setModal('account')} onAuthError={()=>{setOrigin(null);setOriginExpired(false);clearRoutines();setSelected(null);setRoutineToReplace(null);}}/>:
      modal==='account'?<AccountForm onSessionChange={accountChanged}/>:
      <><p>디자인과 화면 흐름을 확인하는 React 프로토타입이에요.</p><ul className="help-list"><li>루틴을 선택하면 최신 경로와 첫 승차 예상 출발을 확인해요. 미지원·근거 부족이면 안내가 제한돼요.</li><li>루틴은 계정에 저장돼요. 설정의 여유 시간은 아직 화면에서만 바뀌어요.</li><li>계정·장소 선택·카카오 경로 비교는 실제 API를 사용해요. 검증된 개인 도보·목표 도착 안내는 준비 중이며 지원 경기 버스의 도착·첫 출발은 추정으로 표시해요.</li><li>삭제된 장소를 참조하는 루틴은 경로를 다시 선택해주세요.</li></ul></>}
    </Modal>}
  </div>;
}
function PageHeading({eyebrow,title,description}) {return <div className="page-heading"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p>{description}</p></div></div>;}
function ServerCheck() {
  const [state, setState] = useState({ phase: 'idle' });
  const pending = useRef(null);
  useEffect(() => () => pending.current?.abort(), []);
  async function check() {
    if (pending.current) return;
    const controller = new AbortController();
    pending.current = controller;
    setState({ phase: 'loading' });
    try {
      const body = await apiRequest('/api/v1/health', { signal: controller.signal });
      if (body.data?.status !== 'ok' || !isServerTime(body.data.server_time)) {
        throw new ApiError('INVALID_RESPONSE', { status: body.status, requestId: body.meta.request_id });
      }
      if (controller.signal.aborted) return;
      setState({ phase: 'ok', serverTime: body.data.server_time, requestId: body.meta.request_id });
      log('ui.server.check.completed', body.meta.request_id);
    } catch (error) {
      if (controller.signal.aborted) return;
      const failure = error instanceof ApiError ? error : new ApiError('INVALID_RESPONSE');
      setState({ phase: 'error', message: failure.message, requestId: failure.requestId });
      log('ui.server.check.failed', failure.requestId);
    } finally {
      if (pending.current === controller) pending.current = null;
    }
  }
  const checkedAt = state.phase === 'ok' ? new Date(state.serverTime).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : null;
  return <div role="status" aria-live="polite" aria-busy={state.phase === 'loading'}>
    {state.phase === 'idle' && <p className="muted small">아직 확인하지 않았어요.</p>}
    {state.phase === 'loading' && <p className="pill"><span className="dot"/>서버에 연결하는 중…</p>}
    {state.phase === 'ok' && <p className="pill"><span className="dot"/>연결됨 · 확인 시각 {checkedAt}</p>}
    {state.phase === 'error' && <p className="muted small">{state.message}</p>}
    <button className="secondary" onClick={check} disabled={state.phase === 'loading'}>{state.phase === 'error' ? '다시 확인하기' : '서버 연결 확인'} <RefreshCw size={15}/></button>
    {state.requestId && <p className="muted small request-id">문의용 요청 ID: <code>{state.requestId}</code></p>}
  </div>;
}
function Modal({title,onClose,children}) {
  const ref=useRef(null);
  useEffect(()=>{const node=ref.current;node.showModal(); return()=>node.close();},[]);
  return <dialog ref={ref} className="modal" onCancel={e=>{e.preventDefault();onClose();}} onClick={e=>{if(e.target===ref.current)onClose();}}><div className="modal-heading"><h2>{title}</h2><button className="icon-button" aria-label="닫기" onClick={onClose}><X size={22}/></button></div>{children}</dialog>;
}
