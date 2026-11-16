// Read-only checks against an already running local server. No browser/model calls.
import assert from 'node:assert/strict';
const base=process.env.LUMINA_CHECK_URL??'http://127.0.0.1:3007';
assert.ok(new URL(base).hostname==='127.0.0.1'||new URL(base).hostname==='localhost','Use a local demo URL.');
const home=await fetch(base);assert.equal(home.status,200);const html=await home.text();assert.match(html,/Lumina/);assert.match(html,/<link[^>]+rel="icon"[^>]+href="\/images\/logo.png"/);
const response=await fetch(`${base}/api/benchmark`);assert.equal(response.status,200);const {cases}=await response.json();
assert.equal(cases.length,240);assert.equal(new Set(cases.map(c=>c.id)).size,240);
for(const c of cases)assert.deepEqual(Object.keys(c).sort(),['category','id','question','split','suite']);
for(const suite of ['basic','advanced'])for(const split of ['dev','test'])assert.equal(cases.filter(c=>c.suite===suite&&c.split===split).length,suite==='basic'?50:70);
const meta=await (await fetch(`${base}/api/document?meta=1`)).json();assert.equal(meta.available,true);assert.ok(meta.bytes>0);
const partial=await fetch(`${base}/api/document`,{headers:{Range:'bytes=0-3'}});assert.equal(partial.status,206);assert.equal(await partial.text(),'%PDF');
const badRange=await fetch(`${base}/api/document`,{headers:{Range:'bytes=100-50'}});assert.equal(badRange.status,416);
const badPath=await fetch(`${base}/api/document?path=../../.env`,{headers:{Range:'bytes=0-3'}});assert.equal(await badPath.text(),'%PDF');
const animation=await fetch(`${base}/animations/animation.json`);assert.equal(animation.status,200);assert.ok((await animation.json()).layers.length>0);
for(const name of ['/images/logo.png','/documents/page-31.png'])assert.equal((await fetch(base+name)).status,200);
console.log('PASS: page, 240 safe query records, source metadata, PDF range/416, fixed-path serving, local Lottie, logo and source preview.');
