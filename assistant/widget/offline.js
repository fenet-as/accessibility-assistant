/**
 * ALX offline runtime: IndexedDB packs, local BM25 retrieval, sync queue.
 * Attaches window.AlxOffline. Extractive answers only — never promises cloud AI offline.
 */
(function (global) {
  'use strict';

  const DB_NAME = 'alx-assistant-offline';
  const DB_VERSION = 1;
  const STORES = {
    packs: 'packs',
    meta: 'meta',
    history: 'history',
    unanswered: 'unanswered',
    pending: 'pending',
  };

  function openDb() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains(STORES.packs)) {
          db.createObjectStore(STORES.packs, { keyPath: 'scope' });
        }
        if (!db.objectStoreNames.contains(STORES.meta)) {
          db.createObjectStore(STORES.meta, { keyPath: 'key' });
        }
        if (!db.objectStoreNames.contains(STORES.history)) {
          const history = db.createObjectStore(STORES.history, { keyPath: 'id', autoIncrement: true });
          history.createIndex('by_session', 'session', { unique: false });
          history.createIndex('by_scope', 'scope', { unique: false });
        }
        if (!db.objectStoreNames.contains(STORES.unanswered)) {
          const unanswered = db.createObjectStore(STORES.unanswered, { keyPath: 'id', autoIncrement: true });
          unanswered.createIndex('by_scope', 'scope', { unique: false });
        }
        if (!db.objectStoreNames.contains(STORES.pending)) {
          const pending = db.createObjectStore(STORES.pending, { keyPath: 'id' });
          pending.createIndex('by_dedupe', 'dedupe_key', { unique: true });
          pending.createIndex('by_status', 'status', { unique: false });
        }
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error || new Error('IndexedDB open failed'));
    });
  }

  function txDone(tx) {
    return new Promise((resolve, reject) => {
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
      tx.onabort = () => reject(tx.error || new Error('IndexedDB transaction aborted'));
    });
  }

  async function idbPut(store, value) {
    const db = await openDb();
    const tx = db.transaction(store, 'readwrite');
    tx.objectStore(store).put(value);
    await txDone(tx);
  }

  async function idbGet(store, key) {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(store, 'readonly');
      const req = tx.objectStore(store).get(key);
      req.onsuccess = () => resolve(req.result || null);
      req.onerror = () => reject(req.error);
    });
  }

  async function idbGetAll(store, indexName, query) {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(store, 'readonly');
      const source = indexName ? tx.objectStore(store).index(indexName) : tx.objectStore(store);
      const req = query === undefined ? source.getAll() : source.getAll(query);
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => reject(req.error);
    });
  }

  async function idbDelete(store, key) {
    const db = await openDb();
    const tx = db.transaction(store, 'readwrite');
    tx.objectStore(store).delete(key);
    await txDone(tx);
  }

  function isQuotaError(err) {
    if (!err) return false;
    const name = err.name || '';
    const msg = String(err.message || err);
    return name === 'QuotaExceededError' || /quota/i.test(msg);
  }

  // --- Tokenizer (mirrors assistant/infrastructure/text_analysis.py enough for pack queries) ---

  const HOMOPHONE_ROWS = [[0x1210, 0x1200], [0x1280, 0x1200], [0x1220, 0x1230], [0x12D0, 0x12A0], [0x1340, 0x1338]];
  const AMHARIC_PREFIXES = ['እንደ', 'ስለ', 'ወደ', 'የ', 'ለ', 'በ', 'ከ'];
  const AMHARIC_SUFFIXES = ['ዎችን', 'ዎች', 'ችን', 'ች', 'ን', 'ው'];
  const TOKEN_RE = /[\u1200-\u135F\u1380-\u139F\u2D80-\u2DDF]+|[\u0600-\u06FF]+|[a-z0-9]+/g;

  function normalizeEthiopicChar(ch) {
    const code = ch.codePointAt(0);
    for (let i = 0; i < HOMOPHONE_ROWS.length; i += 1) {
      const row = HOMOPHONE_ROWS[i][0];
      const canonical = HOMOPHONE_ROWS[i][1];
      if (code >= row && code < row + 7) {
        ch = String.fromCodePoint(canonical + (code - row));
        break;
      }
    }
    if (ch === '\u12a3') return '\u12a0';
    return ch;
  }

  function normalizeText(text) {
    const lower = (text || '').normalize('NFC').toLowerCase();
    let out = '';
    for (const ch of lower) out += normalizeEthiopicChar(ch);
    return out;
  }

  function isEthiopic(token) {
    return /[\u1200-\u135F]/.test(token);
  }

  function toSixthOrder(ch) {
    const code = ch.codePointAt(0);
    if (code < 0x1200 || code > 0x135A) return ch;
    const offset = (code - 0x1200) % 8;
    if (offset > 6) return ch;
    return String.fromCodePoint(code - offset + 5);
  }

  function stemAmharic(token) {
    for (const prefix of AMHARIC_PREFIXES) {
      const minStem = prefix.length > 1 ? 3 : 2;
      if (token.startsWith(prefix) && token.length - prefix.length >= minStem) {
        token = token.slice(prefix.length);
        break;
      }
    }
    for (const suffix of AMHARIC_SUFFIXES) {
      if (token.endsWith(suffix) && token.length - suffix.length >= 2) {
        token = token.slice(0, -suffix.length);
        break;
      }
    }
    return token.slice(0, -1) + toSixthOrder(token[token.length - 1]);
  }

  function stemEnglish(token) {
    if (token.length <= 3 || /^\d+$/.test(token)) return token;
    if (token.endsWith('ies') && token.length > 4) token = token.slice(0, -3) + 'y';
    else if (token.endsWith('sses')) token = token.slice(0, -2);
    else if (token.endsWith('s') && !/(ss|us|is)$/.test(token)) token = token.slice(0, -1);
    if (token.endsWith('ing') && token.length > 5) token = token.slice(0, -3);
    else if (token.endsWith('ed') && token.length > 4) token = token.slice(0, -2);
    if (token.endsWith('e') && token.length > 4) token = token.slice(0, -1);
    return token;
  }

  function stem(token) {
    return isEthiopic(token) ? stemAmharic(token) : stemEnglish(token);
  }

  function words(text) {
    return normalizeText(text).match(TOKEN_RE) || [];
  }

  function expandAcronyms(tokens, acronyms) {
    const expanded = tokens.slice();
    const present = new Set(tokens);
    (acronyms || []).forEach(([acronym, phrase]) => {
      if (present.has(acronym)) {
        phrase.forEach((w) => { if (!present.has(w)) expanded.push(w); });
      } else if (phrase.every((w) => present.has(w))) {
        expanded.push(acronym);
      }
    });
    return expanded;
  }

  function analyze(text, tokenizer) {
    const stop = new Set((tokenizer && tokenizer.stop_words) || []);
    const raw = words(text).filter((t) => !stop.has(t));
    return expandAcronyms(raw, (tokenizer && tokenizer.acronyms) || []).map(stem);
  }

  function phraseBigrams(text, tokenizer) {
    const stop = new Set((tokenizer && tokenizer.stop_words) || []);
    const tokens = words(text);
    const pairs = [];
    for (let i = 0; i < tokens.length - 1; i += 1) {
      const a = tokens[i];
      const b = tokens[i + 1];
      if (stop.has(a) && stop.has(b)) continue;
      pairs.push(stem(a) + '\0' + stem(b));
    }
    return new Set(pairs);
  }

  function synonymsOf(term, synonymMap) {
    return (synonymMap && synonymMap[term]) || [];
  }

  // --- Local retrieval using the serialized Python BM25 index ---

  function retrieveLocal(pack, query, options) {
    options = options || {};
    const index = pack.index;
    const ranking = pack.ranking;
    const thresholds = pack.thresholds;
    const topK = options.topK || thresholds.top_k || 3;
    const lesson = options.lesson || null;
    const scope = options.scope || pack.scope;
    const queryTerms = Array.from(new Set(analyze(query, pack.tokenizer)));
    const docs = index.docs || [];
    const allowed = [];
    for (let i = 0; i < docs.length; i += 1) {
      const chunk = docs[i].chunk;
      if (chunk.scope !== scope && scope !== 'all' && scope !== 'auto') continue;
      if (lesson && chunk.lesson_id !== lesson) continue;
      allowed.push(i);
    }
    if (!queryTerms.length || !allowed.length) {
      return { query_terms: queryTerms, passages: [], term_weights: {}, bonuses: {} };
    }

    const weights = {};
    queryTerms.forEach((t) => { weights[t] = index.idf[t] != null ? index.idf[t] : index.unseen_idf; });
    const totalWeight = Object.keys(weights).reduce((s, t) => s + weights[t], 0) || 1;
    const queryBigrams = phraseBigrams(query, pack.tokenizer);
    const bm25 = {};
    const matched = {};

    function bm25Score(term, docId, tf) {
      const idf = index.idf[term];
      if (idf == null) return 0;
      const lengthNorm = 1 - index.b + index.b * (docs[docId].length / index.avg_doc_len);
      return idf * (tf * (index.k1 + 1)) / (tf + index.k1 * lengthNorm);
    }

    const synonymMap = (pack.tokenizer && pack.tokenizer.synonyms) || {};
    const synonymWeight = ranking.synonym_weight || 0.6;
    allowed.forEach((docId) => { matched[docId] = {}; });

    queryTerms.forEach((term) => {
      const exactDocs = new Set();
      allowed.forEach((docId) => {
        const tf = docs[docId].tfs[term];
        if (!tf) return;
        bm25[docId] = (bm25[docId] || 0) + bm25Score(term, docId, tf);
        matched[docId][term] = 1.0;
        exactDocs.add(docId);
      });
      synonymsOf(term, synonymMap).forEach((syn) => {
        allowed.forEach((docId) => {
          if (exactDocs.has(docId)) return;
          const tf = docs[docId].tfs[syn];
          if (!tf) return;
          bm25[docId] = (bm25[docId] || 0) + synonymWeight * bm25Score(syn, docId, tf);
          if (matched[docId][term] == null) matched[docId][term] = synonymWeight;
        });
      });
    });

    const scoredIds = Object.keys(bm25).map(Number);
    if (!scoredIds.length) {
      return { query_terms: queryTerms, passages: [], term_weights: weights, bonuses: {} };
    }
    const maxBm25 = Math.max.apply(null, scoredIds.map((id) => bm25[id]));
    const w = ranking.weights;
    const c = ranking.confidence;
    const bonuses = {};
    const scored = scoredIds.map((docId) => {
      const titleSet = new Set(docs[docId].title_terms);
      const keywordSet = new Set(docs[docId].keyword_terms);
      const bigramSet = new Set((docs[docId].bigrams || []).map((p) => p[0] + '\0' + p[1]));
      let coverage = 0;
      Object.keys(matched[docId]).forEach((t) => { coverage += weights[t] * matched[docId][t]; });
      coverage /= totalWeight;
      const title = queryTerms.filter((t) => titleSet.has(t)).reduce((s, t) => s + weights[t], 0) / totalWeight;
      const keyword = queryTerms.filter((t) => keywordSet.has(t)).reduce((s, t) => s + weights[t], 0) / totalWeight;
      let phrase = 0;
      if (queryBigrams.size) {
        let hits = 0;
        queryBigrams.forEach((bg) => { if (bigramSet.has(bg)) hits += 1; });
        phrase = hits / queryBigrams.size;
      }
      const raw = bm25[docId];
      const rank = w.bm25 * (raw / maxBm25) + w.coverage * coverage + w.title * title
        + w.keyword * keyword + w.phrase * phrase;
      const bonus = c.title * title + c.phrase * phrase;
      const confidence = Math.min(1, c.coverage * coverage + bonus);
      bonuses[docs[docId].chunk.id] = bonus;
      return { rank, raw, confidence, docId };
    });
    scored.sort((a, b) => (b.rank - a.rank) || (b.raw - a.raw));
    const passages = scored.slice(0, topK).map((item) => {
      const chunk = docs[item.docId].chunk;
      return {
        id: chunk.id,
        scope: chunk.scope,
        course: chunk.course,
        lesson_id: chunk.lesson_id,
        title: chunk.title,
        section: chunk.section,
        anchor: chunk.anchor,
        url: chunk.url,
        text: chunk.text,
        translations: chunk.translations || {},
        score: Math.round(item.rank * 1000) / 1000,
        confidence: Math.round(item.confidence * 1000) / 1000,
        matched_terms: Object.keys(matched[item.docId]).sort(),
      };
    });
    return { query_terms: queryTerms, passages, term_weights: weights, bonuses };
  }

  function combinedConfidence(result, passages) {
    const total = Object.keys(result.term_weights).reduce((s, t) => s + result.term_weights[t], 0);
    if (!passages.length || total <= 0) return 0;
    const covered = new Set();
    passages.forEach((p) => (p.matched_terms || []).forEach((t) => covered.add(t)));
    let coverage = 0;
    covered.forEach((t) => { if (result.term_weights[t] != null) coverage += result.term_weights[t]; });
    coverage /= total;
    let bonus = 0;
    passages.forEach((p) => { bonus = Math.max(bonus, result.bonuses[p.id] || 0); });
    return Math.round(Math.min(1, 0.7 * coverage + bonus) * 1000) / 1000;
  }

  function selectCovering(result, topK) {
    const selected = [];
    let best = 0;
    (result.passages || []).forEach((passage) => {
      if (selected.length >= topK) return;
      const score = combinedConfidence(result, selected.concat([passage]));
      if (score > best) {
        selected.push(passage);
        best = score;
      }
    });
    return selected;
  }

  function bestSentences(text, queryTerms, limit) {
    const parts = (text || '').split(/(?<=[.!?።؟])\s+/).map((s) => s.trim()).filter((s) => s.length > 10);
    if (!parts.length) return (text || '').trim();
    const termSet = new Set(queryTerms || []);
    const ranked = parts.map((sentence, i) => {
      const hits = analyze(sentence, { stop_words: [], acronyms: [] }).filter((t) => termSet.has(t)).length;
      return { i, hits, sentence };
    });
    ranked.sort((a, b) => (b.hits - a.hits) || (a.i - b.i));
    return ranked.slice(0, limit).sort((a, b) => a.i - b.i).map((r) => r.sentence).join(' ');
  }

  function localize(messages, language) {
    return (messages && (messages[language] || messages.en)) || '';
  }

  function answerFromPassages(pack, passages, language, query) {
    if (!passages.length) {
      return {
        status: 'not_found',
        language,
        answer: localize(pack.messages.not_found, language),
        citations: [],
        actions: ['get_human_help'],
        confidence: 0,
        source: 'local',
        translation_fallback: false,
      };
    }
    const queryTerms = analyze(query, pack.tokenizer);
    const used = [passages[0]];
    const covered = new Set(passages[0].matched_terms || []);
    passages.slice(1, 3).forEach((p) => {
      const fresh = (p.matched_terms || []).filter((t) => !covered.has(t));
      if (fresh.length) {
        used.push(p);
        fresh.forEach((t) => covered.add(t));
      }
    });
    let fallback = false;
    const parts = used.map((passage, position) => {
      const limit = position === 0 ? 4 : 1;
      if (language === 'en') return bestSentences(passage.text, queryTerms, limit);
      const translated = (passage.translations || {})[language];
      if (translated) return translated;
      fallback = true;
      return localize(pack.messages.translation_unavailable, language) + '\n'
        + bestSentences(passage.text, queryTerms, limit);
    });
    return {
      status: 'answered',
      language,
      answer: parts.join('\n\n'),
      citations: used.map((p) => ({ title: p.title, section: p.section, url: p.url })),
      actions: ['get_human_help'],
      confidence: passages[0].confidence,
      source: 'local',
      translation_fallback: fallback,
    };
  }

  function answerLocally(pack, request) {
    const language = request.language && request.language !== 'auto' ? request.language : 'en';
    const thresholds = pack.thresholds;
    let result = retrieveLocal(pack, request.message, {
      scope: request.scope || pack.scope,
      lesson: request.lesson || null,
      topK: thresholds.top_k,
    });
    let confidence = result.passages.length ? result.passages[0].confidence : 0;

    if (confidence >= thresholds.high_confidence) {
      const selected = result.passages.filter((p) => p.confidence >= thresholds.low_confidence);
      return answerFromPassages(pack, selected, language, request.message);
    }
    if (result.query_terms.length && confidence < thresholds.low_confidence) {
      return {
        status: 'not_found',
        language,
        answer: localize(pack.messages.not_found, language),
        citations: [],
        actions: ['get_human_help'],
        confidence,
        source: 'local',
        translation_fallback: false,
      };
    }

    result = retrieveLocal(pack, request.message, {
      scope: request.scope || pack.scope,
      lesson: request.lesson || null,
      topK: thresholds.wide_k,
    });
    const selected = selectCovering(result, thresholds.top_k);
    const combined = combinedConfidence(result, selected);
    if (selected.length && combined >= thresholds.high_confidence) {
      const response = answerFromPassages(pack, selected, language, request.message);
      response.confidence = combined;
      return response;
    }
    const suggestions = (result.passages || []).slice(0, 3).map((p) => p.section);
    return {
      status: 'needs_clarification',
      language,
      answer: [localize(pack.messages.needs_clarification, language)].concat(suggestions.map((s) => '- ' + s)).join('\n'),
      citations: [],
      actions: ['clarify', 'get_human_help'],
      confidence: combined,
      suggestions,
      source: 'local',
      translation_fallback: false,
    };
  }

  // --- Pack download / storage ---

  async function savePack(pack) {
    const record = {
      scope: pack.scope,
      kb_version: pack.kb_version,
      pack_format: pack.pack_format,
      app_version: pack.app_version,
      course_title: pack.course_title,
      generated_at: pack.generated_at,
      chunk_count: pack.chunk_count,
      saved_at: new Date().toISOString(),
      pack,
    };
    try {
      await idbPut(STORES.packs, record);
      await idbPut(STORES.meta, { key: 'last_pack_' + pack.scope, value: {
        kb_version: pack.kb_version, saved_at: record.saved_at, chunk_count: pack.chunk_count,
      }});
      return { ok: true, record };
    } catch (err) {
      if (isQuotaError(err)) {
        return { ok: false, quota: true, error: err };
      }
      throw err;
    }
  }

  async function getPack(scope) {
    const record = await idbGet(STORES.packs, scope);
    return record ? record.pack : null;
  }

  async function getPackRecord(scope) {
    return idbGet(STORES.packs, scope);
  }

  async function downloadPack(apiUrl, scope) {
    const res = await fetch(`${apiUrl}/offline/pack?scope=${encodeURIComponent(scope)}`);
    if (!res.ok) throw new Error('Pack download failed: ' + res.status);
    const pack = await res.json();
    const saved = await savePack(pack);
    if (!saved.ok && saved.quota) {
      return { ok: false, quota: true, pack };
    }
    return { ok: true, pack, kb_version: pack.kb_version };
  }

  async function isPackStale(apiUrl, scope) {
    const local = await getPackRecord(scope);
    if (!local) return { stale: true, reason: 'missing' };
    try {
      const res = await fetch(`${apiUrl}/offline/pack/meta?scope=${encodeURIComponent(scope)}`);
      if (!res.ok) return { stale: false, reason: 'meta_unavailable', local };
      const meta = await res.json();
      if (meta.kb_version !== local.kb_version || meta.pack_format !== local.pack_format) {
        return { stale: true, reason: 'version_mismatch', local, remote: meta };
      }
      return { stale: false, local, remote: meta };
    } catch (e) {
      return { stale: false, reason: 'offline', local };
    }
  }

  // --- History / unanswered / pending sync ---

  function dedupeKey(type, payload) {
    const raw = [type, payload.session || '', payload.scope || '', payload.message || '', payload.reason || ''].join('|');
    let hash = 0;
    for (let i = 0; i < raw.length; i += 1) hash = ((hash << 5) - hash) + raw.charCodeAt(i);
    return type + ':' + (hash >>> 0).toString(16);
  }

  async function appendHistory(entry) {
    try {
      await idbPut(STORES.history, Object.assign({ created_at: new Date().toISOString() }, entry));
    } catch (err) {
      if (!isQuotaError(err)) throw err;
      return { quota: true };
    }
    return { ok: true };
  }

  async function recordUnanswered(entry) {
    try {
      await idbPut(STORES.unanswered, Object.assign({ created_at: new Date().toISOString() }, entry));
    } catch (err) {
      if (!isQuotaError(err)) throw err;
      return { quota: true };
    }
    return { ok: true };
  }

  async function enqueuePending(type, payload) {
    const id = dedupeKey(type, payload);
    const existing = await idbGet(STORES.pending, id);
    if (existing && (existing.status === 'queued' || existing.status === 'syncing' || existing.status === 'done')) {
      return { queued: false, duplicate: true, item: existing };
    }
    const item = {
      id,
      dedupe_key: id,
      type,
      payload,
      status: 'queued',
      created_at: new Date().toISOString(),
      attempts: 0,
    };
    try {
      await idbPut(STORES.pending, item);
      return { queued: true, item };
    } catch (err) {
      if (isQuotaError(err)) return { queued: false, quota: true, error: err };
      throw err;
    }
  }

  async function listPending(status) {
    if (status) return idbGetAll(STORES.pending, 'by_status', status);
    return idbGetAll(STORES.pending);
  }

  async function syncPending(apiUrl, { consent, onProgress } = {}) {
    if (!consent) {
      return { synced: 0, skipped: true, reason: 'consent_required' };
    }
    const queued = await listPending('queued');
    let synced = 0;
    const results = [];
    for (const item of queued) {
      if (onProgress) onProgress({ phase: 'syncing', item });
      item.status = 'syncing';
      item.attempts = (item.attempts || 0) + 1;
      await idbPut(STORES.pending, item);
      try {
        let res;
        if (item.type === 'question') {
          res = await fetch(`${apiUrl}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(item.payload),
          });
        } else if (item.type === 'escalation') {
          res = await fetch(`${apiUrl}/escalate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(item.payload),
          });
        } else {
          throw new Error('Unknown pending type');
        }
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const body = await res.json();
        item.status = 'done';
        item.synced_at = new Date().toISOString();
        item.response = body;
        await idbPut(STORES.pending, item);
        synced += 1;
        results.push({ id: item.id, ok: true, body });
      } catch (err) {
        item.status = 'queued';
        item.last_error = String(err.message || err);
        await idbPut(STORES.pending, item);
        results.push({ id: item.id, ok: false, error: item.last_error });
      }
    }
    if (onProgress) onProgress({ phase: 'done', synced });
    return { synced, results, skipped: false };
  }

  function online() {
    return typeof navigator === 'undefined' ? true : navigator.onLine;
  }

  global.AlxOffline = {
    DB_VERSION,
    openDb,
    isQuotaError,
    retrieveLocal,
    answerLocally,
    savePack,
    getPack,
    getPackRecord,
    downloadPack,
    isPackStale,
    appendHistory,
    recordUnanswered,
    enqueuePending,
    listPending,
    syncPending,
    online,
    analyze,
  };
})(typeof window !== 'undefined' ? window : globalThis);
