/**
 * ALX Digital Bridge Accessibility Assistant
 * Level 1 Drop-in Web Component (Shadow DOM)
 * Meets WCAG 2.2 AA standards: NVDA/TalkBack screen reader friendly,
 * 100% keyboard navigable, ARIA live announcements, Amharic & RTL support.
 */

(function () {
  'use strict';

  // Prevent double injection
  if (customElements.get('alx-assistant')) {
    return;
  }

  const TEMPLATE = document.createElement('template');
  TEMPLATE.innerHTML = `
    <style>
      :host {
        --alx-primary: #1062fe;
        --alx-primary-hover: #0043ce;
        --alx-bg: #ffffff;
        --alx-surface: #f4f7fb;
        --alx-text: #161616;
        --alx-text-muted: #525252;
        --alx-border: #d0d7de;
        --alx-focus: #0f62fe;
        --alx-danger: #da1e28;
        --alx-radius: 12px;
        --alx-font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans Ethiopic", Helvetica, Arial, sans-serif;
        
        font-family: var(--alx-font);
        color: var(--alx-text);
        box-sizing: border-box;
      }

      *, *::before, *::after {
        box-sizing: inherit;
      }

      /* Floating launcher button */
      .alx-launcher {
        position: fixed;
        bottom: 24px;
        right: 24px;
        z-index: 999999;
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 12px 18px;
        min-width: 48px;
        min-height: 48px;
        background-color: var(--alx-primary);
        color: #ffffff;
        border: 2px solid transparent;
        border-radius: 9999px;
        font-size: 15px;
        font-weight: 600;
        cursor: pointer;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
        transition: transform 0.2s ease, background-color 0.2s ease;
      }

      .alx-launcher:hover {
        background-color: var(--alx-primary-hover);
        transform: translateY(-2px);
      }

      .alx-launcher:focus-visible {
        outline: 3px solid #ffffff;
        outline-offset: 2px;
        border-color: var(--alx-primary);
      }

      .alx-launcher svg {
        width: 22px;
        height: 22px;
        fill: currentColor;
        flex-shrink: 0;
      }

      /* Main Dialog Container */
      .alx-dialog {
        position: fixed;
        bottom: 84px;
        right: 24px;
        z-index: 999999;
        width: 400px;
        max-width: calc(100vw - 32px);
        height: 580px;
        max-height: calc(100vh - 110px);
        background: var(--alx-bg);
        border: 1px solid var(--alx-border);
        border-radius: var(--alx-radius);
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.18);
        display: flex;
        flex-direction: column;
        overflow: hidden;
      }

      .alx-dialog[hidden] {
        display: none !important;
      }

      /* Header */
      .alx-header {
        background-color: var(--alx-surface);
        padding: 12px 16px;
        border-bottom: 1px solid var(--alx-border);
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
      }

      .alx-header-title {
        font-size: 16px;
        font-weight: 700;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 6px;
      }

      .alx-scope-badge {
        font-size: 11px;
        font-weight: 700;
        padding: 2px 7px;
        border-radius: 9999px;
        background-color: #e0f2fe;
        color: #0369a1;
        text-transform: uppercase;
        margin-left: 6px;
        display: inline-block;
        letter-spacing: 0.3px;
        vertical-align: middle;
      }

      .alx-header-controls {
        display: flex;
        align-items: center;
        gap: 6px;
      }

      .alx-btn-icon {
        background: transparent;
        border: 1px solid var(--alx-border);
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        color: var(--alx-text);
        min-height: 36px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
      }

      .alx-btn-icon:hover {
        background-color: #e5e9f0;
      }

      .alx-btn-icon:focus-visible {
        outline: 3px solid var(--alx-focus);
        outline-offset: 1px;
      }

      /* Quick toolbar */
      .alx-toolbar {
        background: #ffffff;
        padding: 6px 16px;
        border-bottom: 1px solid var(--alx-border);
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 13px;
      }

      .alx-toggle-group {
        display: flex;
        align-items: center;
        gap: 4px;
      }

      .alx-btn-help {
        background: #fff1f1;
        color: #b81922;
        border: 1px solid #ffd7d9;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 12px;
      }

      .alx-btn-help:hover {
        background: #ffe3e5;
      }

      .alx-btn-help:focus-visible {
        outline: 3px solid var(--alx-danger);
      }

      /* Message Log (aria-live region) */
      .alx-messages {
        flex: 1;
        overflow-y: auto;
        padding: 16px;
        display: flex;
        flex-direction: column;
        gap: 12px;
      }

      .alx-bubble {
        max-width: 88%;
        padding: 10px 14px;
        border-radius: 12px;
        font-size: 14px;
        line-height: 1.45;
        word-break: break-word;
      }

      .alx-bubble-user {
        align-self: flex-end;
        background-color: var(--alx-primary);
        color: #ffffff;
        border-bottom-right-radius: 2px;
      }

      .alx-bubble-assistant {
        align-self: flex-start;
        background-color: var(--alx-surface);
        color: var(--alx-text);
        border: 1px solid var(--alx-border);
        border-bottom-left-radius: 2px;
      }

      .alx-bubble-status {
        align-self: center;
        font-style: italic;
        color: var(--alx-text-muted);
        font-size: 13px;
        background: transparent;
      }

      /* Citations List */
      .alx-citations {
        margin-top: 8px;
        padding-top: 8px;
        border-top: 1px dashed var(--alx-border);
        font-size: 12px;
      }

      .alx-citations-title {
        font-weight: 600;
        color: var(--alx-text-muted);
        margin-bottom: 4px;
      }

      .alx-citations-list {
        list-style: none;
        padding: 0;
        margin: 0;
        display: flex;
        flex-direction: column;
        gap: 3px;
      }

      .alx-citation-link {
        color: var(--alx-primary);
        text-decoration: underline;
        font-weight: 500;
      }

      .alx-citation-link:hover {
        color: var(--alx-primary-hover);
      }

      .alx-citation-link:focus-visible {
        outline: 2px solid var(--alx-focus);
      }

      /* Input Area */
      .alx-input-area {
        padding: 12px 16px;
        border-top: 1px solid var(--alx-border);
        background: var(--alx-surface);
      }

      .alx-input-form {
        display: flex;
        gap: 8px;
      }

      .alx-input-field {
        flex: 1;
        padding: 10px 12px;
        font-size: 14px;
        border: 1px solid var(--alx-border);
        border-radius: 6px;
        background: #ffffff;
        color: var(--alx-text);
        font-family: inherit;
      }

      .alx-input-field:focus-visible {
        outline: 3px solid var(--alx-focus);
        outline-offset: -1px;
      }

      .alx-btn-send {
        background-color: var(--alx-primary);
        color: #ffffff;
        border: none;
        border-radius: 6px;
        padding: 0 16px;
        font-weight: 600;
        font-size: 14px;
        cursor: pointer;
        min-height: 40px;
      }

      .alx-btn-send:hover {
        background-color: var(--alx-primary-hover);
      }

      .alx-btn-send:focus-visible {
        outline: 3px solid var(--alx-focus);
        outline-offset: 1px;
      }

      /* Voice Input Button */
      .alx-btn-voice {
        background-color: transparent;
        border: 1px solid var(--alx-border);
        border-radius: 6px;
        padding: 0 10px;
        cursor: pointer;
        min-width: 40px;
        min-height: 40px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        color: var(--alx-text);
        transition: all 0.2s ease;
      }

      .alx-btn-voice svg {
        width: 18px;
        height: 18px;
        fill: currentColor;
      }

      .alx-btn-voice:hover {
        background-color: #f1f5f9;
        color: var(--alx-primary);
      }

      .alx-btn-voice:focus-visible {
        outline: 3px solid var(--alx-focus);
        outline-offset: 1px;
      }

      .alx-btn-voice.listening {
        background-color: #fee2e2;
        border-color: #ef4444;
        color: #dc2626;
        animation: alx-pulse 1.2s infinite ease-in-out;
      }

      @keyframes alx-pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.08); }
        100% { transform: scale(1); }
      }

      /* Read Aloud (TTS) Button */
      .alx-btn-speak {
        background: transparent;
        border: 1px solid var(--alx-border);
        border-radius: 4px;
        padding: 2px 8px;
        font-size: 11px;
        font-weight: 600;
        cursor: pointer;
        color: var(--alx-text-muted);
        display: inline-flex;
        align-items: center;
        gap: 4px;
        margin-top: 6px;
        min-height: 28px;
      }

      .alx-btn-speak:hover {
        background-color: #f1f5f9;
        color: var(--alx-primary);
      }

      .alx-btn-speak:focus-visible {
        outline: 2px solid var(--alx-focus);
      }

      .alx-btn-speak.speaking {
        background-color: #eff6ff;
        border-color: var(--alx-primary);
        color: var(--alx-primary);
      }

      /* High-contrast and reduced motion */
      @media (prefers-reduced-motion: reduce) {
        .alx-launcher, .alx-dialog, .alx-btn-voice.listening {
          transition: none !important;
          animation: none !important;
        }
      }
    </style>

    <!-- Floating Trigger Button -->
    <button type="button" class="alx-launcher" id="alx-launcher" aria-haspopup="dialog" aria-expanded="false" aria-label="Ask Tutor / ረዳት - AI Learning Assistant">
      <svg aria-hidden="true" viewBox="0 0 24 24">
        <path d="M12 2C6.48 2 2 6.48 2 12c0 1.85.5 3.58 1.38 5.08L2 22l5.08-1.38C8.42 21.5 10.15 22 12 22c5.52 0 10-4.48 10-10S17.52 2 12 2zm1 14h-2v-2h2v2zm0-4h-2V7h2v5z"/>
      </svg>
      <span id="alx-launcher-text">Ask Tutor / ረዳት</span>
    </button>

    <!-- Chat Dialog -->
    <div class="alx-dialog" id="alx-dialog" role="dialog" aria-modal="false" aria-labelledby="alx-title" hidden>
      <div class="alx-header">
        <h2 class="alx-header-title" id="alx-title">
          <svg aria-hidden="true" style="width: 20px; height: 20px; fill: var(--alx-primary);" viewBox="0 0 24 24">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9v-2h2v2zm0-4H9V7h2v5z"/>
          </svg>
          <span id="alx-header-label">ALX Learning Assistant</span>
          <span class="alx-scope-badge" id="alx-scope-badge" aria-label="Course scope">VA-1</span>
        </h2>
        <div class="alx-header-controls">
          <button type="button" class="alx-btn-icon" id="alx-lang-btn" aria-label="English / አማርኛ - Switch language">
            English / አማርኛ
          </button>
          <button type="button" class="alx-btn-icon" id="alx-close-btn" aria-label="Close Assistant">
            ✕
          </button>
        </div>
      </div>

      <div class="alx-toolbar">
        <div class="alx-toggle-group">
          <label for="alx-simple-mode" style="display: flex; align-items: center; gap: 6px; cursor: pointer;">
            <input type="checkbox" id="alx-simple-mode" aria-label="Simple Mode" />
            <span id="alx-simple-label">Simple Mode</span>
          </label>
        </div>
        <button type="button" class="alx-btn-help" id="alx-escalate-btn" aria-label="Live Human Help - Request human tutor help">
          Live Human Help
        </button>
      </div>

      <!-- ARIA Live Region for screen readers -->
      <div class="alx-messages" id="alx-messages" role="log" aria-live="polite" aria-atomic="false">
        <div class="alx-bubble alx-bubble-assistant" lang="en">
          Hello! I am your course assistant. Ask me questions about this lesson in English or Amharic (አማርኛ). All answers are strictly grounded in course content.
        </div>
      </div>

      <div class="alx-input-area">
        <form class="alx-input-form" id="alx-form">
          <label for="alx-input" class="visually-hidden" style="position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); border: 0;">Type your question</label>
          <input type="text" class="alx-input-field" id="alx-input" placeholder="Ask a question about this lesson..." autocomplete="off" required />
          <button type="button" class="alx-btn-voice" id="alx-voice-btn" aria-label="Voice input - Speak your question" aria-pressed="false" title="Voice input">
            <svg aria-hidden="true" viewBox="0 0 24 24">
              <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5-3c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
            </svg>
          </button>
          <button type="submit" class="alx-btn-send" id="alx-send-btn" aria-label="Send message">Send</button>
        </form>
      </div>
    </div>
  `;

  class AlxAssistant extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: 'open' });
      this.shadowRoot.appendChild(TEMPLATE.content.cloneNode(true));

      this.isOpen = false;
      this.currentLang = this.getAttribute('data-lang') || 'auto';
      this.apiUrl = this.getAttribute('data-api') || 'http://localhost:8000/api';
      this.scopeBadge = this.shadowRoot.getElementById('alx-scope-badge');
      this.scope = this.detectScope();
      this.updateScopeBadge();
      this.sessionId = 'anon-' + Math.random().toString(36).substring(2, 9);

      // Element references
      this.launcher = this.shadowRoot.getElementById('alx-launcher');
      this.dialog = this.shadowRoot.getElementById('alx-dialog');
      this.closeBtn = this.shadowRoot.getElementById('alx-close-btn');
      this.langBtn = this.shadowRoot.getElementById('alx-lang-btn');
      this.simpleModeCheck = this.shadowRoot.getElementById('alx-simple-mode');
      this.escalateBtn = this.shadowRoot.getElementById('alx-escalate-btn');
      this.form = this.shadowRoot.getElementById('alx-form');
      this.input = this.shadowRoot.getElementById('alx-input');
      this.voiceBtn = this.shadowRoot.getElementById('alx-voice-btn');
      this.messagesContainer = this.shadowRoot.getElementById('alx-messages');
    }

    detectScope() {
      // 1. Explicit component attribute (data-scope, data-source, or data-course-id)
      if (this.getAttribute('data-scope')) return this.getAttribute('data-scope');
      if (this.getAttribute('data-source')) return this.getAttribute('data-source');
      if (this.getAttribute('data-course-id')) return this.getAttribute('data-course-id');

      // 2. Meta tags on host page (<meta name="course-id"> or <meta name="course-scope">)
      const metaCourse = document.querySelector('meta[name="course-id"], meta[name="course-scope"], meta[name="course"]');
      if (metaCourse && metaCourse.content) return metaCourse.content.trim();

      // 3. Body/HTML dataset attributes
      if (document.body && document.body.dataset) {
        if (document.body.dataset.courseScope) return document.body.dataset.courseScope;
        if (document.body.dataset.courseId) return document.body.dataset.courseId;
        if (document.body.dataset.course) return document.body.dataset.course;
      }

      // 4. URL query parameter (?course_id=... or ?course=... or ?scope=...)
      try {
        const params = new URLSearchParams(window.location.search);
        const urlCourse = params.get('course_id') || params.get('course') || params.get('scope');
        if (urlCourse) return urlCourse.trim();
      } catch (e) {
        // Safe fallback in sandboxed contexts
      }

      // 5. Default fallback to VA-1
      return 'course:va-1';
    }

    updateScopeBadge() {
      if (this.scopeBadge) {
        const cleanScope = (this.scope || 'course:va-1').replace(/^course:/i, '');
        this.scopeBadge.textContent = cleanScope.toUpperCase();
        this.scopeBadge.title = `Grounded in curriculum: ${this.scope}`;
        this.scopeBadge.setAttribute('aria-label', `Curriculum: ${cleanScope}`);
      }
    }

    connectedCallback() {
      // Event bindings
      this.launcher.addEventListener('click', () => this.toggle());
      this.closeBtn.addEventListener('click', () => this.close());
      this.langBtn.addEventListener('click', () => this.toggleLanguage());
      this.escalateBtn.addEventListener('click', () => this.requestHumanHelp());
      this.form.addEventListener('submit', (e) => this.handleSubmit(e));
      this.initVoiceInput();

      // Close on Escape key (WCAG Focus Management)
      this.dialog.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          this.close();
        }
      });
    }

    toggle() {
      if (this.isOpen) {
        this.close();
      } else {
        this.open();
      }
    }

    open() {
      this.isOpen = true;
      this.scope = this.detectScope();
      this.updateScopeBadge();
      this.dialog.removeAttribute('hidden');
      this.launcher.setAttribute('aria-expanded', 'true');
      this.input.focus();
    }

    close() {
      this.isOpen = false;
      this.dialog.setAttribute('hidden', '');
      this.launcher.setAttribute('aria-expanded', 'false');
      this.launcher.focus(); // Restore focus to trigger
    }

    toggleLanguage() {
      if (this.currentLang === 'am') {
        this.currentLang = 'en';
        this.langBtn.textContent = 'English (EN)';
        this.langBtn.setAttribute('aria-label', 'English (EN) - Switch language');
        this.input.placeholder = 'Ask a question about this lesson...';
      } else {
        this.currentLang = 'am';
        this.langBtn.textContent = 'አማርኛ (AM)';
        this.langBtn.setAttribute('aria-label', 'አማርኛ (AM) - Switch language');
        this.input.placeholder = 'ስለዚህ ትምህርት ጥያቄዎን ይጠይቁ...';
      }
    }

    initVoiceInput() {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRecognition) {
        if (this.voiceBtn) this.voiceBtn.style.display = 'none';
        return;
      }

      try {
        this.recognition = new SpeechRecognition();
        this.recognition.continuous = false;
        this.recognition.interimResults = true;
        this.isListening = false;

        this.recognition.onstart = () => {
          this.isListening = true;
          this.voiceBtn.classList.add('listening');
          this.voiceBtn.setAttribute('aria-pressed', 'true');
          this.voiceBtn.setAttribute('aria-label', 'Stop listening - Microphone active');
          this.input.placeholder = this.currentLang === 'am' ? 'እያዳመጠ ነው... አሁን ይናገሩ' : 'Listening... Speak your question now';
        };

        this.recognition.onresult = (event) => {
          const transcript = Array.from(event.results)
            .map(res => res[0].transcript)
            .join('');
          this.input.value = transcript;
        };

        this.recognition.onerror = (event) => {
          console.warn('Speech recognition status:', event.error);
          this.stopListening();
        };

        this.recognition.onend = () => {
          this.stopListening();
        };

        this.voiceBtn.addEventListener('click', () => {
          if (this.isListening) {
            this.recognition.stop();
          } else {
            this.recognition.lang = this.currentLang === 'am' ? 'am-ET' : 'en-US';
            try {
              this.recognition.start();
            } catch (err) {
              console.warn('Could not start recognition:', err);
            }
          }
        });
      } catch (err) {
        console.warn('Speech recognition initialization error:', err);
        if (this.voiceBtn) this.voiceBtn.style.display = 'none';
      }
    }

    stopListening() {
      this.isListening = false;
      if (this.voiceBtn) {
        this.voiceBtn.classList.remove('listening');
        this.voiceBtn.setAttribute('aria-pressed', 'false');
        this.voiceBtn.setAttribute('aria-label', 'Voice input - Speak your question');
      }
      this.input.placeholder = this.currentLang === 'am' 
        ? 'ስለዚህ ትምህርት ጥያቄዎን ይጠይቁ...' 
        : 'Ask a question about this lesson...';
      this.input.focus();
    }

    appendMessage(text, sender, lang = 'auto', citations = []) {
      const bubble = document.createElement('div');
      bubble.className = `alx-bubble alx-bubble-${sender}`;
      bubble.setAttribute('dir', 'auto');

      // Detect language if auto
      const isAmharic = /[\u1200-\u137F]/.test(text);
      bubble.setAttribute('lang', isAmharic ? 'am' : (lang === 'auto' ? 'en' : lang));

      const textNode = document.createElement('div');
      textNode.textContent = text;
      bubble.appendChild(textNode);

      // Render citations if provided
      if (citations && citations.length > 0) {
        const citeBox = document.createElement('div');
        citeBox.className = 'alx-citations';

        const citeTitle = document.createElement('div');
        citeTitle.className = 'alx-citations-title';
        citeTitle.textContent = isAmharic ? 'የተጠቀሱ ምንጮች (Citations):' : 'Course Citations:';
        citeBox.appendChild(citeTitle);

        const list = document.createElement('ul');
        list.className = 'alx-citations-list';
        citations.forEach((c) => {
          const item = document.createElement('li');
          const link = document.createElement('a');
          link.className = 'alx-citation-link';

          // Ensure absolute rooted path to prevent relative /pages/pages/... nesting
          let cleanUrl = c.url || '#';
          if (cleanUrl !== '#' && !cleanUrl.startsWith('/') && !cleanUrl.startsWith('http')) {
            cleanUrl = '/' + cleanUrl;
          }
          link.href = cleanUrl;
          link.textContent = `${c.title} — ${c.section}`;
          link.setAttribute('aria-label', `Go to course source: ${c.section}`);

          // In-page deep link handler: smooth scroll and highlight cited paragraph
          link.addEventListener('click', (e) => {
            const hashMatch = cleanUrl.match(/#([a-zA-Z0-9_\-]+)/);
            if (hashMatch) {
              const anchorId = hashMatch[1];
              const targetEl = document.getElementById(anchorId) ||
                               document.querySelector(`[name="${anchorId}"]`) ||
                               document.querySelector(`[data-anchor="${anchorId}"]`) ||
                               document.getElementById(anchorId.toLowerCase());
              if (targetEl) {
                e.preventDefault();
                // Smooth scroll to target
                targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });

                // Highlight section heading/paragraph and focus for screen readers
                const highlightEl = targetEl.closest('h1, h2, h3, h4, h5, h6, section, article') || targetEl.parentElement || targetEl;
                highlightEl.setAttribute('tabindex', '-1');
                highlightEl.focus({ preventScroll: true });

                const origBg = highlightEl.style.backgroundColor;
                const origOutline = highlightEl.style.outline;
                highlightEl.style.transition = 'background-color 0.4s ease, outline 0.4s ease';
                highlightEl.style.backgroundColor = '#fef08a';
                highlightEl.style.outline = '3px solid #eab308';
                highlightEl.style.outlineOffset = '4px';
                highlightEl.style.borderRadius = '4px';

                setTimeout(() => {
                  highlightEl.style.backgroundColor = origBg;
                  highlightEl.style.outline = origOutline;
                }, 2500);

                window.history.pushState(null, '', `#${anchorId}`);
              }
            }
          });

          item.appendChild(link);
          list.appendChild(item);
        });
        citeBox.appendChild(list);
        bubble.appendChild(citeBox);
      }

      // Accessible Read-Aloud (Text-to-Speech) for assistant responses
      if (sender === 'assistant' && typeof window !== 'undefined' && 'speechSynthesis' in window) {
        const speakBtn = document.createElement('button');
        speakBtn.type = 'button';
        speakBtn.className = 'alx-btn-speak';
        speakBtn.setAttribute('aria-label', 'Listen - Read response aloud');
        speakBtn.title = 'Listen to response';
        speakBtn.innerHTML = `
          <svg aria-hidden="true" viewBox="0 0 24 24" style="width: 14px; height: 14px; fill: currentColor;">
            <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
          </svg>
          <span class="alx-speak-label">Listen</span>
        `;
        const labelSpan = speakBtn.querySelector('.alx-speak-label');
        const setSpeaking = (speaking) => {
          speakBtn.classList.toggle('speaking', speaking);
          labelSpan.textContent = speaking ? 'Stop' : 'Listen';
          speakBtn.setAttribute('aria-label', speaking ? 'Stop - Stop reading aloud' : 'Listen - Read response aloud');
        };
        speakBtn.addEventListener('click', () => {
          if (window.speechSynthesis.speaking) {
            window.speechSynthesis.cancel();
            setSpeaking(false);
            return;
          }
          const utterance = new SpeechSynthesisUtterance(text);
          utterance.lang = isAmharic ? 'am-ET' : 'en-US';
          utterance.onend = () => setSpeaking(false);
          utterance.onerror = () => setSpeaking(false);
          setSpeaking(true);
          window.speechSynthesis.speak(utterance);
        });
        bubble.appendChild(speakBtn);
      }

      this.messagesContainer.appendChild(bubble);
      this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    async handleSubmit(e) {
      e.preventDefault();
      const query = this.input.value.trim();
      if (!query) return;

      this.scope = this.detectScope();
      this.updateScopeBadge();

      this.appendMessage(query, 'user');
      this.input.value = '';

      // Status bubble announced via aria-live
      const statusBubble = document.createElement('div');
      statusBubble.className = 'alx-bubble alx-bubble-status';
      statusBubble.textContent = this.currentLang === 'am' ? 'መልስ እየተፈለገ ነው...' : 'Searching course material...';
      this.messagesContainer.appendChild(statusBubble);
      this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;

      try {
        const payload = {
          session: this.sessionId,
          message: query,
          language: this.currentLang,
          mode: this.simpleModeCheck.checked ? 'simple' : 'normal',
          scope: this.scope
        };

        const res = await fetch(`${this.apiUrl}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        statusBubble.remove();

        if (!res.ok) {
          throw new Error('Server returned ' + res.status);
        }

        const data = await res.json();
        this.appendMessage(data.answer, 'assistant', data.language, data.citations);

      } catch (err) {
        statusBubble.remove();
        // Offline / server unavailable fallback
        this.appendMessage(
          this.currentLang === 'am'
            ? 'ይቅርታ፣ ከአገልጋዩ ጋር መገናኘት አልተቻለም። እባክዎ የቀጥታ ረዳትን ያነጋግሩ ወይም እንደገና ይሞክሩ።'
            : 'Unable to reach the assistant server. You can connect with a live human helper using the button above.',
          'assistant',
          this.currentLang
        );
      }
    }

    async requestHumanHelp() {
      const isAmharic = this.currentLang === 'am';
      const promptText = isAmharic
        ? 'የቀጥታ ረዳት እርዳታ ይፈልጋሉ? ረዳቱን ወደ Jitsi ስክሪን መጋሪያ ክፍል ለመጋበዝ ፈቃደኛ ነዎት?'
        : 'Would you like to connect with a live tutor? A secure Jitsi meeting link will be created for you to share your screen with explicit consent.';

      if (!window.confirm(promptText)) return;

      try {
        const res = await fetch(`${this.apiUrl}/escalate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session: this.sessionId, language: isAmharic ? 'am' : 'en' })
        });
        if (!res.ok) throw new Error('Server returned ' + res.status);
        const ticket = await res.json();

        this.appendMessage(
          isAmharic
            ? `የእርዳታ ጥያቄዎ ተልኳል (${ticket.ticket_id})! ከረዳቱ ጋር ለመነጋገር እና ስክሪንዎን ለማጋራት የሚከተለውን ሊንክ ይክፈቱ፡ ${ticket.jitsi_room_url}`
            : `Human tutor request dispatched (${ticket.ticket_id})! When you are ready to share your screen, open the secure session: ${ticket.jitsi_room_url}`,
          'assistant',
          this.currentLang
        );
        window.open(ticket.jitsi_room_url, '_blank', 'noopener,noreferrer');
      } catch (err) {
        this.appendMessage(
          isAmharic
            ? 'ይቅርታ፣ የእርዳታ ጥያቄውን መላክ አልተቻለም። እባክዎ እንደገና ይሞክሩ።'
            : 'Sorry, the help request could not be sent. Please try again.',
          'assistant',
          this.currentLang
        );
      }
    }
  }

  // Register Custom Web Component
  customElements.define('alx-assistant', AlxAssistant);

  // Auto-instantiate if loaded via script tag
  function initAssistant() {
    if (!document.querySelector('alx-assistant')) {
      const script = document.currentScript || document.querySelector('script[src*="assistant.js"]');
      const assistantEl = document.createElement('alx-assistant');
      if (script) {
        if (!script.hasAttribute('data-api') && script.src) {
          try {
            const scriptUrl = new URL(script.src, window.location.href);
            assistantEl.setAttribute('data-api', scriptUrl.origin + '/api');
          } catch (e) {}
        }
        ['data-api', 'data-lang', 'data-source', 'data-scope', 'data-course-id'].forEach((name) => {
          const value = script.getAttribute(name);
          if (value) assistantEl.setAttribute(name, value);
        });
      }
      document.body.appendChild(assistantEl);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAssistant);
  } else {
    initAssistant();
  }
})();

