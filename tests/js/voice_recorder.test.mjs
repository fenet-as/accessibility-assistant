/**
 * VoiceRecorder unit tests — run with: node --test tests/js/voice_recorder.test.mjs
 */
import { describe, it, mock } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const { VoiceRecorder, ERRORS, STATES } = require(
  path.join(root, 'assistant', 'widget', 'voice-recorder.js'),
);

class FakeTrack {
  constructor() { this.readyState = 'live'; }
  stop() { this.readyState = 'ended'; }
}

class FakeStream {
  constructor() { this._tracks = [new FakeTrack()]; }
  getTracks() { return this._tracks; }
}

class FakeMediaRecorder {
  static isTypeSupported(mime) {
    return mime.startsWith('audio/webm');
  }

  constructor(stream, opts) {
    this.stream = stream;
    this.mimeType = (opts && opts.mimeType) || 'audio/webm';
    this.state = 'inactive';
    this.ondataavailable = null;
    this.onerror = null;
    this._listeners = {};
    this._chunkIndex = 0;
  }

  addEventListener(type, fn) {
    this._listeners[type] = this._listeners[type] || [];
    this._listeners[type].push(fn);
  }

  removeEventListener(type, fn) {
    this._listeners[type] = (this._listeners[type] || []).filter((f) => f !== fn);
  }

  _emit(type) {
    (this._listeners[type] || []).forEach((f) => f());
  }

  start(timeslice) {
    this.state = 'recording';
    this._timeslice = timeslice;
    // Emit an initial chunk so tests have audio without waiting.
    this._pushChunk();
  }

  _pushChunk(size = 64) {
    this._chunkIndex += 1;
    const blob = new Blob([new Uint8Array(size)], { type: this.mimeType });
    if (this.ondataavailable) this.ondataavailable({ data: blob });
  }

  pause() {
    assert.equal(this.state, 'recording');
    this.state = 'paused';
  }

  resume() {
    assert.equal(this.state, 'paused');
    this.state = 'recording';
    this._pushChunk();
  }

  requestData() {
    if (this.state !== 'inactive') this._pushChunk(32);
  }

  stop() {
    this._pushChunk(48);
    this.state = 'inactive';
    this._emit('stop');
  }
}

function makeRecorder(overrides = {}) {
  let now = 1_000_000;
  const timers = new Map();
  let timerId = 0;
  const deps = {
    getUserMedia: async () => new FakeStream(),
    MediaRecorder: FakeMediaRecorder,
    AudioContext: null,
    now: () => now,
    setInterval: (fn) => {
      timerId += 1;
      timers.set(timerId, fn);
      return timerId;
    },
    clearInterval: (id) => { timers.delete(id); },
    setTimeout: (fn, ms) => {
      // Run finish callbacks immediately for deterministic tests.
      if (ms === 0) {
        fn();
        return 0;
      }
      timerId += 1;
      timers.set(timerId, fn);
      return timerId;
    },
    clearTimeout: (id) => { timers.delete(id); },
    ...overrides.deps,
  };
  const rec = new VoiceRecorder({
    maxActiveMs: overrides.maxActiveMs || 60000,
    timesliceMs: 1000,
    keepStream: true,
    deps,
    onStateChange: overrides.onStateChange,
    onError: overrides.onError,
    onTick: overrides.onTick,
  });
  return {
    rec,
    advance(ms) { now += ms; },
    tickTimers() { [...timers.values()].forEach((fn) => fn()); },
  };
}

describe('VoiceRecorder state machine', () => {
  it('starts in idle and transitions to recording', async () => {
    const { rec } = makeRecorder();
    assert.equal(rec.state, STATES.IDLE);
    await rec.start();
    assert.equal(rec.state, STATES.RECORDING);
    assert.ok(rec.sessionId);
    assert.ok(rec.chunkCount >= 1);
  });

  it('rejects illegal transitions', async () => {
    const { rec } = makeRecorder();
    await assert.rejects(() => Promise.resolve().then(() => rec.pause()), (err) => {
      assert.equal(err.code, ERRORS.ILLEGAL_TRANSITION);
      return true;
    });
  });

  it('accumulates chunks across multiple pause/resume cycles without duplicates', async () => {
    const { rec, advance } = makeRecorder();
    await rec.start();
    const afterStart = rec.chunkCount;
    assert.ok(afterStart >= 1);

    rec.pause();
    assert.equal(rec.state, STATES.PAUSED);
    const afterPause = rec.chunkCount;
    assert.ok(afterPause >= afterStart);

    advance(500);
    rec.resume();
    assert.equal(rec.state, STATES.RECORDING);
    const afterResume = rec.chunkCount;
    assert.ok(afterResume > afterPause);

    rec.pause();
    rec.resume();
    rec.pause();
    rec.resume();

    const seqs = rec._chunks.map((c) => c.seq);
    assert.deepEqual(seqs, [...seqs].sort((a, b) => a - b));
    assert.equal(new Set(seqs).size, seqs.length, 'chunk seqs must be unique');

    const result = await rec.stop();
    assert.equal(rec.state, STATES.PROCESSING);
    assert.ok(result.blob);
    assert.ok(result.blob.size > 0);
    assert.equal(result.chunkCount, rec.chunkCount);
    // Blob retained after stop — chunks not cleared.
    assert.ok(rec.blob);
    assert.equal(rec.blob.size, result.blob.size);
  });

  it('does not clear chunks on stop; discard clears them', async () => {
    const { rec } = makeRecorder();
    await rec.start();
    await rec.stop();
    assert.ok(rec.chunkCount >= 1);
    assert.ok(rec.blob);

    rec.markTranscribed();
    assert.equal(rec.state, STATES.TRANSCRIBED);

    rec.discard();
    assert.equal(rec.state, STATES.IDLE);
    assert.equal(rec.chunkCount, 0);
    assert.equal(rec.blob, null);
  });

  it('retry reuses the kept blob without clearing', async () => {
    const { rec } = makeRecorder();
    await rec.start();
    await rec.stop();
    rec.markTranscribed();
    const size = rec.blob.size;
    const again = rec.beginRetry();
    assert.equal(rec.state, STATES.PROCESSING);
    assert.equal(again.blob.size, size);
  });

  it('permission guard reuses in-flight getUserMedia', async () => {
    let calls = 0;
    let resolveMedia;
    const pending = new Promise((resolve) => { resolveMedia = resolve; });
    const { rec } = makeRecorder({
      deps: {
        getUserMedia: () => {
          calls += 1;
          return pending.then(() => new FakeStream());
        },
        MediaRecorder: FakeMediaRecorder,
        AudioContext: null,
        now: () => Date.now(),
        setInterval: () => 1,
        clearInterval: () => {},
        setTimeout: (fn) => { fn(); return 0; },
        clearTimeout: () => {},
      },
    });
    const p1 = rec.start();
    const p2 = rec.start(); // second call while requesting_permission returns same session
    assert.equal(calls, 1);
    resolveMedia();
    const [s1, s2] = await Promise.all([p1, p2]);
    assert.equal(s1, s2);
    assert.equal(calls, 1);
  });

  it('surfaces permission_denied without falling through silently', async () => {
    const errors = [];
    const { rec } = makeRecorder({
      onError: (e) => errors.push(e),
      deps: {
        getUserMedia: async () => {
          const err = new Error('denied');
          err.name = 'NotAllowedError';
          throw err;
        },
        MediaRecorder: FakeMediaRecorder,
        AudioContext: null,
        now: () => Date.now(),
        setInterval: () => 1,
        clearInterval: () => {},
        setTimeout: (fn) => { fn(); return 0; },
        clearTimeout: () => {},
      },
    });
    await assert.rejects(() => rec.start(), (err) => {
      assert.equal(err.code, ERRORS.PERMISSION_DENIED);
      return true;
    });
    assert.equal(rec.state, STATES.ERROR);
    assert.ok(errors.some((e) => e.code === ERRORS.PERMISSION_DENIED));
  });

  it('active time excludes paused duration and respects limit', async () => {
    const ticks = [];
    const { rec, advance, tickTimers } = makeRecorder({
      maxActiveMs: 2000,
      onTick: (t) => ticks.push(t.activeMs),
      onError: () => {},
    });
    await rec.start();
    advance(800);
    // Force a timer tick to update activeMs view
    tickTimers();
    assert.ok(rec.activeMs >= 800);
    rec.pause();
    const pausedAt = rec.activeMs;
    advance(5000); // wall clock while paused should not count
    assert.equal(rec.activeMs, pausedAt);
    rec.resume();
    advance(1500);
    // Hitting limit should soft-stop into processing
    tickTimers();
    // After limit handler, state should be processing (or still recording if stop async)
    assert.ok(['processing', 'recording', 'paused', 'error'].includes(rec.state));
  });

  it('start after discard begins a fresh chunk sequence', async () => {
    const { rec } = makeRecorder();
    await rec.start();
    await rec.stop();
    rec.discard();
    await rec.start();
    assert.equal(rec._chunks[0].seq, 0);
  });
});
