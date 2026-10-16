import React,{useEffect,useRef,useState} from 'react';
import {Download} from 'lucide-react';
import {exportRecords} from '../lib/tripExports';

export default function TripExport({onLogin}){
 const [days,setDays]=useState('30'),[state,setState]=useState({});
 const controller=useRef(null);
 useEffect(()=>()=>controller.current?.abort(),[]);
 async function download(){
  if(controller.current)return;
  const c=new AbortController();controller.current=c;setState({loading:true});
  try{const count=await exportRecords(days,c.signal);if(!c.signal.aborted)setState({notice:`${count}개 기록을 JSON 파일로 다운로드했어요.${count===0?' 선택한 기간에 저장된 기록이 없어요.':''}`});}
  catch(e){if(!c.signal.aborted)setState({auth:['AUTH_REQUIRED','SESSION_EXPIRED'].includes(e.code),error:e.code==='EXPORT_LIMIT_EXCEEDED'?'기록이 500건을 넘어요. 더 짧은 기간을 선택해주세요.':['AUTH_REQUIRED','SESSION_EXPIRED'].includes(e.code)?'로그인 후 본인 기록을 다운로드해주세요.':'다운로드하지 못했어요. 잠시 후 다시 시도해주세요.'});}
  finally{if(controller.current===c)controller.current=null;}
 }
 return <section className="card" aria-label="이동 기록 내보내기">
  <h2><Download size={18} aria-hidden="true"/> 기록 내보내기</h2>
  <p className="muted">현재 저장된 본인 기록을 JSON 파일로 내려받아요. 정정·삭제한 내용이 반영돼요.</p>
  <div className="button-row trip-progress-actions"><label>내보낼 기간 <select aria-label="내보낼 기간" value={days} disabled={state.loading} onChange={e=>setDays(e.target.value)}><option value="7">최근 7일</option><option value="30">최근 30일</option><option value="90">최근 90일</option></select></label>
   <button className="secondary" disabled={state.loading} onClick={download}>{state.loading?'파일 준비 중…':'JSON 다운로드'}</button></div>
  {state.loading&&<p role="status">기록 파일을 준비하고 있어요.</p>}
  {state.notice&&<p className="info-box" role="status">{state.notice}</p>}
  {state.error&&<div className="info-box" role="alert"><p>{state.error}</p>{state.auth&&<button className="secondary" onClick={onLogin}>로그인</button>}</div>}
 </section>;
}
