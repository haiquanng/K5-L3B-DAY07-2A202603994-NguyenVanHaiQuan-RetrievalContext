"""Build a LOCAL human-review page for one run (not for publishing: it shows crops of a non-redistributable PDF).

  python -m src.review_page --suite advanced --split test --run E2_gpt54_v4
  python -m src.review_page --suite advanced --split test --run chosen_B1

Output: starter/results/review/review.<suite>.<split>.<run>.html (git-ignored). Open it in a browser.
Every label is pre-filled with a SUGGESTION (proxy evidence overlap + LLM judge) and human_confirmed=false; the
reviewer checks each case against the answer, the crops and the original page, edits, and clicks "Xác nhận".
"Xuất JSON" downloads reviews in the exact format of benchmark/fpt_2025/tools.py score.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.agent import distinctive_numbers  # noqa: E402
from src.eval_retrieval import evidence_in, load  # noqa: E402

OUT = ROOT / "starter" / "results" / "review"
DOC = "fpt-ar2025"


def rel_from_out(p: str | None) -> str | None:
    return os.path.relpath(ROOT / p, OUT) if p else None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--suite", required=True)
    ap.add_argument("--split", required=True)
    ap.add_argument("--run", required=True)
    a = ap.parse_args()
    run_dir = ROOT / "starter" / "results" / "agent" / f"{a.suite}.{a.split}.{a.run}"
    traces = {t["query_id"]: t for t in json.loads((run_dir / "traces.json").read_text())}
    _, gold = load(a.suite, a.split)
    chunks = {}
    for line in (ROOT / "starter" / "results" / "mm" / DOC / "chunks.jsonl").read_text().splitlines():
        c = json.loads(line)
        chunks[c["chunk_id"]] = c
    pages_dir = ROOT / "starter" / "data" / "mm" / DOC / "pages"

    def as_hit(cid: str, ctx: dict) -> dict | None:
        c = ctx.get(cid) or chunks.get(cid)
        if not c:
            return None
        return {"chunk_id": cid, "text": c.get("text") or c.get("content", ""), "bbox": c["bbox"], "pdf_page": c["pdf_page"],
                "printed_page": c.get("printed_page") or c.get("metadata", {}).get("printed_page"), "kind": c["kind"],
                "crop_path": c["crop_path"]}

    cases = []
    for qid, g in gold.items():
        t = traces.get(qid, {"status": "missing", "answer": "", "citations": [], "context": [], "events": []})
        ctx = {c["chunk_id"]: c for c in t.get("context", [])}
        j = t.get("judge", {})
        ranking = [h for h in (as_hit(r["chunk_id"], ctx) for r in t.get("original_query_ranking", [])[:3]) if h]
        ctx_hits = [h for h in (as_hit(cid, ctx) for cid in t.get("context_ids", [])) if h]
        ev1 = sorted(evidence_in(ranking[:1], g)) if ranking else []
        ev3 = sorted(set(ev1) | evidence_in(ranking, g))
        ctx_ev = sorted(evidence_in(ctx_hits, g))
        nums = distinctive_numbers(t.get("answer", ""))
        cites = []
        for cid in t.get("citations", []):
            h = as_hit(cid, ctx)
            ev = sorted(evidence_in([h], g)) if h else []
            has_num = bool(h and nums and any(n in h["text"] for n in nums))
            cites.append({"id": cid, "suggest_supports": bool(ev) or has_num, "suggest_locatable": bool(h),
                          "suggest_evidence": [e for e in ev if e in ctx_ev],
                          "pdf_page": h["pdf_page"] if h else None, "printed_page": h["printed_page"] if h else None,
                          "kind": h["kind"] if h else None, "crop": rel_from_out(h["crop_path"]) if h else None,
                          "text": (h["text"][:1800] if h else "")})
        if g["answerable"]:
            ctx_grade = 2 if any(set(gr["all_of"]) <= set(ctx_ev) for gr in g["evidence_groups"]) else (1 if ctx_ev else 0)
        else:
            ctx_grade = None
        cases.append({
            "query_id": qid, "category": g["primary_category"], "answerable": g["answerable"], "question": g["question"],
            "expected_answer": g["expected_answer"], "required_facts": g.get("required_facts", []),
            "missing": (g.get("absence_check") or {}).get("missing_information"),
            "groups": [gr["all_of"] for gr in g["evidence_groups"]],
            "gold": [{"id": e["id"], "pdf_page": e["pdf_page"], "printed_page": e.get("printed_page"), "locator": e.get("locator"),
                      "quotes": e.get("quotes", []), "visual": e.get("visual_description"),
                      "page_img": rel_from_out(str((pages_dir / f"p{e['pdf_page']:03d}.jpg").relative_to(ROOT)))} for e in g["gold"]],
            "status": t.get("status"), "answer": t.get("answer", ""), "error": t.get("error"),
            "searches": [e.get("query") for e in t.get("events", []) if e.get("event") == "search"],
            "ranking": [{"chunk_id": h["chunk_id"], "pdf_page": h["pdf_page"], "kind": h["kind"], "crop": rel_from_out(h["crop_path"]),
                         "text": h["text"][:500]} for h in ranking],
            "judge_reason": j.get("reason"),
            "suggest": {"answer_grade": (j.get("grade") if g["answerable"] else None) if t.get("status") == "answered" else (0 if g["answerable"] else None),
                        "context_grade": ctx_grade,
                        "abstention_correct": None if g["answerable"] else bool(t.get("status") == "abstain" and j.get("abstain_ok")),
                        "unsupported_claims": bool(j.get("unsupported")) if j else False,
                        "retrieval_evidence_at_1": ev1, "retrieval_evidence_at_3": ev3, "context_evidence": ctx_ev},
            "citations": cites,
        })
    # Minimum sample required by BENCHMARK.md (>= 5 answerable + 2 insufficient-evidence test cases), drawn with a
    # fixed seed and spread over categories, so the sample is reproducible and not hand-picked.
    import random
    rng = random.Random(f"{a.suite}.{a.split}.min-sample.v1")
    ans = [c for c in cases if c["answerable"]]
    by_cat: dict[str, list] = {}
    for c in ans:
        by_cat.setdefault(c["category"], []).append(c)
    picked = [rng.choice(sorted(v, key=lambda x: x["query_id"])) for _, v in sorted(by_cat.items())]
    rest = sorted((c for c in ans if c not in picked), key=lambda x: x["query_id"])
    picked += rng.sample(rest, max(0, 5 - len(picked)))
    picked += rng.sample(sorted((c for c in cases if not c["answerable"]), key=lambda x: x["query_id"]), 2)
    for c in cases:
        c["in_sample"] = c in picked
    OUT.mkdir(parents=True, exist_ok=True)
    title = f"Review {a.suite}/{a.split} · {a.run}"
    data = json.dumps({"title": title, "key": f"review:{a.suite}.{a.split}.{a.run}", "cases": cases}, ensure_ascii=False)
    page = TEMPLATE.replace("__TITLE__", html.escape(title)).replace("__DATA__", data.replace("</", "<\\/"))
    dest = OUT / f"review.{a.suite}.{a.split}.{a.run}.html"
    dest.write_text(page, encoding="utf-8")
    print(dest)


TEMPLATE = r"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#1d2330;--muted:#5d6678;--line:#dfe3ea;--accent:#2457c5;--ok:#1f7a45;--warn:#a15c00;--bad:#b42318;--chip:#eef2f8}
@media (prefers-color-scheme:dark){:root{--bg:#12151b;--card:#1b1f27;--ink:#e6e9ef;--muted:#9aa3b2;--line:#2c323d;--accent:#7aa2ff;--ok:#5cc28a;--warn:#e0a345;--bad:#f07a6f;--chip:#252b36}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
header{position:sticky;top:0;z-index:5;background:var(--card);border-bottom:1px solid var(--line);padding:10px 16px;display:flex;flex-wrap:wrap;gap:8px;align-items:center}
header h1{font-size:15px;margin:0 12px 0 0}input,select,textarea,button{font:inherit;color:inherit}
input[type=text],select,textarea{background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:5px 8px}
button{border:1px solid var(--line);background:var(--chip);border-radius:6px;padding:5px 10px;cursor:pointer}
button.primary{background:var(--accent);color:#fff;border-color:var(--accent);border-radius:12px;padding:7px 14px}
main{max-width:1180px;margin:0 auto;padding:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin:0 0 16px}
.card.confirmed{border-color:var(--ok)}.row{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media (max-width:820px){.row{grid-template-columns:1fr}}
h2{font-size:15px;margin:0 0 6px}h3{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);margin:14px 0 6px}
.tag{display:inline-block;background:var(--chip);border-radius:4px;padding:1px 6px;font-size:12px;margin-right:4px}
.st-answered{color:var(--ok)}.st-abstain{color:var(--warn)}.st-error,.st-missing,.st-timeout{color:var(--bad)}
pre{white-space:pre-wrap;word-break:break-word;background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:8px;margin:0;max-height:260px;overflow:auto;font-size:12.5px}
.cite{border:1px solid var(--line);border-radius:12px;padding:10px;margin:8px 0}
.cite img,.rank img{max-width:100%;border:1px solid var(--line);border-radius:6px;background:#fff;cursor:zoom-in}
.labels{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;margin-top:8px}
.labels fieldset{border:1px solid var(--line);border-radius:6px;padding:6px 10px}legend{font-size:12px;color:var(--muted)}
.sugg{font-size:12px;color:var(--muted)}.muted{color:var(--muted)}a{color:var(--accent)}
.flag{font-size:12px;padding:2px 6px;border-radius:4px;background:var(--chip)}.flag.need{color:var(--warn)}.flag.done{color:var(--ok)}
dialog{max-width:95vw;max-height:95vh;border:0;border-radius:12px;padding:0}dialog img{max-width:92vw;max-height:90vh;display:block}
</style></head><body>
<header><h1>__TITLE__</h1>
<label>Người chấm <input type="text" id="reviewer" placeholder="Họ tên" size="16"></label>
<select id="filter"><option value="sample">Mẫu tối thiểu (7 câu)</option><option value="all">Tất cả</option><option value="todo">Chưa xác nhận</option><option value="fail">Gợi ý: có vấn đề</option></select>
<span id="progress" class="muted"></span>
<button id="import">Nhập JSON</button><input type="file" id="file" accept=".json" hidden>
<button class="primary" id="export">Xuất JSON</button></header>
<main id="list"></main><dialog id="zoom"><img alt=""></dialog>
<script id="data" type="application/json">__DATA__</script>
<script>
const D=JSON.parse(document.getElementById('data').textContent),C=D.cases;
const store={get(){try{return JSON.parse(localStorage.getItem(D.key)||'{}')}catch(e){return{}}},set(v){try{localStorage.setItem(D.key,JSON.stringify(v))}catch(e){}}};
let S=store.get(); // query_id -> review
function init(c){const s=c.suggest;return{query_id:c.query_id,reviewer:'',human_confirmed:false,reason:c.judge_reason?('[gợi ý judge] '+c.judge_reason):'',
 answer_grade:s.answer_grade,context_grade:s.context_grade,abstention_correct:s.abstention_correct,unsupported_claims:s.unsupported_claims,
 retrieval_evidence_at_1:[...s.retrieval_evidence_at_1],retrieval_evidence_at_3:[...s.retrieval_evidence_at_3],context_evidence:[...s.context_evidence],
 citations:c.citations.map(x=>({id:x.id,supports_answer:x.suggest_supports,source_locatable:x.suggest_locatable,evidence_ids:[...x.suggest_evidence]}))}}
C.forEach(c=>{if(!S[c.query_id])S[c.query_id]=init(c)});
const rv=document.getElementById('reviewer');rv.value=(Object.values(S).find(r=>r.reviewer)||{}).reviewer||'';
const esc=t=>String(t??'').replace(/[&<>"]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]));
function problem(c){const r=S[c.query_id];return c.status!=='answered'&&c.answerable||(c.answerable?(r.answer_grade!==2||r.context_grade!==2||r.unsupported_claims||r.citations.some(x=>!x.supports_answer)):(!r.abstention_correct||r.unsupported_claims))}
function chk(name,ids,sel,qid){return ids.map(id=>`<label><input type="checkbox" data-q="${qid}" data-f="${name}" value="${id}" ${sel.includes(id)?'checked':''}> ${id.split(':').pop()}</label>`).join(' ')}
function radios(qid,f,opts,val){return opts.map(([v,l])=>`<label><input type="radio" name="${qid}-${f}" data-q="${qid}" data-f="${f}" value="${v}" ${String(val)===String(v)?'checked':''}> ${l}</label>`).join(' ')}
function card(c){const r=S[c.query_id],ids=c.gold.map(g=>g.id),q=c.query_id;
 const gold=c.gold.map(g=>`<div class="cite"><b>${g.id.split(':').pop()}</b> · PDF ${g.pdf_page} (in ${esc(g.printed_page)}) · ${esc(g.locator)} · <a href="${g.page_img}" target="_blank">mở trang</a><div class="muted">quotes: ${g.quotes.map(esc).join(' | ')}</div>${g.visual?`<div class="muted">${esc(g.visual)}</div>`:''}</div>`).join('');
 const cites=c.citations.map((x,i)=>{const rc=r.citations[i];return `<div class="cite"><b>[${i+1}] ${esc(x.id.split(':').slice(1).join(':'))}</b> · ${x.kind} · PDF ${x.pdf_page} (in ${esc(x.printed_page)})
  ${x.crop?`<div><img loading="lazy" src="${x.crop}" alt="crop"></div>`:''}<details><summary class="muted">text chunk</summary><pre>${esc(x.text)}</pre></details>
  <div class="labels"><fieldset><legend>supports_answer <span class="sugg">(gợi ý ${x.suggest_supports})</span></legend>${radios(q,'c'+i+'.supports_answer',[[true,'đúng'],[false,'sai']],rc.supports_answer)}</fieldset>
  <fieldset><legend>source_locatable</legend>${radios(q,'c'+i+'.source_locatable',[[true,'có'],[false,'không']],rc.source_locatable)}</fieldset>
  <fieldset><legend>evidence_ids</legend>${chk('c'+i+'.evidence_ids',ids,rc.evidence_ids,q)||'<span class=muted>—</span>'}</fieldset></div></div>`}).join('');
 const rank=c.ranking.map((h,i)=>`<div class="rank"><span class="tag">#${i+1}</span>${esc(h.chunk_id.split(':').slice(1).join(':'))} · PDF ${h.pdf_page}<details><summary class="muted">xem</summary>${h.crop?`<img loading="lazy" src="${h.crop}" alt="">`:''}<pre>${esc(h.text)}</pre></details></div>`).join('');
 return `<section class="card ${r.human_confirmed?'confirmed':''}" id="${q}"><h2>${q.split('-').pop()} · <span class="tag">${c.category}</span>${c.answerable?'<span class="tag">có đáp án</span>':'<span class="tag">thiếu evidence</span>'}${c.in_sample?'<span class="tag">mẫu tối thiểu</span>':''}
  <span class="flag ${r.human_confirmed?'done':'need'}">${r.human_confirmed?'đã xác nhận':'chưa xác nhận'}</span></h2>
 <div><b>Câu hỏi:</b> ${esc(c.question)}</div>
 <div class="row"><div><h3>Đáp án chuẩn</h3><pre>${esc(c.expected_answer)}${c.required_facts.length?'\n\nÝ bắt buộc:\n- '+c.required_facts.map(esc).join('\n- '):''}${c.missing?'\n\nThông tin thiếu: '+esc(c.missing):''}</pre>
  ${c.groups.length?`<div class="muted">Nhóm evidence (OR giữa nhóm, AND trong nhóm): ${c.groups.map(g=>'['+g.map(x=>x.split(':').pop()).join(' + ')+']').join(' hoặc ')}</div>`:''}${gold}</div>
 <div><h3>Agent · <span class="st-${c.status}">${c.status}</span></h3><pre>${esc(c.answer||c.error||'')}</pre><div class="muted">Search: ${c.searches.map(esc).join(' ‖ ')}</div>
  <h3>Top-3 câu hỏi gốc</h3>${rank||'<span class=muted>—</span>'}</div></div>
 <h3>Citation (${c.citations.length})</h3>${cites||'<span class=muted>Không có citation</span>'}
 <h3>Nhãn</h3><div class="labels">
 ${c.answerable?`<fieldset><legend>answer_grade <span class="sugg">(gợi ý ${c.suggest.answer_grade})</span></legend>${radios(q,'answer_grade',[[2,'2'],[1,'1'],[0,'0']],r.answer_grade)}</fieldset>
 <fieldset><legend>context_grade <span class="sugg">(gợi ý ${c.suggest.context_grade})</span></legend>${radios(q,'context_grade',[[2,'2'],[1,'1'],[0,'0']],r.context_grade)}</fieldset>`
 :`<fieldset><legend>abstention_correct <span class="sugg">(gợi ý ${c.suggest.abstention_correct})</span></legend>${radios(q,'abstention_correct',[[true,'đúng'],[false,'sai']],r.abstention_correct)}</fieldset>`}
 <fieldset><legend>unsupported_claims <span class="sugg">(gợi ý ${c.suggest.unsupported_claims})</span></legend>${radios(q,'unsupported_claims',[[false,'không'],[true,'có']],r.unsupported_claims)}</fieldset>
 ${c.answerable?`<fieldset><legend>retrieval_evidence_at_1</legend>${chk('retrieval_evidence_at_1',ids,r.retrieval_evidence_at_1,q)}</fieldset>
 <fieldset><legend>retrieval_evidence_at_3</legend>${chk('retrieval_evidence_at_3',ids,r.retrieval_evidence_at_3,q)}</fieldset>
 <fieldset><legend>context_evidence</legend>${chk('context_evidence',ids,r.context_evidence,q)}</fieldset>`:''}</div>
 <h3>Lý do</h3><textarea data-q="${q}" data-f="reason" rows="2" style="width:100%">${esc(r.reason)}</textarea>
 <div style="margin-top:8px"><button class="primary" data-confirm="${q}">${r.human_confirmed?'Bỏ xác nhận':'Xác nhận'}</button></div></section>`}
function render(){const f=document.getElementById('filter').value,list=document.getElementById('list');
 list.innerHTML=C.filter(c=>f==='all'||(f==='sample'&&c.in_sample)||(f==='todo'&&!S[c.query_id].human_confirmed)||(f==='fail'&&problem(c))).map(card).join('');
 const n=C.filter(c=>S[c.query_id].human_confirmed).length,m=C.filter(c=>c.in_sample&&S[c.query_id].human_confirmed).length;
 document.getElementById('progress').textContent=`Mẫu: ${m}/${C.filter(c=>c.in_sample).length} · Tổng: ${n}/${C.length} đã xác nhận`}
function setPath(r,f,v){const m=f.match(/^c(\d+)\.(.+)$/);if(m){r.citations[+m[1]][m[2]]=v}else r[f]=v}
function getPath(r,f){const m=f.match(/^c(\d+)\.(.+)$/);return m?r.citations[+m[1]][m[2]]:r[f]}
document.addEventListener('change',e=>{const t=e.target,q=t.dataset.q,f=t.dataset.f;if(!q||!f)return;const r=S[q];
 if(t.type==='radio'){setPath(r,f,t.value==='true'?true:t.value==='false'?false:Number(t.value))}
 else if(t.type==='checkbox'){const a=new Set(getPath(r,f));t.checked?a.add(t.value):a.delete(t.value);setPath(r,f,[...a].sort());
  if(f==='retrieval_evidence_at_1'&&t.checked&&!r.retrieval_evidence_at_3.includes(t.value)){r.retrieval_evidence_at_3=[...r.retrieval_evidence_at_3,t.value].sort();render()}}
 store.set(S)});
document.addEventListener('input',e=>{const t=e.target;if(t.dataset.f==='reason'){S[t.dataset.q].reason=t.value;store.set(S)}});
document.addEventListener('click',e=>{const t=e.target;if(t.dataset.confirm){const r=S[t.dataset.confirm],c=C.find(x=>x.query_id===t.dataset.confirm);
  if(!r.human_confirmed){if(!rv.value.trim()){alert('Nhập tên người chấm trước.');return}
   const miss=c.answerable?(r.answer_grade==null||r.context_grade==null):(r.abstention_correct==null);if(miss||!r.reason.trim()){alert('Điền đủ nhãn và lý do.');return}
   r.reason=r.reason.replace(/^\[gợi ý judge\] /,'');r.reviewer=rv.value.trim()}
  r.human_confirmed=!r.human_confirmed;store.set(S);render();document.getElementById(c.query_id)?.scrollIntoView({block:'start'})}
 if(t.tagName==='IMG'&&t.closest('.cite,.rank')){const d=document.getElementById('zoom');d.querySelector('img').src=t.src;d.showModal()}});
document.getElementById('zoom').addEventListener('click',e=>e.currentTarget.close());
document.getElementById('filter').addEventListener('change',render);
rv.addEventListener('input',()=>{Object.values(S).forEach(r=>{if(r.human_confirmed)r.reviewer=rv.value.trim()});store.set(S)});
document.getElementById('export').addEventListener('click',()=>{const out=C.map(c=>{const r=S[c.query_id];return{query_id:r.query_id,reviewer:r.reviewer||'',human_confirmed:!!r.human_confirmed,reason:r.reason||'',
 answer_grade:r.answer_grade,context_grade:r.context_grade,abstention_correct:r.abstention_correct,unsupported_claims:r.unsupported_claims,
 retrieval_evidence_at_1:r.retrieval_evidence_at_1,retrieval_evidence_at_3:r.retrieval_evidence_at_3,context_evidence:r.context_evidence,citations:r.citations}});
 const b=new Blob([JSON.stringify(out,null,1)],{type:'application/json'}),u=URL.createObjectURL(b),a=document.createElement('a');
 a.href=u;a.download=D.key.replace('review:','')+'.reviews.json';a.click();URL.revokeObjectURL(u)});
document.getElementById('import').addEventListener('click',()=>document.getElementById('file').click());
document.getElementById('file').addEventListener('change',async e=>{const f=e.target.files[0];if(!f)return;try{const arr=JSON.parse(await f.text());let n=0;
 arr.forEach(x=>{const c=C.find(y=>y.query_id===x.query_id);if(!c)return;const base=S[x.query_id];
  const filled=x.human_confirmed||x.answer_grade!=null||x.abstention_correct!=null||(x.reason||'').trim();if(!filled)return;
  if(!x.citations||x.citations.length!==c.citations.length)x.citations=base.citations;S[x.query_id]={...base,...x};n++});
 store.set(S);render();alert('Đã nhập '+n+' mục đã điền (mục trống giữ gợi ý).')}catch(err){alert('File không hợp lệ: '+err)}});
render();
</script></body></html>"""

if __name__ == "__main__":
    main()
