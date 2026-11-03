"""Execute the shipped page script against bounded DOM/provider test doubles.

These tests exercise asynchronous workspace integrity, not model effectiveness.
"""
from pathlib import Path
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which("node"), "Node.js is required for page-script regressions")
class BrowserStateTests(unittest.TestCase):
    def run_script(self, scenario, setup="", fixture=None):
        page = Path(__file__).resolve().parents[1] / "src/far_demo/augmentation.html"
        harness = r"""
const fs=require('node:fs'), vm=require('node:vm'), assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8').split('<script>')[1].split('</script>')[0];
const fixture=process.argv[2]?JSON.parse(fs.readFileSync(process.argv[2],'utf8')):null;
const elements=new Map(), saved=new Map();
function element(){return {value:'token',hidden:false,disabled:false,dataset:{},listeners:{},
  addEventListener(name,fn){this.listeners[name]=fn},append(){},replaceChildren(){},reset(){},click(){}};}
const doc={getElementById(id){if(!elements.has(id))elements.set(id,element());return elements.get(id)},
  createElement:element,querySelectorAll(){return []}};
let release, calls=0;
const context={document:doc,console,setTimeout,Blob,URL,
  localStorage:{getItem:k=>saved.get(k)||null,setItem:(k,v)=>saved.set(k,v),removeItem:k=>saved.delete(k)},
  fetch:async(path)=>{if(path==='/api/augment/model/status')return {ok:true,json:async()=>({configured:true,model:'stub'})};
    if(path==='/api/augment/semantic'){calls++;return await new Promise(resolve=>{release=report=>resolve({ok:true,json:async()=>report})})}
    throw Error('Unexpected request '+path);}};
vm.createContext(context);
SETUP
vm.runInContext(source+`;globalThis.hooks={set:(s,r)=>{session=s;reports=r},get:()=>({session,reports}),click:()=>byId('modelButton').listeners.click()};`,context);
const report={model:'stub',snapshot_revision_count:0,sha256:'report-A',findings:[],open_questions:[]};
const a={basis_sha256:'basis-A',sha256:'session-A',revisions:[]};
(async()=>{await Promise.resolve();SCENARIO})().catch(e=>{console.error(e);process.exitCode=1});
""".replace("SCENARIO", scenario).replace("SETUP", setup)
        args = [shutil.which("node"), "-e", harness, str(page)]
        if fixture is not None:
            args.append(str(fixture))
        result = subprocess.run(args, text=True,
                                capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_report_limit_prevents_unrestorable_twenty_first_analysis(self):
        self.run_script("""
context.hooks.set(a,Array.from({length:20},()=>report));
const pending=context.hooks.click();
if(release)release(report);
await pending;
assert.equal(calls,0,'limit must be enforced before requesting model inference');
assert.equal(context.hooks.get().reports.length,20);
""")

    def test_pending_response_cannot_enter_replacement_session(self):
        self.run_script("""
context.hooks.set(a,[]);
const pending=context.hooks.click();
const b={basis_sha256:'basis-B',sha256:'session-B',revisions:[]};
context.hooks.set(b,[]);release(report);await pending;
assert.equal(context.hooks.get().reports.length,0,'stale report must be discarded');
assert.equal(saved.size,0,'a mismatched workspace must never be persisted');
""")

    def test_pending_response_survives_append_only_revision(self):
        self.run_script("""
const reports=[];context.hooks.set(a,reports);
const pending=context.hooks.click();
context.hooks.set({...a,sha256:'revision-A',revisions:[{index:1}]},reports);
release(report);await pending;
assert.equal(context.hooks.get().reports.length,1);
assert.equal(saved.size,1);
""")

    def test_offline_restoration_preserves_exact_saved_bytes(self):
        self.run_script("""
await new Promise(setImmediate);
assert.equal(saved.get('far-augmentation-prototype-v02'),original);
assert.equal(context.hooks.get().session,null,'unverified data must not be hydrated');
""", setup="""
const original=JSON.stringify({schema:'far-augmentation-export/0.2',session:{sha256:'saved'},semantic_reports:[]});
saved.set('far-augmentation-prototype-v02',original);
context.fetch=async()=>{throw Error('offline')};
""")

    def test_pending_revision_cannot_overwrite_replacement_workspace(self):
        self.run_script("""
context.hooks.set(a,[]);
const pending=elements.get('revisionPane').listeners.submit({preventDefault(){}});
elements.get('clearButton').listeners.click();
const b={basis_sha256:'basis-B',sha256:'session-B',revisions:[]};context.hooks.set(b,[]);
finishRevision({...a,sha256:'revision-A'});await pending;
assert.equal(context.hooks.get().session,b,'old revision must not replace current workspace');
assert.equal(saved.size,0,'stale revision must not be persisted');
""", setup="""
let finishRevision;
const originalFetch=context.fetch;
context.fetch=async(path,...args)=>path==='/api/augment/revise'
  ?await new Promise(resolve=>{finishRevision=s=>resolve({ok:true,json:async()=>s})})
  :await originalFetch(path,...args);
""")

    def test_pending_start_cannot_overwrite_new_session_intent(self):
        self.run_script("""
const pending=elements.get('initialForm').listeners.submit({preventDefault(){}});
elements.get('clearButton').listeners.click();finishStart(a);await pending;
assert.equal(context.hooks.get().session,null);
assert.equal(saved.size,0);
""", setup="""
let finishStart;
const originalFetch=context.fetch;
context.fetch=async(path,...args)=>path==='/api/augment/start'
  ?await new Promise(resolve=>{finishStart=s=>resolve({ok:true,json:async()=>s})})
  :await originalFetch(path,...args);
""")

    def test_pending_import_cannot_overwrite_new_session_intent(self):
        self.run_script("""
const event={target:{value:'selected',files:[{size:100,text:async()=>JSON.stringify({session:a,semantic_reports:[],schema:'far-augmentation-export/0.2'})}]}};
const pending=elements.get('importFile').listeners.change(event);
await new Promise(setImmediate);elements.get('clearButton').listeners.click();finishVerify();await pending;
assert.equal(context.hooks.get().session,null);
assert.equal(saved.size,0);
""", setup="""
let finishVerify;
const originalFetch=context.fetch;
context.fetch=async(path,...args)=>path==='/api/augment/verify'
  ?await new Promise(resolve=>{finishVerify=()=>resolve({ok:true,json:async()=>({valid:true})})})
  :await originalFetch(path,...args);
""")

    def test_pending_restoration_cannot_overwrite_new_session_intent(self):
        self.run_script("""
elements.get('clearButton').listeners.click();finishVerify();await new Promise(setImmediate);
assert.equal(context.hooks.get().session,null);
assert.equal(saved.size,0);
""", setup="""
let finishVerify;
saved.set('far-augmentation-prototype-v02',JSON.stringify({schema:'far-augmentation-export/0.2',session:{sha256:'old',basis:{claim:'c',confidence:50},questions:[],revisions:[]},semantic_reports:[]}));
context.fetch=async(path)=>path==='/api/augment/verify'
  ?await new Promise(resolve=>{finishVerify=()=>resolve({ok:true,json:async()=>({valid:true})})})
  :{ok:true,json:async()=>({configured:true,model:'stub'})};
""")

    def test_retry_verifies_without_rewriting_original_saved_bytes(self):
        self.run_script("""
await new Promise(setImmediate);
context.fetch=async()=>({ok:true,json:async()=>({valid:true})});
await elements.get('retryRestore').listeners.click();
assert.equal(context.hooks.get().session.sha256,'saved');
assert.equal(saved.get('far-augmentation-prototype-v02'),original);
assert.equal(elements.get('retryRestore').hidden,true);
""", setup="""
const original=JSON.stringify({schema:'far-augmentation-export/0.2',session:{sha256:'saved',basis:{claim:'c',confidence:50},questions:[],revisions:[]},semantic_reports:[]});
saved.set('far-augmentation-prototype-v02',original);
context.fetch=async()=>{throw Error('offline')};
""")

    def test_stored_and_exported_bytes_match_and_import_round_trips(self):
        self.run_script("""
context.hooks.set({...a,basis:{claim:'c',confidence:50},questions:[]},[]);
const pending=context.hooks.click();release(report);await pending;
elements.get('exportButton').listeners.click();
const exported=await downloaded.text();
assert.equal(exported,saved.get('far-augmentation-prototype-v02'));
assert.ok(downloaded.size<=500000);
context.fetch=async()=>({ok:true,json:async()=>({valid:true})});
await elements.get('importFile').listeners.change({target:{value:'selected',files:[{size:downloaded.size,text:async()=>exported}]}});
assert.equal(context.hooks.get().reports.length,1);
assert.equal(saved.get('far-augmentation-prototype-v02'),exported);
""", setup="""
let downloaded;
context.URL={createObjectURL:blob=>{downloaded=blob;return 'blob:stub'},revokeObjectURL(){}};
""")

    def test_aggregate_reports_above_old_import_limit_remain_exportable(self):
        self.run_script("""
const f={category:'INFERENCE_GAP',observation:'o'.repeat(500),inference:'i'.repeat(700),
anchors:[{path:'basis.claim',quote:'a'.repeat(500)},{path:'basis.reasoning',quote:'b'.repeat(500)},{path:'basis.falsifier',quote:'c'.repeat(500)}],
alternatives:['d'.repeat(700),'e'.repeat(700),'f'.repeat(700)],test:'t'.repeat(600),question:'q'.repeat(300)};
const large={...report,findings:Array.from({length:5},()=>f),open_questions:Array.from({length:5},()=> 'x'.repeat(800))};
assert.ok(new Blob([JSON.stringify({findings:large.findings,open_questions:large.open_questions})]).size<35000,'provider output is individually bounded');
const previous=Array.from({length:14},()=>large);
assert.ok(new Blob([JSON.stringify({schema:'far-augmentation-export/0.2',session:a,semantic_reports:previous},null,2)+'\\n']).size<=500000,'initial workspace is within limit');
context.hooks.set(a,previous);
const pending=context.hooks.click();release(large);await pending;
const current=context.hooks.get();
const bytes=new Blob([JSON.stringify({schema:'far-augmentation-export/0.2',session:current.session,semantic_reports:current.reports},null,2)+'\\n']).size;
assert.ok(bytes>500000&&bytes<=8*1024*1024,'valid aggregate can exceed old single-request limit');
assert.equal(current.reports.length,15);
assert.equal(saved.size,1);
""")

    def test_storage_quota_failure_preserves_prior_workspace_and_saved_bytes(self):
        self.run_script("""
const prior=[];context.hooks.set(a,prior);
saved.set('far-augmentation-prototype-v02','previous-exact-bytes');
context.localStorage.setItem=()=>{throw Error('QuotaExceededError')};
const pending=context.hooks.click();release(report);await pending;
assert.equal(context.hooks.get().session,a);
assert.equal(context.hooks.get().reports,prior);
assert.equal(saved.get('far-augmentation-prototype-v02'),'previous-exact-bytes');
""")

    def test_unverified_saved_bytes_can_be_downloaded_without_hydration(self):
        self.run_script("""
await new Promise(setImmediate);
elements.get('downloadStored').listeners.click();
assert.equal(await downloaded.text(),original);
assert.equal(saved.get('far-augmentation-prototype-v02'),original);
assert.equal(context.hooks.get().session,null);
""", setup="""
let downloaded;const original='not even valid JSON: preserved verbatim';
saved.set('far-augmentation-prototype-v02',original);
context.URL={createObjectURL:blob=>{downloaded=blob;return 'blob:stub'},revokeObjectURL(){}};
""")

    def test_aggregate_import_retains_explicit_bounded_ceiling(self):
        self.run_script("""
let read=false;
await elements.get('importFile').listeners.change({target:{value:'selected',files:[{size:8*1024*1024+1,text:async()=>{read=true;return '{}'}}]}});
assert.equal(read,false,'oversized file must be refused before reading');
assert.equal(saved.size,0);
""")


if __name__ == "__main__":
    unittest.main()
