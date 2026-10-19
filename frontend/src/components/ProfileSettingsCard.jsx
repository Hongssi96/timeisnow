import React,{useEffect,useRef,useState} from 'react';
import {SlidersHorizontal,Info} from 'lucide-react';
import {getProfile,saveProfile} from '../lib/profile';
import Modal from './Modal';

const authError=error=>['AUTH_REQUIRED','SESSION_EXPIRED'].includes(error?.code);
const draftOf=p=>({walking_preference:p.walking_preference,route_preference:p.route_preference,
  firstMinutes:String(Math.floor(p.first_boarding_buffer_seconds/60)),firstSeconds:String(p.first_boarding_buffer_seconds%60),
  transferMinutes:String(Math.floor(p.transfer_buffer_seconds/60)),transferSeconds:String(p.transfer_buffer_seconds%60)});
function seconds(minutes,remainder){
  if(!/^\d{1,2}$/.test(minutes)||!/^\d{1,2}$/.test(remainder))return null;
  const total=Number(minutes)*60+Number(remainder);
  return Number(remainder)<60&&total<=1800?total:null;
}
export default function ProfileSettingsCard({onLogin,onSaved}){
  const [retry,setRetry]=useState(0),[state,setState]=useState({phase:'loading'}),[draft,setDraft]=useState(null),[help,setHelp]=useState(false);
  const pending=useRef(null),alive=useRef(false);
  useEffect(()=>{
    alive.current=true;const controller=new AbortController();pending.current=controller;setState({phase:'loading'});setDraft(null);
    getProfile(controller.signal).then(value=>{if(!controller.signal.aborted){setState({phase:'ready',...value});setDraft(draftOf(value.profile));}})
      .catch(error=>{if(!controller.signal.aborted)setState({phase:authError(error)?'anonymous':'error'});})
      .finally(()=>{if(pending.current===controller)pending.current=null;});
    return()=>{alive.current=false;pending.current?.abort();pending.current=null;};
  },[retry]);
  const first=draft?seconds(draft.firstMinutes,draft.firstSeconds):null,transfer=draft?seconds(draft.transferMinutes,draft.transferSeconds):null;
  const valid=first!==null&&transfer!==null;
  const profile=state.profile;
  const changes=profile&&draft?Object.fromEntries(Object.entries({walking_preference:draft.walking_preference,route_preference:draft.route_preference,
    first_boarding_buffer_seconds:first,transfer_buffer_seconds:transfer}).filter(([key,value])=>profile[key]!==value)):{};
  function edit(key,value){setDraft(old=>({...old,[key]:value}));setState(old=>({...old,message:null,notice:null}));}
  async function submit(event){
    event.preventDefault();if(pending.current||!valid||!Object.keys(changes).length||state.conflict)return;
    const controller=new AbortController();pending.current=controller;setState(old=>({...old,saving:true,message:null,notice:null}));
    try{
      const saved=await saveProfile(state.owner,profile.version,changes,controller.signal);
      if(!alive.current||controller.signal.aborted)return;
      setDraft(draftOf(saved));setState({phase:'ready',owner:state.owner,profile:saved,notice:'설정을 저장했어요. 다음 출발 안내부터 반영해요.'});
      onSaved?.(saved);
    }catch(error){
      if(!alive.current||controller.signal.aborted)return;
      if(authError(error)||error.code==='SESSION_CHANGED'){
        setDraft(null);setState({phase:authError(error)?'anonymous':'changed'});
      }else setState(old=>({...old,saving:false,conflict:error.code==='VERSION_CONFLICT',message:error.code==='VERSION_CONFLICT'?'다른 곳에서 설정이 변경됐어요. 최신 설정을 불러온 뒤 다시 수정해주세요.':'설정을 저장하지 못했어요. 입력을 확인하고 다시 시도해주세요.'}));
    }finally{if(pending.current===controller)pending.current=null;}
  }
  return <section className="card profile-settings" aria-labelledby="profile-settings-title">
    <div className="section-heading"><h2 id="profile-settings-title"><SlidersHorizontal size={19} aria-hidden="true"/>이동 설정</h2><button type="button" className="icon-button" aria-label="이동 설정 적용 범위" aria-haspopup="dialog" onClick={()=>setHelp(true)}><Info size={20}/></button></div>
    {state.phase==='loading'&&<p role="status">저장된 설정을 불러오고 있어요…</p>}
    {state.phase==='anonymous'&&<><p role="status">로그인하면 내 이동 설정을 저장할 수 있어요.</p><button className="secondary" onClick={onLogin}>로그인하기</button></>}
    {['error','changed'].includes(state.phase)&&<><p role="alert">{state.phase==='changed'?'로그인 계정이 바뀌었어요. 설정을 다시 불러와주세요.':'설정을 불러오지 못했어요.'}</p><button className="secondary" onClick={()=>setRetry(n=>n+1)}>설정 다시 불러오기</button></>}
    {profile&&draft&&<form onSubmit={submit} aria-busy={Boolean(state.saving)}>
      <fieldset disabled={state.saving||state.conflict}>
        <legend className="sr-only">개인 이동 설정</legend>
        <label>보행 선호<select aria-label="보행 선호" value={draft.walking_preference} onChange={e=>edit('walking_preference',e.target.value)}><option value="slow">천천히</option><option value="normal">보통</option><option value="fast">빠르게</option></select></label>
        <label>기본 경로 비교 기준<select aria-label="기본 경로 비교 기준" value={draft.route_preference} onChange={e=>edit('route_preference',e.target.value)}><option value="balanced">전체 예상 시간순</option><option value="fewer_transfers">환승 적은 순</option><option value="less_walking">제공된 도보 시간순</option></select></label>
        {[['첫 탑승 여유','first'],['환승 여유','transfer']].map(([label,key])=><div className="profile-buffer" key={key}><span>{label}</span><div className="profile-time-inputs">
          <label><input type="number" inputMode="numeric" min="0" max="30" step="1" required aria-label={`${label} 분`} value={draft[key+'Minutes']} onChange={e=>edit(key+'Minutes',e.target.value)}/>분</label>
          <label><input type="number" inputMode="numeric" min="0" max="59" step="1" required aria-label={`${label} 초`} value={draft[key+'Seconds']} onChange={e=>edit(key+'Seconds',e.target.value)}/>초</label>
        </div></div>)}
        <p className="small muted">각 여유는 0~30분까지 설정할 수 있어요.</p>
        {!valid&&<p role="alert">여유를 0~30분 사이의 분·초 정수로 입력해주세요.</p>}
        <button className="primary" disabled={!valid||!Object.keys(changes).length} type="submit">{state.saving?'저장 중…':'설정 저장'}</button>
      </fieldset>
      {state.message&&<p role="alert">{state.message}</p>}
      {state.conflict&&<button type="button" className="secondary" onClick={()=>setRetry(n=>n+1)}>최신 설정 불러오기</button>}
      {state.notice&&<p role="status">{state.notice}</p>}
    </form>}
    {help&&<Modal title="설정은 어디에 반영되나요?" onClose={()=>setHelp(false)}><p>첫 탑승 여유는 다음 출발 안내에, 환승 여유는 다음 환승 계산에 반영해요. 0분은 별도 여유 없이 계산하는 설정이에요.</p><p>경로 비교 기준은 새 검색의 기본값이에요. 비교 화면에서 다른 기준을 선택할 수 있고 저장한 루틴 경로는 그대로 유지돼요.</p><p>보행 선호만으로 도보 시간을 임의로 바꾸지 않아요. 시간 계수는 실제 보행 기록으로 학습하며 여유 시간을 자동으로 줄이지 않아요.</p><p>이미 저장한 이동 기록과 당시 예측은 그대로 남아요.</p></Modal>}
  </section>;
}
