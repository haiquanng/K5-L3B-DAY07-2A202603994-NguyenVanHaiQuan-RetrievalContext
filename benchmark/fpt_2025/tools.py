#!/usr/bin/env python3
"""Offline benchmark packaging, validation and aggregation of human reviews.
No model calls. Gold and review labels must never be sent to the agent.
"""
import argparse
import ast
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import statistics
import unicodedata

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent.parent
SOURCE_HASH = '9449a7251d126b635988974dbc72c2773c7fff39f4e5e858b5f7d3928b4e0e6c'

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def write(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def require(condition, message):
    if not condition:
        raise ValueError(message)

def norm(text):
    return ' '.join(unicodedata.normalize('NFC', text).split())

def arithmetic(expression):
    """Only arithmetic constants; exact integer/decimal intermediates."""
    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return Fraction(str(node.value))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -visit(node.operand)
        if isinstance(node, ast.BinOp):
            a, b = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Add): return a + b
            if isinstance(node.op, ast.Sub): return a - b
            if isinstance(node.op, ast.Mult): return a * b
            if isinstance(node.op, ast.Div): return a / b
        raise ValueError('Unsupported arithmetic expression')
    return visit(ast.parse(expression, mode='eval').body)

def indexed(rows, allowed, label):
    result = {}
    for row in rows:
        qid = row.get('query_id')
        require(qid in allowed, f'{label}: unknown/out-of-split ID {qid}')
        require(qid not in result, f'{label}: duplicate ID {qid}')
        result[qid] = row
    return result

def complete(case, evidence_ids):
    found = set(evidence_ids)
    return any(set(g['all_of']) <= found for g in case['evidence_groups'])

def ratio(n, d):
    return {'n': n, 'N': d, 'rate': n / d if d else None}

def validate(pdf=None, check_freeze=True):
    cases = read(BASE / 'cases.json')
    systems = read(BASE / 'system_cases.json')
    require(len(cases) == 240 and len(systems) == 60, 'Expected 240 questions + 60 system cases')
    for field in ('id', 'fact_key', 'question'):
        require(len({c[field] for c in cases}) == len(cases), 'Duplicate ' + field)
    evidence_count = 0
    calculation_count = 0
    document = None
    if pdf:
        require(digest(pdf) == SOURCE_HASH, 'PDF hash does not match frozen source')
        import fitz
        document = fitz.open(pdf)
        require(len(document) == 232, 'Expected 232 physical PDF pages')
    for suite, counts in [('basic', {'text': 24, 'table': 8, 'multi_hop': 8}),
                          ('advanced', {'text': 10, 'table': 16, 'chart': 10, 'image': 8, 'multi_hop': 12})]:
        for split in ('dev', 'test'):
            selected = [c for c in cases if c['suite'] == suite and c['split'] == split]
            total, answerable = (50, 40) if suite == 'basic' else (70, 56)
            require(len(selected) == total, f'{suite}/{split}: incorrect total')
            require(sum(c['answerable'] for c in selected) == answerable, 'Incorrect answerable count')
            require(Counter(c['primary_category'] for c in selected if c['answerable']) == counts, 'Category coverage mismatch')
            public = read(BASE / 'queries' / f'{suite}.{split}.json')
            expected = [{'id': c['id'], 'question': c['question']} for c in selected]
            require(public == expected, 'Public query file contains leakage or differs from canonical cases')
            require(read(BASE / 'gold' / f'{suite}.{split}.json') == selected, 'Gold export is stale')
    for c in cases:
        qid = c['id']
        if not c['answerable']:
            require(not c['gold'] and not c['evidence_groups'], qid + ': abstention has positive gold')
            require(bool(c.get('absence_check', {}).get('missing_information')), qid + ': missing absence rationale')
            require(c['absence_check']['related_pdf_pages'], qid + ': missing absence audit pages')
            continue
        require(c['required_facts'] and c['gold'] and c['evidence_groups'], qid + ': missing answer/evidence')
        ids = {g['id'] for g in c['gold']}
        require(len(ids) == len(c['gold']), qid + ': duplicate evidence ID')
        for group in c['evidence_groups']:
            require(group['all_of'] and set(group['all_of']) <= ids, qid + ': bad evidence group')
        if c['primary_category'] == 'multi_hop':
            require(len({g['pdf_page'] for g in c['gold']}) >= 2, qid + ': multi-hop needs two pages')
        for gold in c['gold']:
            evidence_count += 1
            p = gold['pdf_page']
            require(1 <= p <= 232, qid + ': page out of range')
            require(gold['source_id'] == 'fpt-ar2025-9449a725', qid + ': wrong source')
            require(gold['printed_page'] == str(p-1).zfill(2), qid + ': wrong printed page')
            x0, y0, x1, y1 = gold['bbox_pt']
            require(0 <= x0 < x1 <= 1058.28 and 0 <= y0 < y1 <= 595.28, qid + ': invalid bbox')
            require(gold['locator'] and (gold['quotes'] or gold.get('visual_description')), qid + ': missing locator')
            if document:
                text = norm(document[p-1].get_text())
                for quote in gold['quotes']:
                    require(quote and norm(quote) in text, f'{qid}: anchor absent at PDF page {p}: {quote}')
        for calculation in c.get('calculations', []):
            calculation_count += 1
            delta = abs(arithmetic(calculation['expression']) - Fraction(str(calculation['result'])))
            require(delta <= Fraction(str(calculation['absolute_tolerance'])), qid + ': arithmetic mismatch')
    require(len({s['id'] for s in systems}) == 60, 'Duplicate system case ID')
    require(all(s['steps'] and s['expected'] and s['status'] == 'not_run' for s in systems), 'Invalid system specifications')
    if check_freeze:
        for name, sha in read(BASE / 'manifest.json')['frozen_files'].items():
            require(digest(BASE / name) == sha, 'Frozen file changed: ' + name)
    return {'questions': len(cases), 'system_specifications': len(systems), 'evidence_entries': evidence_count,
            'arithmetic_checks': calculation_count, 'pdf_hash_and_text_anchors_checked': bool(pdf),
            'benchmark_executed': False, 'system_tests_executed': False}

def build():
    """Editorial export. Never run this to silently replace a frozen benchmark."""
    cases = read(BASE / 'cases.json')
    systems = read(BASE / 'system_cases.json')
    source = {'source_id': 'fpt-ar2025-9449a725', 'title': 'FPT – Báo cáo thường niên 2025',
              'path': 'pdf/BCTN_2025_ad403f779b.pdf', 'sha256': SOURCE_HASH, 'physical_pages': 232,
              'provenance': 'Tệp do người dùng cung cấp trong workspace; không khẳng định hash này được tải từ website.',
              'official_reference': 'https://fpt.com/vi/nha-dau-tu/bao-cao-thuong-nien',
              'rights': 'Dùng bản local cho lab; public access không tự động cho phép tái phân phối PDF.',
              'coordinates': 'PDF points, origin top-left; bbox là vùng điều hướng, locator xác định ô/nhánh cần đọc.',
              'page_numbering': 'pdf_page bắt đầu từ 1; trang in = pdf_page - 1 cho trang PDF 2–231; bìa không có số in.'}
    write(BASE / 'source.json', source)
    for suite in ('basic', 'advanced'):
        for split in ('dev', 'test'):
            subset = [c for c in cases if c['suite'] == suite and c['split'] == split]
            write(BASE / 'queries' / f'{suite}.{split}.json', [{'id': c['id'], 'question': c['question']} for c in subset])
            write(BASE / 'gold' / f'{suite}.{split}.json', subset)
    lines = ['# 240 câu hỏi FPT 2025', '', 'File cho người biên soạn/người chấm. Không đưa file này vào index hoặc agent.', '',
             'Trang dưới đây là **trang PDF vật lý, bắt đầu từ 1**. Đáp án chấp nhận diễn đạt tương đương, phải giữ đủ số liệu, đơn vị và điều kiện.', '']
    for c in cases:
        lines += [f'## {c["id"]} — {c["primary_category"]}', '', c['question'], '', '**Đáp án/hành vi:** ' + c['expected_answer'], '']
        if c['answerable']:
            for g in c['gold']:
                lines += [f'- PDF {g["pdf_page"]} (trang in {g["printed_page"]}), {g["id"]}: {g["locator"]}.']
            lines += ['', 'Phải có **đủ** evidence trong một nhóm `all_of`; các nhóm khác nhau là phương án thay thế.', '']
            for calc in c.get('calculations', []):
                lines += [f'Phép tính: `{calc["expression"]}` = {calc["result"]} {calc["unit"]}; sai số tuyệt đối ≤ {calc["absolute_tolerance"]}.', '']
        else:
            a = c['absence_check']
            lines += ['**Kiểm tra thiếu evidence:** ' + a['missing_information'] + '.', '',
                      'Đọc các trang liên quan: ' + ', '.join(map(str, a['related_pdf_pages'])) + '; rà toàn bộ tài liệu bằng: ' + ', '.join(a['full_document_search_terms']) + '.', '',
                      'Từ chối phần được hỏi; cho phép ngữ cảnh có nguồn nhưng không suy đoán dữ liệu còn thiếu.', '']
    (BASE / 'QUESTION_CASEBOOK.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    lines = ['# 60 ca kiểm thử hệ thống', '', '**Trạng thái: chưa chạy.** Đây là đặc tả tích hợp/thủ công, không phải 60 unit test đã pass.', '']
    for c in systems:
        lines += [f'## {c["id"]} — {c["title"]}', '', f'Nhóm: {c["area"]}. Yêu cầu: {c["requirement"]}.', '',
                  '**Chuẩn bị:** ' + c['preconditions'], '', '**Thao tác:**', '']
        lines += [f'{i}. {step}' for i, step in enumerate(c['steps'], 1)]
        lines += ['', '**Đạt khi:**', ''] + ['- ' + s for s in c['expected']] + ['']
    (BASE / 'SYSTEM_CASEBOOK.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    frozen = ['cases.json', 'system_cases.json', 'source.json', 'QUESTION_CASEBOOK.md', 'SYSTEM_CASEBOOK.md']
    frozen += [str(p.relative_to(BASE)) for folder in ('queries', 'gold') for p in sorted((BASE/folder).glob('*.json'))]
    write(BASE / 'manifest.json', {'version': '1.0.0', 'status': 'authored; no agent runs; independent review pending',
                                 'frozen_files': {name: digest(BASE/name) for name in frozen},
                                 'note': 'Record code commit, model, index version/hash, settings and this manifest hash BEFORE test. Rebuild requires a new published benchmark version.'})

def review_template(cases):
    return [{'query_id': c['id'], 'reviewer': '', 'human_confirmed': False, 'reason': '',
             'answer_grade': None, 'context_grade': None, 'abstention_correct': None,
             'unsupported_claims': None, 'retrieval_evidence_at_1': [], 'retrieval_evidence_at_3': [],
             'context_evidence': [], 'citations': []} for c in cases]

def score(cases, traces, reviews):
    """Aggregate independent human labels, never infer semantic correctness from IDs."""
    allowed = {c['id'] for c in cases}
    require(len(allowed) == len(cases) and cases, 'Cases must be unique and nonempty')
    ts, rs = indexed(traces, allowed, 'traces'), indexed(reviews, allowed, 'reviews')
    details = []
    for c in cases:
        qid = c['id']; t = ts.get(qid, {}); r = rs.get(qid, {})
        status = t.get('status', 'missing')
        require(status in ('answered', 'abstain', 'error', 'timeout', 'missing'), qid + ': bad status')
        for field in ('elapsed_ms', 'cost_usd'):
            val = t.get(field)
            require(val is None or (type(val) in (int, float) and math.isfinite(val) and val >= 0), qid + ': invalid ' + field)
        reviewed = r.get('human_confirmed') is True and bool(r.get('reviewer')) and bool(r.get('reason'))
        d = {'query_id': qid, 'category': c['primary_category'], 'answerable': c['answerable'], 'status': status,
             'reviewed': reviewed, 'passed': False, 'hit1': False, 'hit3': False, 'full_evidence_at_3': False,
             'context_complete': False, 'answer_grade': 0, 'context_grade': 0, 'valid_citations': 0,
             'citation_count': len(t.get('citations', [])), 'tool_use': any(e.get('event', e.get('action')) == 'search' for e in t.get('events', [])),
             'search_calls': sum(e.get('event', e.get('action')) == 'search' for e in t.get('events', [])),
             'reason': r.get('reason') or 'Chưa có review được người chấm xác nhận / chưa có output.'}
        if status in ('answered', 'abstain') and reviewed:
            require(type(r.get('unsupported_claims')) is bool, qid + ': unsupported_claims label required')
            known = {g['id'] for g in c['gold']}
            for field in ('retrieval_evidence_at_1', 'retrieval_evidence_at_3', 'context_evidence'):
                require(isinstance(r.get(field), list) and set(r[field]) <= known, qid + ': invalid evidence labels')
            require(set(r['retrieval_evidence_at_1']) <= set(r['retrieval_evidence_at_3']), qid + ': top-1 must be within top-3')
            d['hit1'] = bool(r['retrieval_evidence_at_1']); d['hit3'] = bool(r['retrieval_evidence_at_3'])
            d['full_evidence_at_3'] = complete(c, r['retrieval_evidence_at_3'])
            d['context_complete'] = complete(c, r['context_evidence'])
            require(len(set(t.get('citations', []))) == len(t.get('citations', [])), qid + ': duplicate citation ID')
            require([x.get('id') for x in r.get('citations', [])] == t.get('citations', []), qid + ': review every citation in trace order')
            supported = set()
            for citation in r['citations']:
                require(set(citation.get('evidence_ids', [])) <= known, qid + ': unknown cited evidence')
                ok = (citation['id'] in t.get('context_ids', []) and citation.get('supports_answer') is True
                      and citation.get('source_locatable') is True and set(citation.get('evidence_ids', [])) <= set(r['context_evidence']))
                if ok:
                    d['valid_citations'] += 1
                    supported.update(citation.get('evidence_ids', []))
            if c['answerable']:
                require(type(r.get('answer_grade')) is int and r['answer_grade'] in (0,1,2), qid + ': answer grade required')
                require(type(r.get('context_grade')) is int and r['context_grade'] in (0,1,2), qid + ': context grade required')
                d['answer_grade'] = r['answer_grade'] if status == 'answered' else 0
                d['context_grade'] = r['context_grade']
                d['passed'] = (status == 'answered' and bool(t.get('answer','').strip()) and d['answer_grade'] == 2
                               and d['context_grade'] == 2 and d['context_complete'] and complete(c, supported)
                               and d['valid_citations'] == d['citation_count'] and d['citation_count'] > 0
                               and r['unsupported_claims'] is False)
            else:
                require(type(r.get('abstention_correct')) is bool, qid + ': abstention label required')
                # An explicit, correct insufficient-evidence answer must be normalized to status abstain.
                d['passed'] = status == 'abstain' and bool(t.get('answer','').strip()) and r['abstention_correct'] and not r['unsupported_claims']
        details.append(d)
    ans = [d for d in details if d['answerable']]; neg = [d for d in details if not d['answerable']]
    successful = [d for d in details if d['status'] in ('answered','abstain')]
    groups = {}
    for label in sorted({d['category'] for d in details}):
        group = [d for d in details if d['category'] == label]
        groups[label] = ratio(sum(d['passed'] for d in group),len(group))
    known_costs = [t['cost_usd'] for t in traces if t.get('cost_usd') is not None]
    times = sorted(t['elapsed_ms'] for t in traces if t.get('elapsed_ms') is not None)
    passed = sum(d['passed'] for d in details)
    return {'strict_pass': ratio(passed,len(cases)), 'meets_90_percent_numeric_threshold': passed*10 >= len(cases)*9,
            'bonus_awarded': None, 'bonus_note': 'Numeric threshold only; index, submission, real-agent runs and independent audit also required.',
            'per_category_including_abstention': groups,
            'answerable_strict': ratio(sum(d['passed'] for d in ans),len(ans)),
            'correct_abstention': ratio(sum(d['passed'] for d in neg),len(neg)),
            'false_abstention': ratio(sum(d['status']=='abstain' for d in ans),len(ans)),
            'hit_at_1': ratio(sum(d['hit1'] for d in ans),len(ans)),
            'evidence_hit_at_3': ratio(sum(d['hit3'] for d in ans),len(ans)),
            'full_evidence_at_3': ratio(sum(d['full_evidence_at_3'] for d in ans),len(ans)),
            'context_evidence_rate': ratio(sum(d['context_complete'] for d in ans),len(ans)),
            'grounded_answer_grade_counts': dict(Counter(d['answer_grade'] for d in ans)),
            'grounded_answer_normalized': ratio(sum(d['answer_grade'] for d in ans),2*len(ans)),
            'context_grade_counts': dict(Counter(d['context_grade'] for d in ans)),
            'valid_citations': ratio(sum(d['valid_citations'] for d in details),sum(d['citation_count'] for d in details)),
            'tool_use_successful_runs': ratio(sum(d['tool_use'] for d in successful),len(successful)),
            'search_call_distribution': dict(Counter(d['search_calls'] for d in details)),
            'statuses': dict(Counter(d['status'] for d in details)), 'unreviewed': sum(not d['reviewed'] for d in details),
            'cost_usd_known_subtotal': sum(known_costs), 'cost_unknown_cases': len(cases)-len(known_costs),
            'latency_ms_median': statistics.median(times) if times else None,
            'latency_ms_p95_nearest_rank': times[math.ceil(.95*len(times))-1] if times else None,
            'latency_unknown_cases': len(cases)-len(times), 'details': details}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('build', help='Editorial export + freeze; changing released data requires a new version')
    v = sub.add_parser('validate'); v.add_argument('--pdf', type=Path)
    for command in ('review-template','score'):
        p = sub.add_parser(command)
        p.add_argument('--suite', choices=('basic','advanced'), required=True)
        p.add_argument('--split', choices=('dev','test'), required=True)
        p.add_argument('--output', type=Path, required=True)
        if command == 'score':
            p.add_argument('--traces', type=Path, required=True); p.add_argument('--reviews', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'build':
        build(); print(json.dumps(validate(), ensure_ascii=False))
    elif args.command == 'validate': print(json.dumps(validate(args.pdf), ensure_ascii=False, indent=2))
    else:
        validate()
        cases = read(BASE/'gold'/f'{args.suite}.{args.split}.json')
        result = review_template(cases) if args.command == 'review-template' else score(cases,read(args.traces),read(args.reviews))
        write(args.output,result)
        print('Wrote', args.output)

if __name__ == '__main__':
    main()
