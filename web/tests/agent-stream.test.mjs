import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readAgentEvents, citationMarkdown } from '../src/lib/agent-stream.ts';

test('NDJSON survives one-byte chunks across Vietnamese UTF-8 and final line without LF', async () => {
  const expected = [{ event: 'loading', message: 'Đang đọc bằng chứng' }, { event: 'model_started', step: 1 }];
  const bytes = new TextEncoder().encode(expected.map(e => JSON.stringify(e)).join('\n'));
  const body = new ReadableStream({ start(c) { for (const b of bytes) c.enqueue(new Uint8Array([b])); c.close(); } });
  const received = [];
  for await (const event of readAgentEvents(body)) received.push(event);
  assert.deepEqual(received, expected);
});

test('malformed backend stream fails visibly instead of inventing an answer', async () => {
  const body = new ReadableStream({ start(c) { c.enqueue(new TextEncoder().encode('not json\n')); c.close(); } });
  await assert.rejects(async () => { for await (const event of readAgentEvents(body)) void event; }, SyntaxError);
});

test('only actual cited chunk IDs become source buttons', () => {
  const cited = 'fpt-ar2025:p010:chart01';
  const text = `[${cited}] [fpt-ar2025:p099:text01]`;
  assert.equal(citationMarkdown(text, [cited]), `[1](#source-${encodeURIComponent(cited)}) [fpt-ar2025:p099:text01]`);
});

test('abandoning a stream cancels the underlying request reader', async () => {
  let cancelled = false;
  const body = new ReadableStream({ start(c) { c.enqueue(new TextEncoder().encode('{"event":"model_started","step":1}\n')); }, cancel() { cancelled = true; } });
  for await (const event of readAgentEvents(body)) { assert.equal(event.event, 'model_started'); break; }
  assert.equal(cancelled, true);
});
