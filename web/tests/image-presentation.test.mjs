import assert from 'node:assert/strict';
import { test } from 'node:test';
import { inlineImages, sourceImages } from '../src/lib/image-presentation.ts';

const photo = { chunk_id: 'fpt-ar2025:p037:photo01', kind: 'photo' };
const table = { chunk_id: 'fpt-ar2025:p086:table01', kind: 'table' };

test('legacy saved chats move automatic attachments to the source panel', () => {
  const trace = { status: 'answered', answer_images: [photo, table] };
  assert.deepEqual(inlineImages(trace), []);
  assert.deepEqual(sourceImages(trace), [photo, table]);
});

test('default new answers retain source images without displaying them inline', () => {
  const trace = { status: 'answered', answer_images: [], source_images: [photo],
    image_presentation: { mode: 'sidebar', selected_chunk_ids: [] } };
  assert.deepEqual(inlineImages(trace), []);
  assert.deepEqual(sourceImages(trace), [photo]);
});

test('inline images follow validated selection instead of sending every available figure', () => {
  const trace = { status: 'answered', answer_images: [photo, table], source_images: [photo, table],
    image_presentation: { mode: 'inline', selected_chunk_ids: [photo.chunk_id] } };
  assert.deepEqual(inlineImages(trace), [photo]);
  assert.deepEqual(sourceImages(trace), [photo, table]);
});

test('empty and abstaining responses never display image attachments', () => {
  assert.deepEqual(inlineImages(undefined), []);
  assert.deepEqual(sourceImages(undefined), []);
  const trace = { status: 'abstain', answer_images: [photo], source_images: [photo],
    image_presentation: { mode: 'inline', selected_chunk_ids: [photo.chunk_id] } };
  assert.deepEqual(inlineImages(trace), []);
  assert.deepEqual(sourceImages(trace), []);
});
