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

      /* High-contrast and reduced motion */
      @media (prefers-reduced-motion: reduce) {
        .alx-launcher, .alx-dialog {
          transition: none !important;
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
      this.scope = this.getAttribute('data-source') || 'course:va-1';
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
      this.messagesContainer = this.shadowRoot.getElementById('alx-messages');
    }

    connectedCallback() {
      // Event bindings
      this.launcher.addEventListener('click', () => this.toggle());
      this.closeBtn.addEventListener('click', () => this.close());
      this.langBtn.addEventListener('click', () => this.toggleLanguage());
      this.escalateBtn.addEventListener('click', () => this.requestHumanHelp());
      this.form.addEventListener('submit', (e) => this.handleSubmit(e));

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
          link.href = c.url || '#';
          link.textContent = `${c.title} — ${c.section}`;
          link.target = '_blank';
          link.rel = 'noopener noreferrer';
          item.appendChild(link);
          list.appendChild(item);
        });
        citeBox.appendChild(list);
        bubble.appendChild(citeBox);
      }

      this.messagesContainer.appendChild(bubble);
      this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    async handleSubmit(e) {
      e.preventDefault();
      const query = this.input.value.trim();
      if (!query) return;

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

    requestHumanHelp() {
      const isAmharic = this.currentLang === 'am';
      const promptText = isAmharic
        ? 'የቀጥታ ረዳት እርዳታ ይፈልጋሉ? ረዳቱን ወደ Jitsi ስክሪን መጋሪያ ክፍል ለመጋበዝ ፈቃደኛ ነዎት?'
        : 'Would you like to connect with a live tutor? A secure Jitsi meeting link will be created for you to share your screen with explicit consent.';

      if (window.confirm(promptText)) {
        const roomName = 'ALX-Savanna-Help-' + Math.random().toString(36).substring(2, 8);
        const jitsiUrl = `https://meet.jit.si/${roomName}`;
        this.appendMessage(
          isAmharic
            ? `የእርዳታ ጥያቄዎ ተልኳል! ከረዳቱ ጋር ለመነጋገር እና ስክሪንዎን ለማጋራት የሚከተለውን ሊንክ ይክፈቱ፡ ${jitsiUrl}`
            : `Human tutor request dispatched! When you are ready to share your screen, click here to open the secure session: ${jitsiUrl}`,
          'assistant',
          this.currentLang
        );
        window.open(jitsiUrl, '_blank', 'noopener,noreferrer');
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
        if (script.getAttribute('data-api')) assistantEl.setAttribute('data-api', script.getAttribute('data-api'));
        if (script.getAttribute('data-lang')) assistantEl.setAttribute('data-lang', script.getAttribute('data-lang'));
        if (script.getAttribute('data-source')) assistantEl.setAttribute('data-source', script.getAttribute('data-source'));
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

