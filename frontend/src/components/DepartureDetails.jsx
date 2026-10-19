import React, {useState} from 'react';
import {Info,ChevronRight} from 'lucide-react';
import Modal from './Modal';

export default function DepartureDetails({children}) {
  const [open,setOpen]=useState(false);
  return <>
    <button type="button" className="secondary departure-details-button" aria-haspopup="dialog" onClick={()=>setOpen(true)}><Info size={17} aria-hidden="true"/>자세히 보기<ChevronRight size={17} aria-hidden="true"/></button>
    {open&&<Modal title="출발 안내 자세히 보기" className="departure-details-modal" onClose={()=>setOpen(false)}>{children}</Modal>}
  </>;
}
