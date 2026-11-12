"""Exercise result and download ownership in the shipped demo page."""

from pathlib import Path
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which("node"), "Node.js is required for page-script regressions")
class DemoBrowserStateTests(unittest.TestCase):
    def run_script(self, scenario):
        page = Path(__file__).resolve().parents[1] / "src/far_demo/app.py"
        harness = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync(process.argv[1], 'utf8').split('<script>')[1].split('</script>')[0];
const elements = new Map(), downloads = new Map(), requests = [];
let nextDownload = 0;
const element = id => {
  if (!elements.has(id)) {
    const classes = new Set();
    elements.set(id, {textContent: '', style: {}, scrollIntoView() {},
      classList: {
        add: name => classes.add(name),
        contains: name => classes.has(name),
        toggle: (name, show) => show ? classes.add(name) : classes.delete(name),
      },
      addEventListener(event, callback) { this[event] = callback; },
    });
  }
  return elements.get(id);
};
const report = id => ({headline: id, artifact: {sha256: id}, trace_completeness: 1,
  release_decision: 'review', plain_summary: 'Summary', why_it_matters: 'Impact',
  status_transition: [], structural_changes: [], unknowns: [], rule_findings: []});
const context = vm.createContext({
  document: {getElementById: element}, Blob, FormData: class {},
  URL: {
    createObjectURL(blob) { const url = 'blob:' + nextDownload++; downloads.set(url, blob); return url; },
    revokeObjectURL(url) { downloads.delete(url); },
  },
  setTimeout: queueMicrotask,
  fetch: path => new Promise((resolve, reject) => requests.push({path,
    success: id => resolve({ok: true, json: async () => report(id)}),
    malformed: data => resolve({ok: true, json: async () => data}),
    failure: detail => resolve({ok: false, json: async () => ({detail})}), reject,
  })),
});
vm.runInContext(source, context);
const sample = () => context.runExample();
const upload = () => element('form').submit({preventDefault() {}, target: {}});
async function assertResult(id) {
  assert.equal(element('headline').textContent, id);
  assert.equal(JSON.parse(element('raw').textContent).sha256, id);
  assert.equal(downloads.size, 1);
  const saved = downloads.get(element('downloadReport').href);
  assert.equal(JSON.parse(await saved.text()).sha256, id);
}
(async () => { SCENARIO })().catch(error => { console.error(error); process.exitCode = 1; });
""".replace("SCENARIO", scenario)
        result = subprocess.run(
            [shutil.which("node"), "-e", harness, str(page)],
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_older_upload_cannot_replace_latest_report_or_download(self):
        self.run_script("""
const old = upload(), latest = upload();
requests[1].success('latest upload'); await latest;
requests[0].success('older upload'); await old;
await assertResult('latest upload');
""")

    def test_sample_cannot_replace_a_later_upload(self):
        self.run_script("""
const old = sample(), latest = upload();
assert.deepEqual(requests.map(request => request.path), ['/api/example', '/api/analyze']);
requests[1].success('latest upload'); await latest;
requests[0].success('older sample'); await old;
await assertResult('latest upload');
assert.equal(element('statusRail').classList.contains('show'), false);
""")

    def test_older_upload_failure_cannot_overwrite_latest_feedback(self):
        self.run_script("""
const old = upload(), latest = upload();
requests[1].success('latest upload'); await latest;
requests[0].failure('older upload error'); await old;
assert.equal(element('error').textContent, '');
await assertResult('latest upload');
""")

    def test_sample_failure_is_visible_and_allows_retry(self):
        self.run_script("""
const failed = sample();
requests[0].failure('Sample unavailable'); await failed;
assert.equal(element('phase').textContent, 'Sample unavailable');
assert.equal(element('phasePct').textContent, '0%');
assert.equal(downloads.size, 0);
const retry = sample();
assert.equal(element('phasePct').textContent, '0%');
requests[1].success('retried sample'); await retry;
assert.equal(element('phasePct').textContent, '100%');
await assertResult('retried sample');
""")

    def test_stale_upload_network_failure_cannot_overwrite_latest_sample(self):
        self.run_script("""
const old = upload(), latest = sample();
requests[0].reject(Error('Connection lost')); await old;
assert.equal(element('error').textContent, '');
requests[1].success('latest sample'); await latest;
await assertResult('latest sample');
""")

    def test_latest_upload_failure_preserves_last_successful_report(self):
        self.run_script("""
const initial = upload(); requests[0].success('last success'); await initial;
const old = upload(), latest = upload();
requests[2].failure('Current upload rejected'); await latest;
requests[1].success('superseded upload'); await old;
assert.equal(element('error').textContent, 'Current upload rejected');
await assertResult('last success');
""")

    def test_malformed_success_preserves_current_report_and_download(self):
        self.run_script("""
const initial = upload(); requests[0].success('last success'); await initial;
const originalUrl = element('downloadReport').href;
for (const body of [{artifact: {}}, {...report('bad sample'), rule_findings: [null]}]) {
  const pending = sample(); requests.at(-1).malformed(body); await pending;
  await assertResult('last success');
  assert.equal(element('downloadReport').href, originalUrl);
  assert.equal(element('phasePct').textContent, '0%');
  assert.equal(element('phase').textContent, 'Invalid analysis response');
}
const retry = upload(); requests.at(-1).success('retried upload'); await retry;
await assertResult('retried upload');
assert.equal(downloads.has(originalUrl), false);
""")
