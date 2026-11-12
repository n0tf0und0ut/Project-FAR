#!/usr/bin/env python3
"""Resume the frozen runner after hosted process lease expires without changing scored behavior.

This launcher changes ONLY the anti-overwrite guard and adds skip-completed behavior.
It asserts the exact source SHA256 of the committed original runner. It never
revises prior receipts or the frozen task/arm order.
"""
import hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
RUNNER=ROOT/'mandatory_gate_run.py'
EXPECTED='18748249368ae6f905fddfdd1b3268191e77b6cf89a93e8aad96e975aabd6b9c'
raw=RUNNER.read_text(encoding='utf-8')
assert hashlib.sha256(raw.encode()).hexdigest()==EXPECTED, 'frozen runner changed'
old_guard="assert not (D/'mandatory_gate_raw.jsonl').exists(), 'refuse to overwrite first results'"
assert raw.count(old_guard)==1
raw=raw.replace(old_guard,"# Resumable: permit append-only progress from prior invocation")
old_arm="  for arm in order:\n   receipt="
assert raw.count(old_arm)==1
skip="""  for arm in order:
   existing=set()
   if path.exists():
    for previous_line in path.read_text(encoding='utf-8').splitlines():
     if not previous_line.strip():continue
     previous=json.loads(previous_line)
     key=(previous.get('task_id'),previous.get('arm'))
     if key in existing:raise RuntimeError('duplicate prior receipt: '+str(key))
     existing.add(key)
   if (t['task_id'],arm) in existing:
    print('SKIP_COMPLETED',i,arm,flush=True)
    continue
   receipt="""
raw=raw.replace(old_arm,skip)
print('FROZEN_RUNNER_SHA',EXPECTED,'PREVIOUS_RECEIPTS',
      len((ROOT/'mandatory_gate_raw.jsonl').read_text().splitlines()),flush=True)
exec(compile(raw,str(RUNNER),mode='exec'),{'__name__':'__main__','__file__':str(RUNNER)})
