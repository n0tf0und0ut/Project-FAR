#!/usr/bin/env python3
"""Research-only, model-directed isolated AST renames; optional vs mandatory graph context.
Live protected repository and accepted FAR theory are never modified.
"""
from __future__ import annotations
import ast,collections,hashlib,json,os,pathlib,re,subprocess,tempfile,time
from llama_cpp import Llama

D=pathlib.Path(__file__).resolve().parent
ROOT=D.parent/'far'
GRAPH=D.parent/'graph.json'
MODEL=pathlib.Path('/home/user/far-graphify-eval-20261112/agent_compare/models/Qwen2.5-Coder-1.5B-Instruct-Q4_K_M.gguf')
RG=pathlib.Path('/home/user/far-graphify-eval-20261112/ripgrep-14.1.1-x86_64-unknown-linux-musl/rg')
protocol_path=D/'mandatory_gate_protocol.json';oracle_path=D/'mandatory_gate_oracle.json'
P=json.loads(protocol_path.read_text())
TRACKED=set(str(x.relative_to(ROOT)) for x in ROOT.rglob('*.py'))
assert len(TRACKED)==945
assert P['source_sha']=='8c6dc6cf840a0d82fb4dcde114c1af471b3f74fe'
assert hashlib.sha256(GRAPH.read_bytes()).hexdigest()==P['graph_sha256']
assert MODEL.stat().st_size==986048800 and RG.is_file()
assert not (D/'mandatory_gate_raw.jsonl').exists(), 'refuse to overwrite first results'
program_sha=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()
manifest={'protocol_sha256':hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
          'oracle_sha256':hashlib.sha256(oracle_path.read_bytes()).hexdigest(),
          'runner_sha256':program_sha,'source_sha':P['source_sha'],'graph_sha256':P['graph_sha256'],
          'model_sha256':hashlib.sha256(MODEL.read_bytes()).hexdigest(),
          'model_package':'llama-cpp-python==0.3.36','model_seed':662,'temperature':0,
          'n_ctx':4096,'max_tokens_per_call':400,'model_calls_per_task':'baseline=1; mandatory=1; optional=1 or 2 if model requests graphify',
          'run_order':'Rotate three arms per frozen task index modulo 3. No model fine-tuning. No gold access in prompts.',
          'tool_runner':'Model chooses candidate paths; deterministic AST token mutation tool changes those and definition file only, in disposable scratch dir.',
          'scope':'Nonsemantic syntactic rename; no original repository edits or runtime behavior claims'}
(D/'mandatory_gate_execution_manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
G=json.loads(GRAPH.read_text());byid={n['id']:n for n in G['nodes']}
bylabel=collections.defaultdict(list);back=collections.defaultdict(list)
for n in G['nodes']:bylabel[(n.get('label'),n.get('source_file'))].append(n)
for e in G['edges']:
 if e['relation']=='calls':back[e['target']].append(e)
def graph_lookup(name,defined):
 files=collections.defaultdict(list)
 for n in bylabel[(name+'()',defined)]+bylabel[('.'+name+'()',defined)]:
  for e in back[n['id']]:
   src=byid.get(e['source'],{})
   path=src.get('source_file')
   if path in TRACKED:
    files[path].append(str(e.get('source_location') or src.get('source_location') or ''))
 return {p:sorted(set(ls))[:2] for p,ls in sorted(files.items())}
def rg_lookup(name):
 pat=r'\b'+re.escape(name)+r'\s*\('
 cp=subprocess.run([str(RG),'-n','--pcre2','--hidden','--no-ignore','--glob','*.py','--max-columns','200',pat,'.'],
                   cwd=ROOT,capture_output=True,text=True,timeout=25)
 if cp.returncode not in (0,1):raise RuntimeError('rg error '+str(cp.returncode)+' '+cp.stderr[:200])
 files=collections.defaultdict(list)
 for line in cp.stdout.splitlines():
  m=re.match(r'^\./(.+?):(\d+):(.*)$',line)
  if not m:continue
  path=m.group(1)
  if path in TRACKED and len(files[path])<2:
   files[path].append({'line':int(m.group(2)),'snippet':m.group(3).strip()[:150]})
 return dict(sorted(files.items()))
def evidence_rg(name):
 st=time.perf_counter()
 data=rg_lookup(name)
 return {'source':'ripgrep','candidates':[{'file':k,'matches':v} for k,v in data.items()]},time.perf_counter()-st
def evidence_graph(name,defined):
 st=time.perf_counter();data=graph_lookup(name,defined)
 return {'source':'Graphify local code-only calls edges','candidates':[{'file':k,'graph_call_locations':v} for k,v in data.items()]},time.perf_counter()-st

SYS="""You are a bounded autonomous code-refactor planning agent.
You must choose all repository-tracked Python files containing ast.Call where the terminal
callee identifier equals the given old name. The underlying mutation tool will rename
exactly those ast.Call nodes and the unique function definition in an isolated sandbox;
the definition file is auto-handled, even if it is omitted from your list.
Definitions, comments, docstrings, imports, and examples are NOT calls, unless the
same file also contains an actual call.
Never invent files. Ripgrep regex snippets may include false positives.
Graphify edges can be useful but are incomplete; NEVER discard a ripgrep match
just because Graphify omitted it. Only return syntactic call-site paths.
For your FINAL ACTION return JSON exactly {"action":"apply_patch","files":["path.py",...]}.
No prose or markdown. Your tool budget is constrained."""
OPTIONAL="""For this task only, you can optionally request structural graph evidence ONCE
by returning exactly {"action":"graphify"}. If you can decide from ripgrep evidence,
return the apply_patch action immediately, conserving token/time cost.
After receiving graph evidence, you MUST return apply_patch and never request it again."""
MANDATORY="""Graphify dependency graph evidence was automatically injected by the
mandatory pre-task hook, whether or not you wanted it. Include ripgrep-only matches
when actually call expressions. Return apply_patch immediately."""
BASE="""Graphify is unavailable in this arm. You have ripgrep evidence only.
Return apply_patch immediately."""
def task_prompt(task,rg_data,extra=None):
 s=(f"Perform a synthetic refactor plan: rename {task['function']!r} -> "
    f"{task['function']+'_farref_v2'!r} across direct syntactic Python call sites. "
    f"Unique definition path: {task['definition_file']!r} (auto-mutated). "
    "Select every file containing an ast.Call with terminal identifier exactly "
    "the old name; list no definitions-only or other false positives. "
    "Evidence from ripgrep:\n"+json.dumps(rg_data,separators=(',',':')))
 if extra is not None:s+="\nGraphify secondary evidence:\n"+json.dumps(extra,separators=(',',':'))
 return s
def parse_action(answer):
 try:
  obj=json.loads(answer)
  if not isinstance(obj,dict) or not isinstance(obj.get('action'),str):raise ValueError('invalid JSON action')
  if obj['action']=='graphify' and set(obj)=={'action'}:return 'graphify',[],None
  if obj['action']!='apply_patch' or set(obj)!={'action','files'} or not isinstance(obj['files'],list):raise ValueError('unsupported action')
  files=obj['files']
  if any(not isinstance(x,str) or x not in TRACKED for x in files):raise ValueError('not repository tracked Python path')
  if len(set(files))!=len(files):raise ValueError('duplicate file')
  return 'apply_patch',sorted(files),None
 except Exception as e:return 'error',[],str(e)
def caller_match(node,name):
 if not isinstance(node,ast.Call):return False
 f=node.func
 return (isinstance(f,ast.Name) and f.id==name) or (isinstance(f,ast.Attribute) and f.attr==name)
def mutation_spans(code,name,rename_defs=False):
 tree=ast.parse(code)
 lines=code.encode('utf-8').splitlines(keepends=True);spans=collections.defaultdict(list)
 for n in ast.walk(tree):
  if caller_match(n,name):
   f=n.func
   if not isinstance(f,(ast.Name,ast.Attribute)):continue
   l=f.end_lineno-1;c=f.end_col_offset
   if lines[l][c-len(name):c]!=name.encode():raise ValueError('AST call token boundary mismatch')
   spans[l].append((c-len(name),c))
  if rename_defs and isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name:
   l=n.lineno-1;line=lines[l]
   pattern=rb'\bdef\s+('+re.escape(name.encode())+rb')\s*\('
   m=re.search(pattern,line)
   if not m:raise ValueError('definition span not found')
   spans[l].append(m.span(1))
 patched=list(lines);count=0
 for l,locs in spans.items():
  src=lines[l]; uniq=sorted(set(locs),reverse=True)
  for a,b in uniq:
   src=src[:a]+(name+'_farref_v2').encode()+src[b:];count+=1
  patched[l]=src
 body=b''.join(patched).decode('utf-8')
 ast.parse(body)
 compile(body,'<synthetic_AST_refactor>','exec',dont_inherit=True)
 return body,count
def patch_and_test(name,defined,selected):
 """Apply agent-controlled file list (not hidden oracle) to a temp checkout.
 Works from actual source files, not from the answer key."""
 new_name=name+'_farref_v2';changed=[];events=[];exception=None
 with tempfile.TemporaryDirectory(prefix='far-graphify-patch-') as tmp:
  target=pathlib.Path(tmp)
  for f in sorted(set(selected)|{defined}):
   src=ROOT/f
   raw=src.read_text(encoding='utf-8')
   try:
    after,n=mutation_spans(raw,name,rename_defs=(f==defined))
    if n:
     dst=target/f;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text(after,encoding='utf-8')
     check=ast.parse(dst.read_text(encoding='utf-8'))
     compile(check,str(dst),'exec',dont_inherit=True)
     changed.append(f)
     events.append({'file':f,'replacements':n,
                  'before_sha256':hashlib.sha256(raw.encode()).hexdigest(),
                  'after_sha256':hashlib.sha256(after.encode()).hexdigest()})
   except Exception as e:
    exception=repr(e);break
 return {'edit_files':changed,'edit_events':events,
         'syntax_valid':exception is None,'tool_error':exception,
         'new_name':new_name,'files_requested':selected}

def run():
 start=time.monotonic();model=Llama(model_path=str(MODEL),n_ctx=4096,n_threads=1,n_batch=256,verbose=False,seed=662)
 print('MODEL_LOADED_SECONDS',round(time.monotonic()-start,3),flush=True)
 path=D/'mandatory_gate_raw.jsonl';arms=['rg_only','optional_graph','mandatory_graph_hook']
 for i,t in enumerate(P['tasks']):
  order=arms[i%3:]+arms[:i%3]
  rg_data,rt= evidence_rg(t['function'])
  gr_data,gt=evidence_graph(t['function'],t['definition_file'])
  # identical retrieval observations for all arms of the same question.
  for arm in order:
   receipt={'task_id':t['task_id'],'task_index':i,'function':t['function'],'definition_file':t['definition_file'],
            'arm':arm,'model_sha256':manifest['model_sha256'],'source_sha':P['source_sha'],
            'tool_initial_retrieval_seconds':round(rt,6),'graph_lookup_seconds':round(gt,6),
            'rg_evidence':rg_data,'graph_evidence':gr_data if arm=='mandatory_graph_hook' else None,
            'visible_gold':False,'model_calls':[],'second_stage_graph_requested':False}
   try:
    extra=gr_data if arm=='mandatory_graph_hook' else None
    sys_text=SYS+'\n'+({'rg_only':BASE,'optional_graph':OPTIONAL,'mandatory_graph_hook':MANDATORY}[arm])
    first=task_prompt(t,rg_data,extra)
    msgs=[{'role':'system','content':sys_text},{'role':'user','content':first}]
    response_tokens=0
    action=None;files=[];invalid=None
    for call_idx in range(2):
     model.reset();st=time.perf_counter()
     response=model.create_chat_completion(messages=msgs,response_format={'type':'json_object'},
                  temperature=0.0,max_tokens=400,seed=662+i)
     runtime=time.perf_counter()-st
     raw=response['choices'][0]['message']['content']
     act,files,parse_error=parse_action(raw)
     usage=response.get('usage') or {};response_tokens+=usage.get('total_tokens',0)
     receipt['model_calls'].append({'messages':msgs.copy(),'raw':raw,'action':act,'parse_error':parse_error,
                                   'wall_seconds':round(runtime,5),'usage':usage})
     if parse_error:invalid=parse_error;break
     if act=='apply_patch':action=act;break
     if act=='graphify' and arm=='optional_graph' and call_idx==0:
      receipt['second_stage_graph_requested']=True
      receipt['graph_evidence']=gr_data
      msgs=msgs+[{'role':'assistant','content':raw},
                  {'role':'user','content':"Tool result (Graphify):\n"+json.dumps(gr_data,separators=(',',':'))+
                   "\nNow choose all true ast.Call files and emit final apply_patch action; do not ask for more tools."}]
      continue
     invalid='unexpected graphify request or unfinished action';break
    receipt['final_action']=action
    receipt['invalid_action']=invalid
    receipt['model_total_tokens']=response_tokens
    receipt['selected_files']=files if action=='apply_patch' else []
    receipt['patch_result']=patch_and_test(t['function'],t['definition_file'],receipt['selected_files']) if action else None
    receipt['error']=None
   except Exception as exc:
    receipt['error']=repr(exc)
    receipt['invalid_action']=receipt.get('invalid_action') or 'uncaught tool/model error'
    receipt['model_total_tokens']=sum(r.get('usage',{}).get('total_tokens',0) for r in receipt['model_calls'])
    receipt['selected_files']=[]
    receipt['patch_result']=None
   with path.open('a',encoding='utf-8') as f:f.write(json.dumps(receipt,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
   print('COMPLETE',i,arm,'selected',len(receipt['selected_files']),
         'tokens',receipt['model_total_tokens'],'graph_requested',receipt['second_stage_graph_requested'],
         'error',receipt['error'] or receipt['invalid_action'],flush=True)
 print('ALL_72_DONE',flush=True)
if __name__=='__main__':run()
