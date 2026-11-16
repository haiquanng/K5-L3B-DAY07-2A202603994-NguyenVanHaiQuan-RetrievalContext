import { test } from 'node:test';
import assert from 'node:assert/strict';
import { checkRun } from '../src/lib/benchmark-results.ts';
function fixture() {
  const r={n:1,N:2,rate:.5};
  return {
    strict_pass:{...r},hit_at_1:{...r},evidence_hit_at_3:{...r},context_evidence_rate:{...r},
    correct_abstention:{n:0,N:0,rate:null},false_abstention:{n:0,N:2,rate:0},
    valid_citations:{n:1,N:1,rate:1},tool_use_successful_runs:{n:1,N:1,rate:1},
    grounded_answer_normalized:{n:2,N:4,rate:.5},
    per_category_including_abstention:{text:{...r}},statuses:{answered:1,error:1},
    latency_ms_median:40,latency_ms_p95_nearest_rank:60,cost_usd_known_subtotal:.001,cost_unknown_cases:1,
    details:[{query_id:'test-1',passed:true,status:'answered',reviewed:true,reason:'Synthetic validation fixture.'},{query_id:'test-2',passed:false,status:'error',reviewed:false,reason:'Synthetic error.'}]
  };
}
test('accepts complete matching summary without changing the values',()=>{const f=fixture();assert.equal(checkRun(f,['test-1','test-2']),f);});
test('rejects missing or duplicate case IDs',()=>{const f=fixture();assert.throws(()=>checkRun(f,['test-1']));f.details[1].query_id='test-1';assert.throws(()=>checkRun(f,['test-1','test-2']));});
test('rejects mismatched pass count',()=>{const f=fixture();f.strict_pass.n=2;assert.throws(()=>checkRun(f,['test-1','test-2']));});
test('rejects a passing case without human review',()=>{const f=fixture();f.details[0].reviewed=false;assert.throws(()=>checkRun(f,['test-1','test-2']));});
test('rejects invalid cost and latency',()=>{for(const field of ['cost_usd_known_subtotal','latency_ms_median']){const f=fixture();f[field]=-1;assert.throws(()=>checkRun(f,['test-1','test-2']));}});
test('rejects missing metrics instead of fabricating zero',()=>{const f=fixture();delete f.valid_citations;assert.throws(()=>checkRun(f,['test-1','test-2']));});
