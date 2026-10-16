"""Sweep and rebuild atomically; no external providers and no private logging."""
import json
import asyncio
import threading
from contextlib import asynccontextmanager
from app.common.database import database
from app.personalization import repository as learning
from app.retention import repository as repo

def sweep(c,owner):
    if not repo.pending(c,owner):return None
    profile=learning.locked(c,owner,maintain=False)
    # Recheck after waiting for another request or server's sweep.
    if not repo.pending(c,owner):return None
    result=repo.remove(c,owner)
    if result['rebuild']:
        from app.personalization.relearning import rebuild
        rebuild(c,owner,profile)
    return result

def run_all(stop=None):
    totals={'checked':0,'changed':0,'rebuilt':0,'failed':0};after=None
    while stop is None or not stop.is_set():
        with database() as c:rows=repo.owners(c,after)
        if not rows:break
        for row in rows:
            if stop is not None and stop.is_set():return totals
            after=row['user_id'];totals['checked']+=1
            try:
                with database() as c:
                    repo.timeouts(c)
                    result=sweep(c,after)
                if result:totals['changed']+=1;totals['rebuilt']+=int(result['rebuild'])
            except Exception:totals['failed']+=1
    return totals

@asynccontextmanager
async def lifespan(app):
    stop=threading.Event();wake=asyncio.Event()
    async def loop():
        while not stop.is_set():
            try:result=await asyncio.to_thread(run_all,stop)
            except Exception:result={'checked':0,'changed':0,'rebuilt':0,'failed':1}
            print(json.dumps({'event':'retention.sweep.completed',**result}),flush=True)
            try:await asyncio.wait_for(wake.wait(),timeout=3600)
            except TimeoutError:pass
    task=asyncio.create_task(loop())
    try:yield
    finally:
        stop.set();wake.set();await task
