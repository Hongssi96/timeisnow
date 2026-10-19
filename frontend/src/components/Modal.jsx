import React, {useEffect, useId, useRef} from 'react';
import {X} from 'lucide-react';

export default function Modal({title,onClose,children,className=''}) {
  const ref=useRef(null),titleId=useId();
  useEffect(()=>{
    const node=ref.current,trigger=document.activeElement;
    node.showModal();
    return()=>{node.close();if(trigger?.isConnected)trigger.focus();};
  },[]);
  function backdrop(event){
    if(event.target!==ref.current)return;
    const box=ref.current.getBoundingClientRect();
    if(event.clientX<box.left||event.clientX>box.right||event.clientY<box.top||event.clientY>box.bottom)onClose();
  }
  function containFocus(event){
    if(event.key!=='Tab')return;
    const items=[...ref.current.querySelectorAll('button:not(:disabled),a[href],input:not(:disabled),select:not(:disabled),textarea:not(:disabled),[tabindex]:not([tabindex="-1"])')]
      .filter(node=>node.getClientRects().length>0);
    const first=items[0],last=items.at(-1);
    if(!first){event.preventDefault();return;}
    if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
    else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
  }
  return <dialog ref={ref} className={`modal ${className}`} aria-labelledby={titleId}
    onCancel={event=>{event.preventDefault();onClose();}} onClick={backdrop} onKeyDown={containFocus}>
    <div className="modal-heading"><h2 id={titleId}>{title}</h2><button type="button" className="icon-button" aria-label="닫기" onClick={onClose}><X size={22}/></button></div>
    {children}
  </dialog>;
}
