"""Run from backend: .venv/Scripts/python.exe -m app.retention."""
import json
from app.retention.service import run_all
if __name__=='__main__':
    try:result=run_all()
    except Exception:result={'checked':0,'changed':0,'rebuilt':0,'failed':1}
    print(json.dumps(result))
    raise SystemExit(1 if result['failed'] else 0)
