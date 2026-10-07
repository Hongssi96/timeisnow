import React, { useState, useRef, useEffect } from 'react';

import { ArrowUpRight, ArrowRight, ArrowLeft, Home, Repeat2, History, SlidersHorizontal, MapPin, BusFront, Footprints, TrainFront, Plus, X, Check, Clock3, ChevronRight, CircleHelp, Navigation, Leaf, Coffee, Sun, RefreshCw, LogIn, ShieldCheck } from 'lucide-react';
import '../styles/styles.css';
import { apiRequest, ApiError, isServerTime } from '../lib/api';
import AccountForm from '../components/AccountForm';
import PlacesCard from '../components/PlacesCard';
import OriginSelector from '../components/OriginSelector';
import JourneyComparison from '../components/JourneyComparison';

// 이동 체험은 합성 데이터. 계정·장소·경로 비교는 실제 API를 사용합니다.
const initialRoutines = [
  { id: 'work', name: '평일 출근', origin: '집', destination: '회사', time: '09:00', days: ['월','화','수','목','금'], bus: '143', transfer: false },
  { id: 'school', name: '학교 가는 길', origin: '집', destination: '학교', time: '09:00', days: ['월','화','수','목','금'], bus: '721', transfer: true },
];
const log = (event, requestId) => { if (import.meta.env.DEV) console.info(JSON.stringify({ timestamp: new Date().toISOString(), event, mode: 'ui_demo', ...(requestId ? { request_id: requestId } : {}) })); };
export default function App() {
  const [page, setPage] = useState('home');
  const [routines, setRoutines] = useState(initialRoutines);
  const [selected, setSelected] = useState('work');
  const [buffer, setBuffer] = useState(5);
  const [modal, setModal] = useState(null);
  const [toast, setToast] = useState('');
  const [trip, setTrip] = useState(null);
  const [history, setHistory] = useState([]);
  const [scenario, setScenario] = useState('ready');
  const [origin, setOrigin] = useState(null);
  const [originExpired, setOriginExpired] = useState(false);
  useEffect(() => { if (modal === 'account') { setOrigin(null); setOriginExpired(false); } }, [modal]);
  useEffect(() => {
    if (!origin) return;
    const timer = setTimeout(() => setOriginExpired(true), Math.max(0, origin.deadline - Date.now()));
    return () => clearTimeout(timer);
  }, [origin]);
  const routine = routines.find(r => r.id === selected) || routines[0];
  const busMinutes = scenario === 'next' ? 20 : 13;
  const waitMinutes = busMinutes - 5 - buffer;
  const notify = (message) => setToast(message);
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(''), 4000); return () => clearTimeout(t); }, [toast]);
  function navigate(next) { setPage(next); log('ui.navigation'); window.scrollTo({ top: 0, behavior: 'smooth' }); }
  function startTrip() { if (origin) return; setTrip({ routine: { ...routine }, stage: 0, events: [{ type: 'departed', at: new Date().toISOString() }], slack: busMinutes - 5 }); navigate('trip'); log('ui.trip.started'); }
  function advanceTrip() {
    const last = trip.routine.transfer ? 6 : 3;
    if (trip.stage === last) {
      setHistory(h => [{ id: Date.now(), name: trip.routine.name, time: new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }), events: trip.events.length, outcome: '이동 완료' }, ...h]);
      setTrip(null); navigate('history'); notify('화면 체험 기록을 남겼어요. 실제 학습에는 사용하지 않아요.'); return;
    }
    const eventTypes = trip.routine.transfer ? ['approach_arrived','boarded','alighted','approach_arrived','boarded','alighted'] : ['approach_arrived','boarded','alighted'];
    setTrip(t => ({ ...t, stage: t.stage + 1, events: [...t.events, { type: eventTypes[t.stage], at: new Date().toISOString() }] })); log('ui.trip.event');
  }
  const navItems = [['home', Home, '오늘의 출발'], ['routines', Repeat2, '내 루틴'], ['history', History, '이동 기록'], ['settings', SlidersHorizontal, '내 설정']];
  return <div className="app">
    <aside className="sidebar">
      <a href="#" className="brand" onClick={e => { e.preventDefault(); navigate('home'); }}><span className="brand-icon"><Clock3 size={25}/></span>지금이니<span className="brand-q">?</span></a>
      <p className="brand-caption">여유 있게, 딱 맞게.</p>
      <div className="nav-label">MY EVERYDAY</div>
      <nav aria-label="주 메뉴">{navItems.map(([key,Icon,label]) => <button key={key} className={'nav-item '+(page===key?'active':'')} aria-current={page===key?'page':undefined} onClick={() => navigate(key)}><Icon size={20}/><span>{label}</span>{page===key&&<span className="active-dot"/>}</button>)}</nav>
      {trip && <button className="trip-return" onClick={() => navigate('trip')}><Navigation size={18}/> 이동 중 화면으로 <ArrowRight size={16}/></button>}
      <div className="sidebar-note"><Leaf size={25}/><h3>기다림은 편안한 곳에서.</h3><p>매일 걷던 그 길,<br/>이제 시간을 맞춰 나가요.</p></div>
      <button className="profile" onClick={() => setModal('account')}><span className="avatar">나</span><span><strong>나의 하루</strong><small>회원가입 · 로그인</small></span><ChevronRight size={17}/></button>
    </aside>
    <div className="workspace">
      <header className="topbar"><span className="breadcrumb">나의 일상 <ChevronRight size={14}/> {page==='trip'?'이동 중':page==='journeys'?'경로 후보 비교':navItems.find(n=>n[0]===page)?.[2]}</span><span className="preview-label"><span/> {page==='journeys'?'실제 경로 후보 · 예상값':'화면 미리보기 · 예시 데이터'}</span><button className="icon-button" aria-label="미리보기 도움말" onClick={() => setModal('help')}><CircleHelp size={20}/></button></header>
      <main id="main">{trip && page !== 'trip' && <button className="mobile-trip-return" onClick={() => navigate('trip')}><Navigation size={17}/> 진행 중인 이동으로 돌아가기 <ArrowRight size={16}/></button>}
        {page === 'home' && <>
          <div className="page-heading"><div><p className="eyebrow">YOUR DAILY DEPARTURE</p><h1>오늘도, 여유 있게 출발해요<span>.</span></h1><p>밖에서 기다리는 시간 대신, 집에서 조금 더 편안하게.</p></div><div className="morning"><Sun size={23}/><span>좋은 아침이에요</span></div></div>
          <div className="routine-toolbar"><div className="tabs" aria-label="출발 루틴">{routines.map(r=><button key={r.id} className={selected===r.id?'selected':''} onClick={()=>{setSelected(r.id);setScenario('ready');}}><span>{r.transfer?'학교':'출근'}</span> {r.name}</button>)}</div><button className="text-button" onClick={()=>setModal('location')}><Navigation size={16}/> 다른 곳에서 출발 <ArrowUpRight size={15}/></button></div>
          <button className="secondary comparison-entry" onClick={()=>navigate('journeys')}><Navigation size={17}/>경로 후보 비교 <ArrowRight size={17}/></button>
          {origin ? <section className="card origin-summary" aria-live="polite"><span className="soft-icon"><Navigation size={24}/></span>
            <h2>{originExpired ? '출발지를 다시 확인해주세요' : `${origin.label}에서 출발 준비`}</h2><p>{origin.location_address}</p>
            {origin.origin.type === 'current_location' && <p className="small muted">측정 시각 {new Date(origin.origin.captured_at).toLocaleTimeString('ko-KR')} · 측정 정확도 약 {Math.round(origin.origin.accuracy_meters)}m · 위치 직접 확인 · GPS 품질 자동 판정 보류</p>}
            <div className="info-box">{originExpired ? '출발지 선택이 만료됐어요. 다시 선택해주세요.' : '출발지를 확인했어요. 경로 후보를 비교할 수 있으며 출발 시간 안내는 준비 중이에요.'}</div>
            <div className="button-row"><button className="primary" onClick={()=>setModal('location')}>출발지 다시 선택</button><button className="secondary" onClick={()=>{setOrigin(null);setOriginExpired(false);}}>예시 화면으로 돌아가기</button></div>
          </section> : <><div className="home-grid"><div className="primary-column">
            <section className={'departure-card '+(scenario==='stale'?'stale':'')}>
              <div className="hero-top"><span className="pill"><span className="dot"/>{scenario==='stale'?'정보 확인이 필요해요':'아직 집에서 기다려도 돼요'}</span><span className="hero-routine">{routine.name} · 예시</span></div>
              <div className="hero-center"><div><p className="hero-label">{scenario==='stale'?'출발 안내를 잠시 멈췄어요':'권장 출발까지'}</p><h2>{scenario==='stale'?<span className="stale-title">다시 확인할게요</span>:<><strong>{waitMinutes}</strong><span>분 뒤 출발</span></>}</h2><p className="hero-sub">{scenario==='stale'?'오래된 정보로 출발 시간을 안내하지 않아요.':'서두르지 않아도 괜찮아요.'}</p></div><div className="clock-art" aria-hidden="true"><div className="orbit-dot"/><div className="clock-face"><i className="tick t1"/><i className="tick t2"/><i className="tick t3"/><i className="tick t4"/><div className="hand hour"/><div className="hand minute"/><b/></div><div className="clock-leaf"><Leaf size={23}/></div></div></div>
              <div className="slack-message"><ShieldCheck size={21}/><p>{scenario==='stale'?'현재 여유 시간을 확인할 수 없어요.':<>그때 출발하면 정류장 도착 후 <strong>약 {buffer}분의 여유</strong>가 있어요.</>}</p></div>
              <div className="hero-metrics"><div><Footprints size={20}/><span>정류장까지<strong>도보 5분</strong></span></div><div><BusFront size={20}/><span>버스 도착<strong>{scenario==='stale'?'확인 필요':`약 ${busMinutes}분 후`}</strong></span></div><div><Clock3 size={20}/><span>첫 탑승 여유<strong>{buffer}분 설정</strong></span></div></div>
              <button className="primary start-button" onClick={scenario==='stale'?()=>{setScenario('ready');notify('정상 안내 예시로 전환했어요.');}:startTrip}>{scenario==='stale'?'안내 다시 확인하기':'지금 출발할게요'}<ArrowRight size={20}/></button><p className="hero-footnote">{scenario==='stale'?'버튼을 누르면 정상 화면 예시로 돌아갑니다.':`지금 출발하면 예상 여유는 ${busMinutes-5}분이에요.`}</p>
            </section>
            <section className="card journey-card"><div className="section-heading"><h2>오늘의 이동 경로</h2><button className="text-button" onClick={()=>setModal('route')}>자세히 보기 <ChevronRight size={15}/></button></div><div className="journey-summary"><strong>{routine.origin} <ArrowRight size={17}/> {routine.destination}</strong><span>약 {(routine.transfer?42:27)+buffer}분 · 환승 {routine.transfer?1:0}회</span></div><div className="route-bar"><span className="walk-segment">도보 5분</span><span className="bus-segment"><BusFront size={16}/>{routine.bus}번 · 17분</span>{routine.transfer&&<span className="train-segment">2호선 · 10분</span>}<span className="walk-segment">도보 5분</span></div><div className="route-endpoints"><span><span className="tiny-dot"/> 집 출입구</span><span>{routine.destination} 도착 <MapPin size={13}/></span></div><p className="muted small">정류장 대기 {buffer}분 포함{routine.transfer?' · 환승 구간은 상세 화면에서 확인해요.': ' · 저장된 도보 시간을 사용해요.'}</p></section>
          </div><aside className="secondary-column">
            <section className="card bus-card"><div className="section-heading"><h2>탈 버스, 한눈에</h2><span className="tag">예시</span></div><div className="stop-name"><MapPin size={18}/><div><strong>우리집 앞 정류장</strong><p>회사 방면 · 가상 정류장</p></div></div><div className="bus-arrival"><span className="bus-number"><BusFront size={18}/>{routine.bus}</span><strong>{scenario==='stale'?'—':busMinutes}<small>분 후</small></strong></div><div className="next-bus"><span>다음 버스</span><span>약 {scenario==='next'?27:20}분 후</span></div><div className="bus-note"><Clock3 size={14}/> 실시간 정보 연동 전입니다.</div></section>
            <section className="comfort-card"><div className="coffee-icon"><Coffee size={28}/></div><p className="eyebrow">A LITTLE MORE TIME</p><h2>한 모금 더,<br/>마음은 느긋하게.</h2><p>출발 시간은 확인했으니,<br/>남은 시간은 나를 위해 써요.</p><span className="comfort-line"/></section>
            <section className="learning-note"><span className="soft-icon"><Footprints size={20}/></span><div><strong>내 걸음에 맞춰가는 중</strong><p>정확한 이동 기록 5개부터<br/>나에게 맞는 시간을 찾아요.</p></div></section>
          </aside></div>
          <div className="demo-controls"><span>화면 상태 확인</span><button onClick={()=>setScenario('ready')}>기본 안내</button><button onClick={()=>setScenario('next')}>다음 버스</button><button onClick={()=>setScenario('stale')}>정보 만료</button></div></>}
        </>}
        {page==='routines'&&<><PageHeading eyebrow="MY ROUTINES" title="매일 가는 길을 기억해요." description="한 번 저장한 경로로, 내일 아침은 조금 더 간단하게."/><div className="section-heading"><h2>저장한 루틴 <span className="count">{routines.length}</span></h2><button className="primary compact" onClick={()=>setModal({type:'routine'})}><Plus size={17}/> 루틴 추가</button></div><div className="routine-grid">{routines.map(r=><section className="card routine-card" key={r.id}><span className="soft-icon"><Repeat2/></span><h2>{r.name}</h2><p>{r.origin} → {r.destination}</p><div className="day-list">{['월','화','수','목','금','토','일'].map(d=><span key={d} className={r.days.includes(d)?'on':''}>{d}</span>)}</div><div className="routine-details"><span>목표 도착 <strong>{r.time}</strong></span><span>환승 <strong>{r.transfer?1:0}회</strong></span></div><div className="button-row"><button className="secondary" onClick={()=>setModal({type:'routine',routine:r})}>수정</button><button className="primary" onClick={()=>{setSelected(r.id);setScenario('ready');navigate('home');}}>출발 확인 <ArrowRight size={16}/></button></div></section>)}</div><p className="muted small">루틴 변경은 이 미리보기에서만 유지돼요. 새로고침하면 초기화됩니다.</p></>}
        {page==='trip'&&trip&&<><PageHeading eyebrow="ON YOUR WAY" title={trip.stage===0?'천천히, 이제 출발해볼까요?':'잘 가고 있어요.'} description="도착과 탑승을 구분해서 알려주면 내 이동 시간을 더 잘 알 수 있어요."/><section className="card trip-card"><div className="section-heading"><h2>{trip.routine.name}</h2><span className="tag">이동 체험</span></div><div className="trip-banner"><Navigation size={22}/><strong>{trip.stage===0?`지금 출발 기준 예상 여유 ${trip.slack}분`:'현재 위치·교통 정보는 연동 전이에요'}</strong></div><ol className="timeline">{(trip.routine.transfer?['집에서 출발','버스 정류장 도착','버스 탑승','환승 정류장에서 하차','지하철 승강장 도착','지하철 탑승','목적지 역에서 하차','목적지 도착']:['집에서 출발','버스 정류장 도착','버스 탑승','목적지 정류장에서 하차','목적지 도착']).map((label,i)=><li key={label} className={i<=trip.stage?'done':''}><span>{i<=trip.stage?<Check size={15}/>:i+1}</span><div><strong>{label}</strong><p>{i===trip.stage?'현재 단계':i<trip.stage?'확인 완료':'아직 확인하지 않았어요'}</p></div></li>)}</ol><button className="primary wide" onClick={advanceTrip}>{(trip.routine.transfer?['정류장에 도착했어요','버스를 탔어요','환승 정류장에서 내렸어요','승강장에 도착했어요','지하철을 탔어요','목적지 역에서 내렸어요','목적지에 도착했어요']:['정류장에 도착했어요','버스를 탔어요','목적지 정류장에서 내렸어요','목적지에 도착했어요'])[trip.stage]}<Check size={18}/></button><button className="text-button cancel" onClick={()=>{setTrip(null);setScenario('next');navigate('home');notify('다음 버스 안내 예시로 돌아왔어요.');}}>이동 취소 / 버스를 놓쳤어요</button></section></>}
        {page==='history'&&<><PageHeading eyebrow="MY JOURNEYS" title="내 걸음이 쌓이는 곳." description="실제 이동과 기다린 시간을 나누어, 더 잘 맞는 출발을 준비해요."/><div className="card history-summary"><span className="soft-icon"><Footprints size={26}/></span><div><h2>{history.length}번의 화면 체험</h2><p>실제 관측 데이터가 없어 개인화 학습은 시작하지 않았어요.</p></div></div>{history.length?history.map(h=><div className="card history-row" key={h.id}><span className="soft-icon"><Check size={20}/></span><div><h3>{h.name}</h3><p>{h.time} · {h.events}개 이벤트 · 체험 기록</p></div><span className="tag">{h.outcome}</span></div>):<div className="empty-state"><History size={38}/><h2>첫 번째 이동을 기다리고 있어요</h2><p>홈에서 출발하고 도착·탑승을 확인해보세요.</p><button className="primary" onClick={()=>navigate('home')}>출발 화면으로 <ArrowRight size={18}/></button></div>}</>}
        {page==='journeys'&&modal!=='account'&&<JourneyComparison initialOrigin={originExpired?null:origin} onBack={()=>navigate('home')} onLogin={()=>setModal('account')} onAuthError={()=>{setOrigin(null);setOriginExpired(false);}}/>}
        {page==='settings'&&<><PageHeading eyebrow="MADE FOR YOU" title="나에게 맞는 작은 설정." description="익숙한 장소와 편안한 여유를 기억해둘게요."/><div className="settings-grid">{modal!=='account'&&<PlacesCard onLogin={()=>setModal('account')}/>}<section className="card"><h2>첫 탑승 여유</h2><p className="muted">정류장에 얼마나 여유 있게 도착할까요?</p><div className="buffer-control"><button aria-label="여유 1분 줄이기" disabled={buffer<=1} onClick={()=>setBuffer(b=>b-1)}>−</button><strong>{buffer}<small>분</small></strong><button aria-label="여유 1분 늘리기" disabled={buffer>=10} onClick={()=>setBuffer(b=>b+1)}>+</button></div><p className="small muted">처음에는 5분으로 시작해요.<br/>내 걸음을 학습해도 여유는 자동으로 줄이지 않아요.</p><p className="small">화면 체험 범위: 1~10분 · 서버 저장 전</p></section><section className="card"><h2>내 걸음 학습</h2><div className="progress-track"><span/></div><p>실제 유효 기록 <strong>0 / 5개</strong></p><p className="muted small">도착 시각과 탑승 시각을 따로 기록해요. 버스를 기다린 시간은 걷는 시간에 포함하지 않아요.</p></section><section className="card"><h2>계정과 알림</h2><button className="place-row" onClick={()=>setModal('account')}><LogIn size={20}/><span>회원가입 · 로그인</span><ChevronRight size={18}/></button><p className="muted small">백그라운드 출발 알림은 아직 제공하지 않아요. 이 화면을 닫으면 알림이 오지 않습니다.</p></section><section className="card"><h2>서버 연결</h2><p className="muted small">이 화면이 백엔드 서버와 통신되는지 확인해요. 화면 체험용 예시와는 별개예요.</p><ServerCheck/></section></div></>}
        <footer><span>지금이니? <span className="footer-dot">·</span> 기다림을 줄이는 작은 습관</span><span>{page==='journeys'?'경로는 카카오 예상값입니다. 실제 출발 안내는 준비 중입니다.':'이동 체험의 경로·시각은 예시입니다.'}</span></footer>
      </main>
    </div>
    <nav className="mobile-nav" aria-label="모바일 메뉴">{navItems.map(([key,Icon,label])=><button key={key} className={page===key?'active':''} aria-current={page===key?'page':undefined} onClick={()=>navigate(key)}><Icon size={21}/><span>{label}</span></button>)}</nav>
    {toast&&<div className="toast" role="status"><Check size={18}/>{toast}</div>}
    {modal&&<Modal title={typeof modal==='object'?'루틴 설정':({route:'오늘의 경로',location:'출발 장소 확인',help:'화면 미리보기 안내',account:'나의 일상을 기억하려면'})[modal]} onClose={()=>setModal(null)}>
      {typeof modal==='object'?<RoutineForm routine={modal.routine} onSave={r=>{setRoutines(items=>modal.routine?items.map(item=>item.id===r.id?r:item):[...items,r]);setModal(null);notify('루틴을 미리보기에 저장했어요.');log('ui.routine.saved');}}/>:
      modal==='route'?<><p className="muted">{routine.origin} → {routine.destination} · 가상 경로</p><ol className="route-detail">{[['도보','집 출입구 → 정류장','5분'],['대기','첫 탑승 여유',`${buffer}분`],['버스',`${routine.bus}번 · 회사 방면`,'17분'],...(routine.transfer?[['환승','정류장 → 지하철 승강장','3분'],['대기','환승 여유','2분'],['지하철','2호선 · 목적지 방면','10분']]:[]),['도보','하차 지점 → 목적지','5분']].map(([type,detail,time],i)=><li key={i}><span className="tag">{type}</span><div><strong>{detail}</strong><p>{time}</p></div></li>)}</ol><p className="small muted">도보·대기·환승을 분리한 화면 예시예요. 실제 노선이나 연결 가능성은 확인되지 않았습니다.</p></>:
      modal==='location'?<OriginSelector onSelect={value=>{setOrigin(value);setOriginExpired(false);setTrip(null);setModal(null);navigate('home');}} onLogin={()=>setModal('account')} onAuthError={()=>{setOrigin(null);setOriginExpired(false);}}/>:
      modal==='account'?<AccountForm/>:
      <><p>디자인과 화면 흐름을 확인하는 React 프로토타입이에요.</p><ul className="help-list"><li>시간은 고정된 예시이며 실시간 카운트다운이 아니에요.</li><li>루틴과 설정은 새로고침하면 초기화돼요.</li><li>계정·장소 선택·카카오 경로 비교는 실제 API를 사용해요. AI 도보·실시간 도착·출발 안내는 준비 중이에요.</li><li>‘정보 만료’ 버튼으로 안내를 중지한 화면도 볼 수 있어요.</li></ul></>}
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
function RoutineForm({routine,onSave}) {
  const [name,setName]=useState(routine?.name||'');const [destination,setDestination]=useState(routine?.destination||'회사');const [time,setTime]=useState(routine?.time||'09:00');const [days,setDays]=useState(routine?.days||['월','화','수','목','금']);
  return <form onSubmit={e=>{e.preventDefault();if(!name.trim()||!days.length)return;onSave({id:routine?.id||crypto.randomUUID(),name:name.trim(),origin:'집',destination,time,days,bus:destination==='학교'?'721':'143',transfer:destination==='학교'});}}><label>루틴 이름<input autoFocus required maxLength={24} value={name} onChange={e=>setName(e.target.value)} placeholder="예: 아침 출근"/></label><div className="form-grid"><label>출발지<input value="집 (예시 장소)" readOnly/></label><label>도착지<select value={destination} onChange={e=>setDestination(e.target.value)}><option>회사</option><option>학교</option></select></label></div><label>목표 도착 시각<input type="time" required value={time} onChange={e=>setTime(e.target.value)}/></label><fieldset><legend>반복 요일</legend><div className="day-list selectable">{['월','화','수','목','금','토','일'].map(d=><button type="button" key={d} aria-pressed={days.includes(d)} className={days.includes(d)?'on':''} onClick={()=>setDays(ds=>ds.includes(d)?ds.filter(x=>x!==d):[...ds,d])}>{d}</button>)}</div></fieldset><div className="info-box">예시 경로: {destination==='학교'?'버스 → 지하철 · 환승 1회':'버스 직행'}<br/>도보는 자동 산정 결과를 표시할 자리예요. 현재는 예시 5분입니다.</div><button disabled={!name.trim()||!days.length} className="primary wide" type="submit">루틴 저장 <Check size={17}/></button></form>;
}
