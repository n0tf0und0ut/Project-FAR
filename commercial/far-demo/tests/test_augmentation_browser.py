"""Execute the shipped page script against bounded DOM/provider test doubles.

These tests exercise asynchronous workspace integrity, not model effectiveness.
"""
from pathlib import Path
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which("node"), "Node.js is required for page-script regressions")
class BrowserStateTests(unittest.TestCase):
    def run_script(self, scenario):
        page = Path(__file__).resolve().parents[1] / "src/far_demo/augmentation.html"
        harness = r"""
const fs=require('node:fs'), vm=require('node:vm'), assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8').split('<script>')[1].split('</script>')[0];
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
vm.runInContext(source+`;globalThis.hooks={set:(s,r)=>{session=s;reports=r},get:()=>({session,reports}),click:()=>byId('modelButton').listeners.click()};`,context);
const report={model:'stub',snapshot_revision_count:0,sha256:'report-A',findings:[],open_questions:[]};
const a={basis_sha256:'basis-A',sha256:'session-A',revisions:[]};
(async()=>{await Promise.resolve();SCENARIO})().catch(e=>{console.error(e);process.exitCode=1});
""".replace("SCENARIO", scenario)
        result = subprocess.run([shutil.which("node"), "-e", harness, str(page)], text=True,
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


if __name__ == "__main__":
    unittest.main()
