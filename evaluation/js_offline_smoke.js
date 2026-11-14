/**
 * Node smoke test for AlxOffline.answerLocally (no browser IndexedDB required for answer path).
 * Usage: node evaluation/js_offline_smoke.js path/to/pack.json
 */
const fs = require('fs');
const path = process.argv[2];
if (!path) {
  console.error('usage: node js_offline_smoke.js pack.json');
  process.exit(2);
}
const pack = JSON.parse(fs.readFileSync(path, 'utf8'));
const code = fs.readFileSync(require('path').join(__dirname, '..', 'assistant', 'widget', 'offline.js'), 'utf8');
const sandbox = { window: {}, globalThis: {}, console };
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
Function('window', 'globalThis', 'console', code)(sandbox, sandbox, console);
const AlxOffline = sandbox.AlxOffline || sandbox.window.AlxOffline;
if (!AlxOffline) {
  console.error('AlxOffline missing');
  process.exit(1);
}

const known = AlxOffline.answerLocally(pack, {
  message: 'How can AI help virtual assistants?',
  language: 'en',
  scope: pack.scope,
});
if (known.status !== 'answered' || known.source !== 'local') {
  console.error('known question failed', known);
  process.exit(1);
}
if (!(known.citations || []).some((c) => /Artificial Intelligence/i.test(c.section))) {
  console.error('wrong citation', known.citations);
  process.exit(1);
}

const unknown = AlxOffline.answerLocally(pack, {
  message: 'What is the capital of France?',
  language: 'en',
  scope: pack.scope,
});
if (unknown.status !== 'not_found' || (unknown.citations || []).length) {
  console.error('unknown question should be not_found', unknown);
  process.exit(1);
}

const am = AlxOffline.answerLocally(pack, {
  message: 'How can AI help virtual assistants?',
  language: 'am',
  scope: pack.scope,
});
if (am.status !== 'answered' || am.language !== 'am') {
  console.error('amharic answer failed', am);
  process.exit(1);
}

console.log(JSON.stringify({
  ok: true,
  known_section: known.citations[0].section,
  known_confidence: known.confidence,
  unknown_status: unknown.status,
  am_fallback: !!am.translation_fallback,
}));
