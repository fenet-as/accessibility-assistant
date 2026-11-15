/**
 * VoiceRecorder — pause/resume MediaRecorder with persistent chunk accumulation.
 * States: idle | requesting_permission | recording | paused | processing | transcribed | error
 * Works in the browser (window.VoiceRecorder) and in Node tests with injected deps.
 */
(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }
  if (root) {
    root.VoiceRecorder = api.VoiceRecorder;
    root.VoiceRecorderErrors = api.ERRORS;
  }
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const STATES = Object.freeze({
    IDLE: 'idle',
    REQUESTING_PERMISSION: 'requesting_permission',
    RECORDING: 'recording',
    PAUSED: 'paused',
    PROCESSING: 'processing',
    TRANSCRIBED: 'transcribed',
    ERROR: 'error',
  });

  const TRANSITIONS = Object.freeze({
    idle: ['requesting_permission', 'error'],
    requesting_permission: ['recording', 'error', 'idle'],
    recording: ['paused', 'processing', 'error', 'idle'],
    paused: ['recording', 'processing', 'error', 'idle'],
    processing: ['transcribed', 'error', 'idle'],
    transcribed: ['idle', 'requesting_permission', 'processing', 'error'],
    error: ['idle', 'requesting_permission'],
  });

  const ERRORS = Object.freeze({
    PERMISSION_DENIED: 'permission_denied',
    NO_DEVICE: 'no_device',
    UNSUPPORTED: 'unsupported',
    ILLEGAL_TRANSITION: 'illegal_transition',
    EMPTY_AUDIO: 'empty_audio',
    LIMIT_REACHED: 'limit_reached',
  });

  let _sessionCounter = 0;

  function pickMimeType(MediaRecorderCtor) {
    if (!MediaRecorderCtor || typeof MediaRecorderCtor.isTypeSupported !== 'function') {
      return '';
    }
    const candidates = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/ogg;codecs=opus',
      'audio/mp4',
    ];
    for (let i = 0; i < candidates.length; i += 1) {
      if (MediaRecorderCtor.isTypeSupported(candidates[i])) return candidates[i];
    }
    return '';
  }

  function classifyGetUserMediaError(err) {
    const name = (err && err.name) || '';
    if (name === 'NotAllowedError' || name === 'PermissionDeniedError' || name === 'SecurityError') {
      return ERRORS.PERMISSION_DENIED;
    }
    if (name === 'NotFoundError' || name === 'DevicesNotFoundError' || name === 'OverconstrainedError') {
      return ERRORS.NO_DEVICE;
    }
    if (name === 'NotSupportedError' || name === 'TypeError') {
      return ERRORS.UNSUPPORTED;
    }
    return ERRORS.UNSUPPORTED;
  }

  class VoiceRecorder {
    /**
     * @param {object} [options]
     * @param {number} [options.maxActiveMs=60000]
     * @param {number} [options.timesliceMs=1000]
     * @param {function} [options.onStateChange]
     * @param {function} [options.onLevel]
     * @param {function} [options.onTick]  ({ activeMs, displayMs })
     * @param {function} [options.onError]
     * @param {object} [options.deps]  injectables for tests
     */
    constructor(options) {
      const opts = options || {};
      this.maxActiveMs = opts.maxActiveMs || 60000;
      this.timesliceMs = opts.timesliceMs || 1000;
      this.onStateChange = opts.onStateChange || null;
      this.onLevel = opts.onLevel || null;
      this.onTick = opts.onTick || null;
      this.onError = opts.onError || null;

      const deps = opts.deps || {};
      this._getUserMedia = deps.getUserMedia
        || (typeof navigator !== 'undefined' && navigator.mediaDevices
          ? navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices)
          : null);
      this._MediaRecorder = deps.MediaRecorder
        || (typeof MediaRecorder !== 'undefined' ? MediaRecorder : null);
      this._AudioContext = deps.AudioContext
        || (typeof window !== 'undefined'
          ? (window.AudioContext || window.webkitAudioContext)
          : null);
      this._now = deps.now || (() => Date.now());
      this._setInterval = deps.setInterval || ((fn, ms) => setInterval(fn, ms));
      this._clearInterval = deps.clearInterval || ((id) => clearInterval(id));
      this._setTimeout = deps.setTimeout || ((fn, ms) => setTimeout(fn, ms));
      this._clearTimeout = deps.clearTimeout || ((id) => clearTimeout(id));

      this.state = STATES.IDLE;
      this.sessionId = null;
      this._chunks = []; // { seq, blob }
      this._nextSeq = 0;
      this._mimeType = '';
      this._stream = null;
      this._recorder = null;
      this._permissionPromise = null;
      this._activeMs = 0;
      this._segmentStartedAt = 0;
      this._paused = false;
      this._timerId = null;
      this._limitId = null;
      this._audioCtx = null;
      this._analyser = null;
      this._levelRaf = null;
      this._blob = null;
      this._lastError = null;
      this._keepStream = opts.keepStream !== false;
    }

    get activeMs() {
      if (this.state === STATES.RECORDING && this._segmentStartedAt) {
        return this._activeMs + (this._now() - this._segmentStartedAt);
      }
      return this._activeMs;
    }

    get blob() {
      return this._blob;
    }

    get lastError() {
      return this._lastError;
    }

    get chunkCount() {
      return this._chunks.length;
    }

    get mimeType() {
      return this._mimeType || 'audio/webm';
    }

    static get STATES() {
      return STATES;
    }

    static get ERRORS() {
      return ERRORS;
    }

    _canTransition(to) {
      const allowed = TRANSITIONS[this.state] || [];
      return allowed.indexOf(to) !== -1;
    }

    _setState(to) {
      if (to === this.state) return;
      if (!this._canTransition(to)) {
        const err = {
          code: ERRORS.ILLEGAL_TRANSITION,
          message: `Cannot transition from ${this.state} to ${to}`,
          from: this.state,
          to,
        };
        this._lastError = err;
        if (this.onError) this.onError(err);
        throw Object.assign(new Error(err.message), err);
      }
      const from = this.state;
      this.state = to;
      if (this.onStateChange) this.onStateChange({ from, to, sessionId: this.sessionId });
    }

    _emitTick() {
      if (!this.onTick) return;
      this.onTick({
        activeMs: this.activeMs,
        displayMs: this.activeMs,
        state: this.state,
        sessionId: this.sessionId,
      });
    }

    _startTimers() {
      this._stopTimers();
      this._timerId = this._setInterval(() => {
        this._emitTick();
        if (this.activeMs >= this.maxActiveMs) {
          this._onLimitReached();
        }
      }, 250);
    }

    _stopTimers() {
      if (this._timerId != null) {
        this._clearInterval(this._timerId);
        this._timerId = null;
      }
      if (this._limitId != null) {
        this._clearTimeout(this._limitId);
        this._limitId = null;
      }
    }

    _onLimitReached() {
      if (this.state !== STATES.RECORDING && this.state !== STATES.PAUSED) return;
      const err = { code: ERRORS.LIMIT_REACHED, message: 'Recording time limit reached' };
      this._lastError = err;
      if (this.onError) this.onError(err);
      // Soft-stop into processing so caller can upload the accumulated audio.
      try {
        this.stop();
      } catch (e) { /* already stopping */ }
    }

    async _acquireStream() {
      if (this._stream && this._stream.getTracks().some((t) => t.readyState === 'live')) {
        return this._stream;
      }
      if (!this._getUserMedia) {
        throw Object.assign(new Error('getUserMedia unavailable'), { code: ERRORS.UNSUPPORTED });
      }
      if (this._permissionPromise) {
        return this._permissionPromise;
      }
      this._permissionPromise = this._getUserMedia({ audio: true })
        .then((stream) => {
          this._stream = stream;
          this._permissionPromise = null;
          return stream;
        })
        .catch((err) => {
          this._permissionPromise = null;
          const code = classifyGetUserMediaError(err);
          throw Object.assign(new Error(err.message || code), { code, cause: err });
        });
      return this._permissionPromise;
    }

    _releaseStream() {
      if (this._stream) {
        this._stream.getTracks().forEach((t) => {
          try { t.stop(); } catch (e) { /* noop */ }
        });
        this._stream = null;
      }
    }

    _startLevelMeter(stream) {
      this._stopLevelMeter();
      if (!this.onLevel || !this._AudioContext) return;
      try {
        this._audioCtx = new this._AudioContext();
        const source = this._audioCtx.createMediaStreamSource(stream);
        this._analyser = this._audioCtx.createAnalyser();
        this._analyser.fftSize = 256;
        source.connect(this._analyser);
        const data = new Uint8Array(this._analyser.frequencyBinCount);
        const tick = () => {
          if (!this._analyser || (this.state !== STATES.RECORDING && this.state !== STATES.PAUSED)) {
            this._levelRaf = null;
            return;
          }
          this._analyser.getByteTimeDomainData(data);
          let sum = 0;
          for (let i = 0; i < data.length; i += 1) {
            const v = (data[i] - 128) / 128;
            sum += v * v;
          }
          const rms = Math.sqrt(sum / data.length);
          this.onLevel(Math.min(1, rms * 4));
          if (typeof requestAnimationFrame === 'function') {
            this._levelRaf = requestAnimationFrame(tick);
          } else {
            this._levelRaf = this._setTimeout(tick, 50);
          }
        };
        tick();
      } catch (e) {
        this._audioCtx = null;
        this._analyser = null;
      }
    }

    _stopLevelMeter() {
      if (this._levelRaf != null) {
        if (typeof cancelAnimationFrame === 'function') {
          try { cancelAnimationFrame(this._levelRaf); } catch (e) { /* noop */ }
        }
        try { this._clearTimeout(this._levelRaf); } catch (e) { /* noop */ }
        this._levelRaf = null;
      }
      if (this._audioCtx) {
        try { this._audioCtx.close(); } catch (e) { /* noop */ }
        this._audioCtx = null;
      }
      this._analyser = null;
    }

    _appendChunk(blob) {
      if (!blob || !blob.size) return;
      const seq = this._nextSeq;
      this._nextSeq += 1;
      this._chunks.push({ seq, blob });
    }

    _combineChunks() {
      if (!this._chunks.length) return null;
      // Sort by seq to guarantee order even if events arrive oddly.
      const ordered = this._chunks.slice().sort((a, b) => a.seq - b.seq);
      const parts = ordered.map((c) => c.blob);
      return new Blob(parts, { type: this.mimeType });
    }

    /**
     * Start a new recording session. Clears previous chunks unless resumeAfterTranscribed.
     */
    async start() {
      if (this.state === STATES.RECORDING || this.state === STATES.PAUSED
          || this.state === STATES.REQUESTING_PERMISSION) {
        return this.sessionId;
      }
      // New session: clear prior audio unless we are only re-entering from error/idle/transcribed.
      if (this.state === STATES.PROCESSING) {
        throw Object.assign(new Error('Cannot start while processing'), {
          code: ERRORS.ILLEGAL_TRANSITION,
        });
      }

      this._blob = null;
      this._lastError = null;
      this._chunks = [];
      this._nextSeq = 0;
      this._activeMs = 0;
      this._segmentStartedAt = 0;
      this._paused = false;
      _sessionCounter += 1;
      this.sessionId = `rec-${_sessionCounter}-${this._now()}`;

      this._setState(STATES.REQUESTING_PERMISSION);

      try {
        if (!this._MediaRecorder) {
          throw Object.assign(new Error('MediaRecorder unsupported'), { code: ERRORS.UNSUPPORTED });
        }
        const stream = await this._acquireStream();
        // Guard: user may have discarded while permission prompt was open.
        if (this.state !== STATES.REQUESTING_PERMISSION) {
          return this.sessionId;
        }

        this._mimeType = pickMimeType(this._MediaRecorder);
        const recorder = this._mimeType
          ? new this._MediaRecorder(stream, { mimeType: this._mimeType })
          : new this._MediaRecorder(stream);
        this._mimeType = recorder.mimeType || this._mimeType || 'audio/webm';
        this._recorder = recorder;

        recorder.ondataavailable = (e) => {
          if (e && e.data && e.data.size) this._appendChunk(e.data);
        };
        recorder.onerror = (e) => {
          const err = {
            code: ERRORS.UNSUPPORTED,
            message: (e && e.error && e.error.message) || 'MediaRecorder error',
          };
          this._lastError = err;
          if (this.onError) this.onError(err);
          try {
            if (this.state === STATES.RECORDING || this.state === STATES.PAUSED) {
              this._setState(STATES.ERROR);
            }
          } catch (ex) { /* noop */ }
        };

        recorder.start(this.timesliceMs);
        this._segmentStartedAt = this._now();
        this._setState(STATES.RECORDING);
        this._startTimers();
        this._startLevelMeter(stream);
        this._emitTick();
        return this.sessionId;
      } catch (err) {
        const code = err.code || classifyGetUserMediaError(err);
        this._lastError = { code, message: err.message || code };
        try {
          this._setState(STATES.ERROR);
        } catch (e) { /* noop */ }
        if (this.onError) this.onError(this._lastError);
        throw Object.assign(err instanceof Error ? err : new Error(String(err)), { code });
      }
    }

    pause() {
      if (this.state !== STATES.RECORDING) {
        throw Object.assign(new Error('Can only pause while recording'), {
          code: ERRORS.ILLEGAL_TRANSITION,
        });
      }
      if (this._recorder && this._recorder.state === 'recording') {
        try { this._recorder.pause(); } catch (e) { /* some browsers lack pause */ }
        // Request a chunk so audio up to the pause is flushed into our array.
        try {
          if (typeof this._recorder.requestData === 'function') this._recorder.requestData();
        } catch (e) { /* noop */ }
      }
      if (this._segmentStartedAt) {
        this._activeMs += this._now() - this._segmentStartedAt;
        this._segmentStartedAt = 0;
      }
      this._paused = true;
      this._setState(STATES.PAUSED);
      this._emitTick();
    }

    resume() {
      if (this.state !== STATES.PAUSED) {
        throw Object.assign(new Error('Can only resume while paused'), {
          code: ERRORS.ILLEGAL_TRANSITION,
        });
      }
      if (this.activeMs >= this.maxActiveMs) {
        this._onLimitReached();
        return;
      }
      if (this._recorder && this._recorder.state === 'paused') {
        try { this._recorder.resume(); } catch (e) { /* noop */ }
      }
      this._segmentStartedAt = this._now();
      this._paused = false;
      this._setState(STATES.RECORDING);
      this._emitTick();
    }

    /**
     * Stop recording and combine chunks into a Blob. Does NOT clear chunks until discard/start.
     * @returns {Promise<{ blob: Blob, sessionId: string, mimeType: string, activeMs: number }>}
     */
    stop() {
      if (this.state !== STATES.RECORDING && this.state !== STATES.PAUSED) {
        throw Object.assign(new Error('Can only stop while recording or paused'), {
          code: ERRORS.ILLEGAL_TRANSITION,
        });
      }
      if (this._segmentStartedAt) {
        this._activeMs += this._now() - this._segmentStartedAt;
        this._segmentStartedAt = 0;
      }
      this._stopTimers();
      this._stopLevelMeter();
      this._setState(STATES.PROCESSING);

      const sessionId = this.sessionId;
      const recorder = this._recorder;

      return new Promise((resolve, reject) => {
        const finish = () => {
          const blob = this._combineChunks();
          this._blob = blob;
          this._recorder = null;
          if (!this._keepStream) this._releaseStream();
          if (!blob || !blob.size) {
            const err = { code: ERRORS.EMPTY_AUDIO, message: 'No audio captured' };
            this._lastError = err;
            try { this._setState(STATES.ERROR); } catch (e) { /* noop */ }
            if (this.onError) this.onError(err);
            reject(Object.assign(new Error(err.message), err));
            return;
          }
          resolve({
            blob,
            sessionId,
            mimeType: this.mimeType,
            activeMs: this._activeMs,
            chunkCount: this._chunks.length,
          });
        };

        if (!recorder || recorder.state === 'inactive') {
          finish();
          return;
        }

        const onStop = () => {
          recorder.removeEventListener('stop', onStop);
          // Final dataavailable may fire before stop; give it a tick.
          this._setTimeout(finish, 0);
        };
        recorder.addEventListener('stop', onStop);
        try {
          if (typeof recorder.requestData === 'function' && recorder.state !== 'inactive') {
            recorder.requestData();
          }
        } catch (e) { /* noop */ }
        try {
          recorder.stop();
        } catch (e) {
          finish();
        }
      });
    }

    /** Mark transcription complete for this session (blob still kept). */
    markTranscribed() {
      if (this.state === STATES.TRANSCRIBED) return;
      if (this.state !== STATES.PROCESSING && this.state !== STATES.ERROR) {
        // Allow idle→transcribed only after processing; from error go via idle.
        if (this.state === STATES.IDLE && this._blob) {
          // Already reset; keep blob reference for retry UI.
          return;
        }
      }
      if (this.state === STATES.PROCESSING || this.state === STATES.ERROR) {
        if (this.state === STATES.ERROR) {
          this._setState(STATES.IDLE);
        }
        if (this.state === STATES.PROCESSING) {
          this._setState(STATES.TRANSCRIBED);
        } else if (this.state === STATES.IDLE && this._blob) {
          // no-op
        }
      }
    }

    /** Mark that transcription failed but keep blob for retry. */
    markError(err) {
      this._lastError = err || this._lastError || { code: 'error', message: 'error' };
      if (this.state === STATES.PROCESSING) {
        try { this._setState(STATES.ERROR); } catch (e) { /* noop */ }
      } else if (this.state === STATES.TRANSCRIBED || this.state === STATES.IDLE) {
        // stay; blob retained
      } else if (this.state === STATES.RECORDING || this.state === STATES.PAUSED) {
        this._stopTimers();
        this._stopLevelMeter();
        try {
          if (this._recorder && this._recorder.state !== 'inactive') this._recorder.stop();
        } catch (e) { /* noop */ }
        this._recorder = null;
        try { this._setState(STATES.ERROR); } catch (e) { /* noop */ }
      }
    }

    /**
     * Re-enter processing with the kept blob (for Whisper retry). Does not clear chunks.
     */
    beginRetry() {
      if (!this._blob || !this._blob.size) {
        throw Object.assign(new Error('No audio to retry'), { code: ERRORS.EMPTY_AUDIO });
      }
      if (this.state === STATES.TRANSCRIBED || this.state === STATES.ERROR || this.state === STATES.IDLE) {
        if (this.state === STATES.IDLE) {
          // Idle after discard would have no blob; with blob we allow processing.
          // Transition table: idle → requesting_permission | error only.
          // So go error→idle is wrong. Use transcribed path: transcribed → processing.
          // Force: if idle with blob, treat as transcribed first via internal reset of state machine.
          this.state = STATES.TRANSCRIBED;
        }
        if (this.state === STATES.ERROR) {
          this._setState(STATES.IDLE);
          this.state = STATES.TRANSCRIBED;
        }
        this._setState(STATES.PROCESSING);
        return { blob: this._blob, sessionId: this.sessionId, mimeType: this.mimeType };
      }
      if (this.state === STATES.PROCESSING) {
        return { blob: this._blob, sessionId: this.sessionId, mimeType: this.mimeType };
      }
      throw Object.assign(new Error('Cannot retry in current state'), {
        code: ERRORS.ILLEGAL_TRANSITION,
      });
    }

    /** Discard audio and return to idle. */
    discard() {
      this._stopTimers();
      this._stopLevelMeter();
      if (this._recorder && this._recorder.state !== 'inactive') {
        try {
          this._recorder.ondataavailable = null;
          this._recorder.stop();
        } catch (e) { /* noop */ }
      }
      this._recorder = null;
      this._chunks = [];
      this._nextSeq = 0;
      this._blob = null;
      this._activeMs = 0;
      this._segmentStartedAt = 0;
      this._lastError = null;
      if (!this._keepStream) this._releaseStream();
      // Force idle regardless of prior state (discard is always allowed).
      const from = this.state;
      this.state = STATES.IDLE;
      if (this.onStateChange) this.onStateChange({ from, to: STATES.IDLE, sessionId: this.sessionId });
      this.sessionId = null;
    }

    /** Release mic stream (call when widget closes). */
    release() {
      this.discard();
      this._releaseStream();
    }
  }

  return { VoiceRecorder, ERRORS, STATES };
}));
