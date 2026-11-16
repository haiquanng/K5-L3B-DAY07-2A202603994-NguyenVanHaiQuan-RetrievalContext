import assert from 'node:assert/strict';
import { test } from 'node:test';
import { proxyBackend } from '../src/lib/backend.ts';

test('cross-origin model requests are rejected before contacting Python', async () => {
  const response = await proxyBackend(new Request('http://localhost:3007/api/agent/chat', {
    method: 'POST', headers: { origin: 'https://other.example', 'content-type': 'application/json' }, body: '{}',
  }), '/chat', 'POST');
  assert.equal(response.status, 403);
});

test('unavailable backend returns an explicit 503 without internal error details', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => { throw new Error('private upstream details'); };
  try {
    const response = await proxyBackend(new Request('http://localhost:3007/api/agent/health'), '/health');
    assert.equal(response.status, 503);
    const body = await response.text();
    assert.match(body, /Chưa kết nối/);
    assert.doesNotMatch(body, /private upstream details/);
  } finally { globalThis.fetch = originalFetch; }
});

test('proxy preserves progress bytes, content type and upstream status', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => new Response('{"event":"model_started","step":1}\n', {
    headers: { 'content-type': 'application/x-ndjson' },
  });
  try {
    const response = await proxyBackend(new Request('http://localhost:3007/api/agent/chat', {
      method: 'POST', headers: { 'content-type': 'application/json' }, body: '{"question":"q"}',
    }), '/chat', 'POST');
    assert.equal(response.status, 200);
    assert.match(response.headers.get('content-type'), /ndjson/);
    assert.equal(await response.text(), '{"event":"model_started","step":1}\n');
  } finally { globalThis.fetch = originalFetch; }
});
