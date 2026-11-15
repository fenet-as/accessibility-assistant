/**
 * ALX Digital Bridge Accessibility Assistant
 * Multilingual drop-in web component (Shadow DOM).
 * Languages: en, am, ti, om, so, ar — Ethiopic, Latin and Arabic scripts; RTL for Arabic.
 * WCAG 2.2 AA: keyboard, ARIA live, voice input / read-aloud with capability checks.
 */

(function () {
  'use strict';

  function ensureOfflineRuntime() {
    return new Promise((resolve) => {
      if (window.AlxOffline) { resolve(window.AlxOffline); return; }
      const existing = document.querySelector('script[data-alx-offline]');
      if (existing) {
        existing.addEventListener('load', () => resolve(window.AlxOffline || null));
        existing.addEventListener('error', () => resolve(null));
        return;
      }
      const script = document.createElement('script');
      script.src = (document.currentScript && document.currentScript.src)
        ? document.currentScript.src.replace(/assistant\.js(\?.*)?$/, 'offline.js$1')
        : '/widget/offline.js';
      script.async = true;
      script.setAttribute('data-alx-offline', '1');
      script.onload = () => resolve(window.AlxOffline || null);
      script.onerror = () => resolve(null);
      document.head.appendChild(script);
    });
  }

  function ensureVoiceRecorder() {
    return new Promise((resolve) => {
      if (window.VoiceRecorder) { resolve(window.VoiceRecorder); return; }
      const existing = document.querySelector('script[data-alx-voice-recorder]');
      if (existing) {
        existing.addEventListener('load', () => resolve(window.VoiceRecorder || null));
        existing.addEventListener('error', () => resolve(null));
        return;
      }
      const script = document.createElement('script');
      script.src = (document.currentScript && document.currentScript.src)
        ? document.currentScript.src.replace(/assistant\.js(\?.*)?$/, 'voice-recorder.js$1')
        : '/widget/voice-recorder.js';
      script.async = false;
      script.setAttribute('data-alx-voice-recorder', '1');
      script.onload = () => resolve(window.VoiceRecorder || null);
      script.onerror = () => resolve(null);
      document.head.appendChild(script);
    });
  }

  function formatMmSs(ms) {
    const total = Math.max(0, Math.floor((ms || 0) / 1000));
    const m = Math.floor(total / 60);
    const s = total % 60;
    return `${m}:${String(s).padStart(2, '0')}`;
  }


  if (customElements.get('alx-assistant')) {
    return;
  }

  const LANG_ORDER = ['en', 'am', 'ti', 'om', 'so', 'ar'];
  const LANG_META = {
    en: { name: 'English', native: 'English', script: 'latin', dir: 'ltr', speech: 'en-US', tts: 'en-US' },
    am: { name: 'Amharic', native: 'አማርኛ', script: 'ethiopic', dir: 'ltr', speech: 'am-ET', tts: 'am-ET' },
    ti: { name: 'Tigrinya', native: 'ትግርኛ', script: 'ethiopic', dir: 'ltr', speech: 'ti-ET', tts: 'ti-ET' },
    om: { name: 'Afaan Oromo', native: 'Afaan Oromo', script: 'latin', dir: 'ltr', speech: 'om-ET', tts: 'om-ET' },
    so: { name: 'Somali', native: 'Soomaali', script: 'latin', dir: 'ltr', speech: 'so-SO', tts: 'so-SO' },
    ar: { name: 'Arabic', native: 'العربية', script: 'arabic', dir: 'rtl', speech: 'ar-SA', tts: 'ar-SA' },
  };

  // Mirrors assistant/domain/language.py UI_STRINGS (offline fallback if /api/languages is unreachable).
  const UI = {
    en: {
      launcher: 'Ask Tutor', launcher_aria: 'Ask Tutor - AI Learning Assistant', header: 'ALX Learning Assistant',
      language: 'Language', language_aria: 'Select response language', auto: 'Auto-detect',
      simple_mode: 'Simple Mode', human_help: 'Live Human Help',
      human_help_aria: 'Live Human Help - Request human tutor help', close_aria: 'Close Assistant',
      placeholder: 'Ask a question about this lesson...', listening: 'Listening... Speak your question now',
      send: 'Send', send_aria: 'Send message', voice_aria: 'Voice input - Speak your question',
      voice_stop_aria: 'Stop listening - Microphone active', voice_unsupported: 'Voice input is not available in this browser',
      transcribing: 'Transcribing your speech…', stt_failed: 'Could not transcribe audio. Type your question or try again.',
      voice_needs_network: 'Voice input needs an internet connection.',
      recording_limit: 'Recording stopped at the time limit. Review the transcript before sending.',
      rec_pause: 'Pause', rec_resume: 'Resume', rec_stop: 'Stop', rec_discard: 'Discard',
      rec_replay: 'Replay', rec_retry: 'Retry transcription', rec_edit: 'Edit transcript',
      rec_uploading: 'Uploading audio…', rec_ready: 'Ready to review',
      rec_permission: 'Waiting for microphone permission…',
      rec_paused: 'Recording paused',
      mic_permission_denied: 'Microphone permission denied. Allow the mic or type your question.',
      mic_no_device: 'No microphone found. Type your question instead.',
      mic_unsupported: 'Voice recording is not supported in this browser.',
      copy: 'Copy', copied: 'Copied', retry: 'Retry', regenerate: 'Regenerate',
      typing: 'Assistant is typing',
      listen: 'Listen', listen_aria: 'Listen - Read response aloud', stop: 'Stop', stop_aria: 'Stop - Stop reading aloud',
      pause_tts: 'Pause', resume_tts: 'Resume',
      speak_unsupported: 'Read-aloud is not available for this language on this device',
      loading: 'Searching course material...',
      offline_error: 'Unable to reach the assistant server. You can connect with a live human helper using the button above.',
      welcome: 'Hello! I am Savanna, your learning assistant. I help with course material, virtual assistant skills, freelancing, remote work, and careers. Course answers cite real lessons; general educational answers are labeled clearly.',
      citations: 'Course Citations:', citation_aria: 'Go to course source',
      escalate_confirm: 'Would you like to connect with a live tutor? A secure Jitsi meeting link will be created for you to share your screen with explicit consent.',
      escalate_ok: 'Human tutor request dispatched ({ticket})! When you are ready to share your screen, open the secure session: {url}',
      escalate_fail: 'Sorry, the help request could not be sent. Please try again.',
      input_label: 'Type your question', detected: 'Detected language',
      status_online: 'Online', status_offline: 'Offline', status_syncing: 'Synchronizing…',
      badge_local: 'Local course answer', badge_cloud: 'Gemini generated',
      badge_fallback: 'FAQ fallback',
      badge_cache: 'Cached AI answer',
      badge_course: 'Course-grounded Gemini',
      badge_general: 'Gemini generated',
      badge_mixed: 'Mixed answer',
      badge_local_course: 'Local course answer',
      badge_faq: 'FAQ fallback',
      badge_social: 'Greeting',
      badge_careers: 'Careers answer',
      download_pack: 'Download for offline', downloading_pack: 'Downloading course pack…',
      pack_ready: 'Course pack ready offline', pack_error: 'Could not download the course pack',
      pack_quota: 'Not enough device storage for the course pack. Free space and try again.',
      pack_stale: 'Course update available — tap to refresh offline pack',
      sync_prompt: 'You have {n} queued offline request(s) that may include personal questions. Sync them to the server now?',
      sync_done: 'Synchronization complete ({n} sent)', sync_skip: 'Kept offline. Nothing was sent.',
      pending_badge: '{n} waiting',
      pending_send: 'Send queued questions',
      pending_discard: 'Discard queued questions',
      pack_refresh_prompt: 'A newer course pack is available (kb {remote}). Refresh offline pack now?',
      offline_no_pack: 'You are offline and this course is not downloaded yet. Open once online and tap Download for offline.',
      offline_ai_note: 'Offline mode uses downloaded course content only. Cloud AI is unavailable offline.',
      offline_using_pack: 'Server unreachable — answering from your downloaded course pack.',
      loading_local: 'Searching downloaded course material…',
      new_chat: 'New chat',
      search_chats: 'Search chats',
      chat_history: 'Chat history',
      rename_chat: 'Rename',
      delete_chat: 'Delete',
      open_sidebar: 'Open chat history',
      close_sidebar: 'Close chat history',
      today: 'Today',
      yesterday: 'Yesterday',
      previous_7_days: 'Previous 7 days',
      older: 'Older',
      suggestions_title: 'Try asking',
      suggest_1: 'What is a virtual assistant?',
      suggest_2: 'What skills do clients value?',
      suggest_3: 'How do I get started as a VA?',
      suggest_4: 'What is freelancing?',
      empty_history: 'No saved chats yet',
      composer_hint: 'Enter to send · Shift+Enter for a new line',
      connectivity_ai_offline: 'Offline — course pack only (no Gemini)',
      connectivity_ai_online: 'Online',
    },
    am: {
      launcher: 'ረዳት ጠይቅ', launcher_aria: 'ረዳት ጠይቅ - የትምህርት ረዳት', header: 'የALX የትምህርት ረዳት',
      language: 'ቋንቋ', language_aria: 'የመልስ ቋንቋ ይምረጡ', auto: 'በራስ መለየት',
      simple_mode: 'ቀላል ሁነታ', human_help: 'የቀጥታ ረዳት', human_help_aria: 'የቀጥታ ረዳት - ከሰው መምህር ጋር ይገናኙ',
      close_aria: 'ረዳቱን ዝጋ', placeholder: 'ስለዚህ ትምህርት ጥያቄዎን ይጠይቁ...', listening: 'እያዳመጠ ነው... አሁን ይናገሩ',
      send: 'ላክ', send_aria: 'መልእክት ላክ', voice_aria: 'የድምጽ ግቤት - ጥያቄዎን ይናገሩ',
      voice_stop_aria: 'ማዳመጥ አቁም - ማይክሮፎን ንቁ ነው', voice_unsupported: 'የድምጽ ግቤት በዚህ አሳሽ አይገኝም',
      transcribing: 'ድምጽዎ እየተተረጎመ ነው…', stt_failed: 'ድምጽ ሊተረጎም አልተቻለም። ጥያቄዎን ይጻፉ ወይም እንደገና ይሞክሩ።',
      voice_needs_network: 'የድምጽ ግቤት የበይነመረብ ግንኙነት ይፈልጋል።',
      recording_limit: 'ቀረጻው በጊዜ ገደብ ቆሟል። ከመላኩ በፊት ጽሑፉን ይመልከቱ።',
      rec_pause: 'ለአፍታ አቁም', rec_resume: 'ቀጥል', rec_stop: 'አቁም', rec_discard: 'አስወግድ',
      rec_replay: 'እንደገና አጫውት', rec_retry: 'ትርጉም እንደገና', rec_edit: 'ጽሑፉን አርትዕ',
      rec_uploading: 'ድምጽ እየተላከ ነው…', rec_ready: 'ለመገምገም ዝግጁ',
      rec_permission: 'የማይክሮፎን ፈቃድ በመጠባበቅ ላይ…', rec_paused: 'ቀረጻ ቆሟል',
      mic_permission_denied: 'የማይክሮፎን ፈቃድ ተከልክሏል። ጥያቄዎን ይጻፉ።',
      mic_no_device: 'ማይክሮፎን አልተገኘም። ጥያቄዎን ይጻፉ።',
      mic_unsupported: 'የድምጽ ቀረጻ በዚህ አሳሽ አይደገፍም።',
      copy: 'ቅዳ', copied: 'ተቀድቷል', retry: 'እንደገና ሞክር', regenerate: 'እንደገና ፍጠር',
      typing: 'ረዳቱ እየጻፈ ነው',
      listen: 'አዳምጥ', listen_aria: 'አዳምጥ - መልሱን በድምጽ ያንብቡ', stop: 'አቁም', stop_aria: 'አቁም - ማንበብ አቁም',
      pause_tts: 'ለአፍታ አቁም', resume_tts: 'ቀጥል',
      speak_unsupported: 'በዚህ መሣሪያ ለዚህ ቋንቋ ማንበብ አይገኝም', loading: 'መልስ እየተፈለገ ነው...',
      offline_error: 'ይቅርታ፣ ከአገልጋዩ ጋር መገናኘት አልተቻለም። እባክዎ የቀጥታ ረዳትን ያነጋግሩ ወይም እንደገና ይሞክሩ።',
      welcome: 'ሰላም! እኔ የትምህርት ረዳትዎ ነኝ። ስለዚህ ትምህርት ጥያቄዎችን ይጠይቁ። መልሶች ከትምህርቱ ይዘት ብቻ ናቸው።',
      citations: 'የተጠቀሱ ምንጮች:', citation_aria: 'ወደ ትምህርቱ ምንጭ ሂድ',
      escalate_confirm: 'የቀጥታ ረዳት እርዳታ ይፈልጋሉ? ረዳቱን ወደ Jitsi ስክሪን መጋሪያ ክፍል ለመጋበዝ ፈቃደኛ ነዎት?',
      escalate_ok: 'የእርዳታ ጥያቄዎ ተልኳል ({ticket})! ከረዳቱ ጋር ለመነጋገር እና ስክሪንዎን ለማጋራት የሚከተለውን ሊንክ ይክፈቱ፡ {url}',
      escalate_fail: 'ይቅርታ፣ የእርዳታ ጥያቄውን መላክ አልተቻለም። እባክዎ እንደገና ይሞክሩ።',
      input_label: 'ጥያቄዎን ይጻፉ', detected: 'የተለየ ቋንቋ',
      status_online: 'ኦንላይን', status_offline: 'ኦፍላይን', status_syncing: 'እየተመሳሰለ ነው…',
      badge_local: 'የአካባቢ መልስ', badge_cloud: 'የደመና መልስ',
      badge_fallback: 'የመጠባበቂያ መልስ',
      download_pack: 'ለኦፍላይን አውርድ', downloading_pack: 'የትምህርት ጥቅል እየወረደ ነው…',
      pack_ready: 'የትምህርት ጥቅል ለኦፍላይን ዝግጁ ነው', pack_error: 'የትምህርት ጥቅሉን ማውረድ አልተቻለም',
      pack_quota: 'በመሣሪያው ላይ በቂ ቦታ የለም።', pack_stale: 'የትምህርት ዝማኔ አለ — ለማደስ ይጫኑ',
      sync_prompt: '{n} የኦፍላይን ጥያቄ(ዎች) ተጠብቀዋል። ወደ አገልጋዩ ይላኩ?',
      sync_done: 'ማመሳሰል ተጠናቋል ({n} ተልኳል)', sync_skip: 'ኦፍላይን ተይዟል።',
      offline_no_pack: 'ኦፍላይን ነዎት እና ይህ ትምህርት አልተወረደም።',
      offline_ai_note: 'ኦፍላይን ሁነታ የወረደውን የትምህርት ይዘት ብቻ ይጠቀማል።',
      loading_local: 'የወረደውን የትምህርት ይዘት እየፈለገ ነው…',
    },
    ti: {
      launcher: 'ሓጋዚ ሕተት', launcher_aria: 'ሓጋዚ ሕተት - ናይ ትምህርቲ ሓጋዚ', header: 'ናይ ALX ትምህርቲ ሓጋዚ',
      language: 'ቋንቋ', language_aria: 'ቋንቋ መልሲ ምረጽ', auto: 'ብባዕሉ ምልላይ',
      simple_mode: 'ቀሊል ሞድ', human_help: 'ሓያል ሰብ ሓጋዚ', human_help_aria: 'ሓያል ሰብ ሓጋዚ - ምስ መምህር ተራኸብ',
      close_aria: 'ሓጋዚ ዕጸው', placeholder: 'ብዛዕባ እዚ ትምህርቲ ሕቶኻ ሕተት...', listening: 'ይሰምዕ ኣሎ... ሕጂ ተዛረብ',
      send: 'ላእክ', send_aria: 'መልእኽቲ ላእክ', voice_aria: 'ድምጺ ምእታው - ሕቶኻ ተዛረብ',
      voice_stop_aria: 'ምስማዕ ኣቁም', voice_unsupported: 'ድምጺ ምእታው ኣብዚ ብራውዘር የለን',
      listen: 'ሰምዕ', listen_aria: 'ሰምዕ - መልሲ ብድምጺ ኣንብብ', stop: 'ኣቁም', stop_aria: 'ኣቁም',
      speak_unsupported: 'ንዚ ቋንቋ ኣብዚ መሳርሒ ምንባብ የለን', loading: 'መልሲ ይድለ ኣሎ...',
      offline_error: 'ምስ ሰርቨር ክትራኸብ ኣይተኻእለን። በጃኹም ሓያል ሰብ ሓጋዚ ተጠቐሙ።',
      welcome: 'ሰላም! ኣነ ናይ ትምህርቲ ሓጋዝኻ እየ። ብዛዕባ እዚ ትምህርቲ ሕቶታት ሕተት። መልስታት ካብ ትሕዝቶ ትምህርቲ ጥራይ እዮም።',
      citations: 'ምንጭታት:', citation_aria: 'ናብ ምንጭ ትምህርቲ ኺድ',
      escalate_confirm: 'ምስ ሓያል መምህር ክትራኸብ ትደሊዶ? ናይ Jitsi ኣገናኽ ክፍጠር እዩ።',
      escalate_ok: 'ሕቶ ሓገዝ ተላኢኹ ({ticket})! ስክሪንካ ንምክፋል እዚ ሊንክ ክፈት፡ {url}',
      escalate_fail: 'ይቕሬታ፣ ሕቶ ሓገዝ ክለኣኽ ኣይከኣለን። ደጊምካ ፈትን።',
      input_label: 'ሕቶኻ ጸሓፍ', detected: 'ዝተለለየ ቋንቋ',
      status_online: 'ኦንላይን', status_offline: 'ኦፍላይን', status_syncing: 'ይሰማማ ኣሎ…',
      badge_local: 'ናይ ከባቢ መልሲ', badge_cloud: 'ናይ ደመና መልሲ',
      download_pack: 'ንኦፍላይን ኣውርድ', downloading_pack: 'ናይ ትምህርቲ ጥቕላል ይወርድ ኣሎ…',
      pack_ready: 'ናይ ትምህርቲ ጥቕላል ንኦፍላይን ድሉው እዩ', pack_error: 'ጥቕላል ምውራድ ኣይተኻእለን',
      pack_quota: 'ኣብ መሳርሒ እኹል ቦታ የለን።', pack_stale: 'ሓድሽ ትምህርቲ ኣሎ — ንምሕዳስ ጠውቕ',
      sync_prompt: '{n} ናይ ኦፍላይን ሕቶታት ኣለዉ። ሕጂ ናብ ሰርቨር ይለኣኽ?',
      sync_done: 'ምስማማ ተዛዚሙ ({n})', sync_skip: 'ኦፍላይን ተሓልዩ።',
      offline_no_pack: 'ኦፍላይን ኢኻ እሞ እዚ ትምህርቲ ኣይተወርደን።',
      offline_ai_note: 'ኦፍላይን ዝወረደ ትሕዝቶ ትምህርቲ ጥራይ ይጥቀም።',
      loading_local: 'ዝወረደ ትሕዝቶ ይድለ ኣሎ…',
    },
    om: {
      launcher: 'Gargaaraa Gaafadhu', launcher_aria: 'Gargaaraa Gaafadhu - Gargaaraa barnootaa', header: 'Gargaaraa Barnootaa ALX',
      language: 'Afaan', language_aria: 'Afaan deebii filadhu', auto: 'Ofumaan adda baasi',
      simple_mode: 'Haala salphaa', human_help: 'Gargaarsa Namaa', human_help_aria: 'Gargaarsa Namaa - Barsiisaan wal qunnami',
      close_aria: 'Gargaaraa cufi', placeholder: 'Waa\'ee barnoota kanaa gaaffii kee gaafadhu...', listening: 'Dhaggeeffachaa jira... Amma dubbadhu',
      send: 'Ergi', send_aria: 'Ergaa ergi', voice_aria: 'Galtee sagalee - Gaaffii kee dubbadhu',
      voice_stop_aria: 'Dhaggeeffachuu dhaabi', voice_unsupported: 'Galtee sagalee browzera kana irratti hin jiru',
      listen: 'Dhaggeeffadhu', listen_aria: 'Dhaggeeffadhu - Deebii sagaleen dubbisi', stop: 'Dhaabi', stop_aria: 'Dhaabi',
      speak_unsupported: 'Afaan kanaaf meeshaa kana irratti dubbisuu hin jiru', loading: 'Deebii barbaadaa jira...',
      offline_error: 'Serverii waliin wal qunnamiin hin dandeenye. Gargaarsa namaa fayyadami.',
      welcome: 'Akkam! Ani gargaaraa barnootaa keeti. Waa\'ee barnoota kanaa gaaffii gaafadhu. Deebiin qofa qabiyyee barnootaa irraa dhufa.',
      citations: 'Maddaalee:', citation_aria: 'Gara madda barnootaatti deemi',
      escalate_confirm: 'Barsiisaa waliin wal qunnamuu barbaaddaa? Linkii Jitsi ni uumama.',
      escalate_ok: 'Gaaffiin gargaarsaa ergame ({ticket})! Argii kee qooduuf linkii kana bani: {url}',
      escalate_fail: 'Dhiifama, gaaffiin gargaarsaa erguu hin dandeenye. Irra deebi\'ii yaali.',
      input_label: 'Gaaffii kee barreessi', detected: 'Afaan adda ba\'e',
      status_online: 'Toora irratti', status_offline: 'Toora ala', status_syncing: 'Wal simsiisaa jira…',
      badge_local: 'Deebii naannoo', badge_cloud: 'Deebii duumessa',
      download_pack: 'Toora alaaf buusi', downloading_pack: 'Paakeejii barnootaa buusaa jira…',
      pack_ready: 'Paakeejii barnootaa toora alaaf qophaaeera', pack_error: 'Paakeejii buusuu hin dandeenye',
      pack_quota: 'Kuusaa meeshaa gahaa miti.', pack_stale: 'Haaromsonni barnootaa jiru — tuqi',
      sync_prompt: 'Gaaffii toora alaa {n} qabda. Amma serveritti erguu?',
      sync_done: 'Wal simsiisuun xumurame ({n})', sync_skip: 'Toora alaatti hafe.',
      offline_no_pack: 'Toora alaatti jirta; barnoonni kun hin buufamne.',
      offline_ai_note: 'Toora alaa qabiyyee barnootaa buufame qofa fayyadama.',
      loading_local: 'Qabiyyee barnootaa buufame barbaadaa jira…',
    },
    so: {
      launcher: 'Weeydii Macallinka', launcher_aria: 'Weeydii Macallinka - Caawimaadda waxbarashada', header: 'Caawiyaha Waxbarashada ALX',
      language: 'Luqadda', language_aria: 'Dooro luqadda jawaabta', auto: 'Si toos ah u ogow',
      simple_mode: 'Hab fudud', human_help: 'Caawimaad Bini\'aadam', human_help_aria: 'Caawimaad Bini\'aadam - La xiriir macallin',
      close_aria: 'Xir caawiyaha', placeholder: 'Weydii su\'aal ku saabsan casharkan...', listening: 'Waa dhagaysanayaa... Hadda hadal',
      send: 'Dir', send_aria: 'Dir fariinta', voice_aria: 'Gelinta codka - Ku hadal su\'aashaada',
      voice_stop_aria: 'Jooji dhageysiga', voice_unsupported: 'Gelinta codka kuma jirto browser-kan',
      listen: 'Dhageyso', listen_aria: 'Dhageyso - Akhri jawaabta cod ahaan', stop: 'Jooji', stop_aria: 'Jooji',
      speak_unsupported: 'Akhinta ma heli karo luqaddan qalabkan', loading: 'Waa raadinta waxyaabaha casharka...',
      offline_error: 'Lama gaadhi karo server-ka. Isticmaal caawimaadda bini\'aadamka.',
      welcome: 'Salaan! Waxaan ahay caawiyahaaga casharka. Weydii su\'aalo ku saabsan casharkan. Jawaabuhu waxay ka yimaadaan oo keliya nuxurka casharka.',
      citations: 'Xigashooyinka:', citation_aria: 'Tag isha casharka',
      escalate_confirm: 'Ma rabtaa inaad la xiriirto macallin? Xiriir Jitsi ayaa la abuuri doonaa.',
      escalate_ok: 'Codsiga caawimaadda waa la diray ({ticket})! Fur xiriirkan si aad u wadaagto shaashadda: {url}',
      escalate_fail: 'Waan ka xumahay, codsiga lama diri karin. Fadlan isku day mar kale.',
      input_label: 'Qor su\'aashaada', detected: 'Luqadda la ogaaday',
      status_online: 'Online', status_offline: 'Offline', status_syncing: 'Waa isku-dubbaridayaa…',
      badge_local: 'Jawaab maxalli', badge_cloud: 'Jawaab daruureed',
      download_pack: 'U soo deg offline', downloading_pack: 'Xirmada casharka waa soo degaysaa…',
      pack_ready: 'Xirmada casharka offline diyaar', pack_error: 'Xirmada lama soo dejin karin',
      pack_quota: 'Kaydka qalabka kuma filna.', pack_stale: 'Cusboonaysi cashar ayaa jira',
      sync_prompt: 'Waxaad haysataa {n} codsi offline ah. Ma u dirtaa server-ka?',
      sync_done: 'Isku-dubbaridku wuu dhammaaday ({n})', sync_skip: 'Offline ayaa lagu hayay.',
      offline_no_pack: 'Offline baad tahay; casharkan weli lama soo dejin.',
      offline_ai_note: 'Offline waxay isticmaashaa oo keliya nuxurka la soo dejiyay.',
      loading_local: 'Waa raadinta nuxurka la soo dejiyay…',
    },
    ar: {
      launcher: 'اسأل المساعد', launcher_aria: 'اسأل المساعد - مساعد التعلّم', header: 'مساعد التعلّم ALX',
      language: 'اللغة', language_aria: 'اختر لغة الإجابة', auto: 'اكتشاف تلقائي',
      simple_mode: 'وضع مبسّط', human_help: 'مساعدة بشرية مباشرة',
      human_help_aria: 'مساعدة بشرية مباشرة - تواصل مع معلّم', close_aria: 'إغلاق المساعد',
      placeholder: 'اطرح سؤالاً عن هذا الدرس...', listening: 'جاري الاستماع... تحدّث الآن',
      send: 'إرسال', send_aria: 'إرسال الرسالة', voice_aria: 'إدخال صوتي - انطق سؤالك',
      voice_stop_aria: 'إيقاف الاستماع', voice_unsupported: 'الإدخال الصوتي غير متاح في هذا المتصفح',
      listen: 'استمع', listen_aria: 'استمع - اقرأ الإجابة بصوت عالٍ', stop: 'إيقاف', stop_aria: 'إيقاف القراءة',
      speak_unsupported: 'القراءة الصوتية غير متاحة لهذه اللغة على هذا الجهاز', loading: 'جاري البحث في محتوى الدورة...',
      offline_error: 'تعذّر الاتصال بالخادم. يمكنك طلب مساعدة بشرية من الزر أعلاه.',
      welcome: 'مرحبًا! أنا مساعد الدورة. اسألني عن هذا الدرس. تُستمدّ الإجابات فقط من محتوى الدورة.',
      citations: 'مراجع الدورة:', citation_aria: 'الانتقال إلى مصدر الدورة',
      escalate_confirm: 'هل تريد التواصل مع معلّم مباشر؟ سيتم إنشاء رابط Jitsi آمن لمشاركة شاشتك بموافقتك.',
      escalate_ok: 'تم إرسال طلب المساعدة ({ticket})! عند الاستعداد لمشاركة شاشتك افتح الجلسة: {url}',
      escalate_fail: 'عذرًا، تعذّر إرسال طلب المساعدة. يُرجى المحاولة مجددًا.',
      input_label: 'اكتب سؤالك', detected: 'اللغة المكتشفة',
      status_online: 'متصل', status_offline: 'غير متصل', status_syncing: 'جاري المزامنة…',
      badge_local: 'إجابة محلية', badge_cloud: 'إجابة سحابية',
      download_pack: 'تنزيل للاستخدام دون اتصال', downloading_pack: 'جاري تنزيل حزمة الدورة…',
      pack_ready: 'حزمة الدورة جاهزة دون اتصال', pack_error: 'تعذّر تنزيل حزمة الدورة',
      pack_quota: 'لا توجد مساحة كافية على الجهاز.', pack_stale: 'يتوفر تحديث للدورة',
      sync_prompt: 'لديك {n} طلب(ات) دون اتصال قد تتضمن أسئلة شخصية. هل تريد مزامنتها الآن؟',
      sync_done: 'اكتملت المزامنة ({n})', sync_skip: 'بقيت دون اتصال. لم يُرسل شيء.',
      offline_no_pack: 'أنت غير متصل ولم تُنزَّل هذه الدورة بعد.',
      offline_ai_note: 'الوضع دون اتصال يبحث في محتوى الدورة المُنزَّل فقط.',
      loading_local: 'جاري البحث في محتوى الدورة المُنزَّل…',
    },
  };


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
        --alx-font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
          "Noto Sans Ethiopic", "Noto Sans Arabic", "Segoe UI Historic", Helvetica, Arial, sans-serif;
        font-family: var(--alx-font);
        color: var(--alx-text);
        box-sizing: border-box;
      }
      *, *::before, *::after { box-sizing: inherit; }
      .alx-launcher {
        position: fixed; bottom: 24px; right: 24px; z-index: 999999;
        display: flex; align-items: center; gap: 8px; padding: 12px 18px;
        min-width: 48px; min-height: 48px; background-color: var(--alx-primary); color: #ffffff;
        border: 2px solid transparent; border-radius: 9999px; font-size: 15px; font-weight: 600;
        cursor: pointer; box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
        transition: transform 0.2s ease, background-color 0.2s ease; font-family: inherit;
      }
      .alx-launcher:hover { background-color: var(--alx-primary-hover); transform: translateY(-2px); }
      .alx-launcher:focus-visible { outline: 3px solid #ffffff; outline-offset: 2px; border-color: var(--alx-primary); }
      .alx-launcher svg { width: 22px; height: 22px; fill: currentColor; flex-shrink: 0; }
      .alx-dialog {
        --alx-dialog-w: min(720px, calc(100vw - 24px));
        --alx-dialog-h: min(640px, calc(100vh - 100px));
        position: fixed; bottom: 84px; right: 24px; z-index: 999999;
        width: var(--alx-dialog-w); height: var(--alx-dialog-h);
        max-width: calc(100vw - 16px); max-height: calc(100vh - 72px);
        min-width: 300px; min-height: 360px;
        background: var(--alx-bg); border: 1px solid var(--alx-border); border-radius: var(--alx-radius);
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.18); display: flex; flex-direction: column; overflow: hidden;
      }
      .alx-dialog[hidden] { display: none !important; }
      .alx-dialog[data-maximized="true"] {
        top: 8px !important; right: 8px !important; bottom: 8px !important; left: 8px !important;
        width: auto !important; height: auto !important; max-width: none; max-height: none;
        border-radius: 10px;
      }
      .alx-resize-handle {
        position: absolute; width: 20px; height: 20px; left: 2px; top: 2px; z-index: 5;
        cursor: nwse-resize; touch-action: none;
        background:
          linear-gradient(135deg, #94a3b8 0 2px, transparent 2px) no-repeat,
          linear-gradient(135deg, #94a3b8 0 2px, transparent 2px) no-repeat;
        background-size: 10px 10px, 6px 6px;
        background-position: 4px 4px, 4px 4px;
        border: none; padding: 0; border-radius: 4px;
      }
      .alx-resize-handle:focus-visible { outline: 2px solid var(--alx-focus); outline-offset: 1px; }
      .alx-btn-resize {
        background: transparent; border: 1px solid var(--alx-border); border-radius: 6px;
        padding: 6px 8px; font-size: 12px; font-weight: 700; cursor: pointer; min-height: 36px;
        color: var(--alx-text); font-family: inherit;
      }
      .alx-body { flex: 1; display: flex; min-height: 0; position: relative; }
      .alx-sidebar {
        width: 260px; flex-shrink: 0; border-right: 1px solid var(--alx-border);
        background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
        display: flex; flex-direction: column; min-height: 0;
      }
      .alx-sidebar[hidden] { display: none !important; }
      .alx-sidebar-head { padding: 10px; display: flex; flex-direction: column; gap: 8px; border-bottom: 1px solid var(--alx-border); }
      .alx-btn-newchat {
        width: 100%; min-height: 40px; border: none; border-radius: 8px; cursor: pointer;
        background: var(--alx-primary); color: #fff; font-weight: 700; font-size: 13px; font-family: inherit;
      }
      .alx-btn-newchat:focus-visible { outline: 3px solid var(--alx-focus); outline-offset: 1px; }
      .alx-search-chats {
        width: 100%; padding: 8px 10px; border: 1px solid var(--alx-border); border-radius: 8px;
        font: inherit; font-size: 12px; background: #fff; color: var(--alx-text);
      }
      .alx-conv-list { flex: 1; overflow-y: auto; padding: 8px; display: flex; flex-direction: column; gap: 4px; }
      .alx-conv-group-label {
        font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em;
        color: var(--alx-text-muted); padding: 8px 6px 4px;
      }
      .alx-conv-item {
        display: flex; align-items: center; gap: 4px; border-radius: 8px; border: 1px solid transparent;
        background: transparent; padding: 2px;
      }
      .alx-conv-item.active { background: #fff; border-color: var(--alx-border); box-shadow: 0 1px 2px rgba(15,23,42,.06); }
      .alx-conv-open {
        flex: 1; text-align: left; border: none; background: transparent; cursor: pointer;
        padding: 8px; font: inherit; font-size: 12px; font-weight: 600; color: var(--alx-text);
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-height: 36px;
      }
      .alx-conv-actions { display: flex; gap: 2px; }
      .alx-conv-actions button {
        border: none; background: transparent; cursor: pointer; font-size: 11px; min-width: 28px; min-height: 28px;
        border-radius: 6px; color: var(--alx-text-muted); font-family: inherit;
      }
      .alx-conv-actions button:hover { background: #e2e8f0; }
      .alx-main { flex: 1; display: flex; flex-direction: column; min-width: 0; min-height: 0; }
      .alx-welcome-wrap { display: flex; flex-direction: column; gap: 12px; }
      .alx-suggestions { display: flex; flex-wrap: wrap; gap: 8px; }
      .alx-suggestion {
        border: 1px solid var(--alx-border); background: #fff; border-radius: 9999px;
        padding: 8px 12px; font-size: 12px; font-weight: 600; cursor: pointer; font-family: inherit;
        color: var(--alx-text); min-height: 36px;
      }
      .alx-suggestion:hover { border-color: var(--alx-primary); color: var(--alx-primary); }
      .alx-suggestion:focus-visible { outline: 3px solid var(--alx-focus); }
      .alx-md p { margin: 0 0 0.55em; }
      .alx-md p:last-child { margin-bottom: 0; }
      .alx-md ul, .alx-md ol { margin: 0.35em 0 0.55em; padding-left: 1.25em; }
      .alx-md code {
        font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        font-size: 0.92em; background: #e2e8f0; padding: 0.1em 0.35em; border-radius: 4px;
      }
      .alx-md pre {
        background: #0f172a; color: #e2e8f0; padding: 10px 12px; border-radius: 8px;
        overflow-x: auto; font-size: 12px; line-height: 1.45;
      }
      .alx-md pre code { background: transparent; color: inherit; padding: 0; }
      .alx-md strong { font-weight: 700; }
      .alx-md a { color: var(--alx-primary); }
      .alx-composer-wrap { display: flex; flex-direction: column; gap: 6px; flex: 1; min-width: 0; }
      .alx-composer-hint { font-size: 11px; color: var(--alx-text-muted); }
      .alx-input-form { align-items: flex-end; }
      .alx-sidebar-backdrop {
        display: none; position: absolute; inset: 0; background: rgba(15,23,42,0.35); z-index: 2;
      }
      .alx-sidebar-backdrop[data-open="true"] { display: block; }
      @media (max-width: 720px) {
        .alx-sidebar {
          position: absolute; inset: 0 auto 0 0; z-index: 3; width: min(280px, 86vw);
          box-shadow: 8px 0 24px rgba(15,23,42,0.18);
        }
        .alx-dialog {
          --alx-dialog-w: calc(100vw - 12px);
          --alx-dialog-h: calc(100vh - 84px);
          right: 6px; bottom: 70px; left: auto;
          width: var(--alx-dialog-w); height: var(--alx-dialog-h);
        }
        .alx-resize-handle { display: none; }
      }
      @media (max-width: 480px) {
        .alx-dialog {
          top: 0; right: 0; bottom: 0; left: 0;
          width: 100vw !important; height: 100vh !important;
          max-width: 100vw; max-height: 100vh;
          border-radius: 0; bottom: 0;
        }
        .alx-launcher { right: 12px; bottom: 12px; }
        .alx-header-title { font-size: 14px; }
        .alx-status-bar { flex-wrap: wrap; }
        .alx-resize-handle, .alx-btn-resize { display: none; }
      }
      .alx-dialog[dir="rtl"] .alx-bubble-user { align-self: flex-start; border-bottom-right-radius: 12px; border-bottom-left-radius: 2px; }
      .alx-dialog[dir="rtl"] .alx-bubble-assistant { align-self: flex-end; border-bottom-left-radius: 12px; border-bottom-right-radius: 2px; }
      .alx-header {
        background-color: var(--alx-surface); padding: 12px 16px; border-bottom: 1px solid var(--alx-border);
        display: flex; align-items: center; justify-content: space-between; gap: 8px;
      }
      .alx-header-title { font-size: 16px; font-weight: 700; margin: 0; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
      .alx-scope-badge {
        font-size: 11px; font-weight: 700; padding: 2px 7px; border-radius: 9999px;
        background-color: #e0f2fe; color: #0369a1; text-transform: uppercase; letter-spacing: 0.3px;
      }
      .alx-header-controls { display: flex; align-items: center; gap: 6px; }
      .alx-lang-label { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); border: 0; }
      .alx-lang-select {
        background: #ffffff; border: 1px solid var(--alx-border); border-radius: 6px; padding: 6px 8px;
        font-size: 12px; font-weight: 600; cursor: pointer; color: var(--alx-text); min-height: 36px;
        max-width: 140px; font-family: inherit;
      }
      .alx-lang-select:focus-visible { outline: 3px solid var(--alx-focus); outline-offset: 1px; }
      .alx-btn-icon {
        background: transparent; border: 1px solid var(--alx-border); border-radius: 6px; padding: 6px 10px;
        font-size: 13px; font-weight: 600; cursor: pointer; color: var(--alx-text); min-height: 36px;
        display: inline-flex; align-items: center; justify-content: center;
      }
      .alx-btn-icon:hover { background-color: #e5e9f0; }
      .alx-btn-icon:focus-visible { outline: 3px solid var(--alx-focus); outline-offset: 1px; }
      .alx-toolbar {
        background: #ffffff; padding: 6px 16px; border-bottom: 1px solid var(--alx-border);
        display: flex; align-items: center; justify-content: space-between; font-size: 13px; gap: 8px;
      }
      .alx-toggle-group { display: flex; align-items: center; gap: 4px; }
      .alx-btn-help {
        background: #fff1f1; color: #b81922; border: 1px solid #ffd7d9; font-weight: 600;
        padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 12px; font-family: inherit;
      }
      .alx-btn-help:hover { background: #ffe3e5; }
      .alx-btn-help:focus-visible { outline: 3px solid var(--alx-danger); }
      .alx-messages { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; }
      .alx-bubble {
        max-width: 88%; padding: 10px 14px; border-radius: 12px; font-size: 14px; line-height: 1.55; word-break: break-word;
      }
      .alx-bubble[lang="am"], .alx-bubble[lang="ti"], .alx-bubble[lang="ar"] { line-height: 1.7; }
      .alx-bubble-user { align-self: flex-end; background-color: var(--alx-primary); color: #ffffff; border-bottom-right-radius: 2px; }
      .alx-bubble-assistant {
        align-self: flex-start; background-color: var(--alx-surface); color: var(--alx-text);
        border: 1px solid var(--alx-border); border-bottom-left-radius: 2px;
      }
      .alx-bubble-status { align-self: center; font-style: italic; color: var(--alx-text-muted); font-size: 13px; background: transparent; }
      .alx-citations { margin-top: 8px; padding-top: 8px; border-top: 1px dashed var(--alx-border); font-size: 12px; }
      .alx-citations-title { font-weight: 600; color: var(--alx-text-muted); margin-bottom: 4px; }
      .alx-citations-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 3px; }
      .alx-citation-link { color: var(--alx-primary); text-decoration: underline; font-weight: 500; }
      .alx-citation-link:hover { color: var(--alx-primary-hover); }
      .alx-citation-link:focus-visible { outline: 2px solid var(--alx-focus); }
      .alx-input-area { padding: 12px 16px; border-top: 1px solid var(--alx-border); background: var(--alx-surface); }
      .alx-input-form { display: flex; gap: 8px; }
      .alx-input-field {
        flex: 1; padding: 10px 12px; font-size: 14px; border: 1px solid var(--alx-border);
        border-radius: 10px; background: #ffffff; color: var(--alx-text); font-family: inherit;
        resize: none; min-height: 44px; max-height: 140px; line-height: 1.4;
      }
      .alx-input-field:focus-visible { outline: 3px solid var(--alx-focus); outline-offset: -1px; }
      .alx-btn-send {
        background-color: var(--alx-primary); color: #ffffff; border: none; border-radius: 6px;
        padding: 0 16px; font-weight: 600; font-size: 14px; cursor: pointer; min-height: 40px; font-family: inherit;
      }
      .alx-btn-send:hover { background-color: var(--alx-primary-hover); }
      .alx-btn-send:focus-visible { outline: 3px solid var(--alx-focus); outline-offset: 1px; }
      .alx-btn-voice {
        background-color: transparent; border: 1px solid var(--alx-border); border-radius: 6px; padding: 0 10px;
        cursor: pointer; min-width: 40px; min-height: 40px; display: inline-flex; align-items: center;
        justify-content: center; color: var(--alx-text); transition: all 0.2s ease;
      }
      .alx-btn-voice svg { width: 18px; height: 18px; fill: currentColor; }
      .alx-btn-voice:hover { background-color: #f1f5f9; color: var(--alx-primary); }
      .alx-btn-voice:focus-visible { outline: 3px solid var(--alx-focus); outline-offset: 1px; }
      .alx-btn-voice.listening { background-color: #fee2e2; border-color: #ef4444; color: #dc2626; animation: alx-pulse 1.2s infinite ease-in-out; }
      .alx-btn-voice[hidden], .alx-btn-speak[hidden] { display: none !important; }
      @keyframes alx-pulse { 0% { transform: scale(1); } 50% { transform: scale(1.08); } 100% { transform: scale(1); } }
      .alx-btn-speak {
        background: transparent; border: 1px solid var(--alx-border); border-radius: 4px; padding: 2px 8px;
        font-size: 11px; font-weight: 600; cursor: pointer; color: var(--alx-text-muted);
        display: inline-flex; align-items: center; gap: 4px; margin-top: 6px; min-height: 28px; font-family: inherit;
      }
      .alx-btn-speak:hover { background-color: #f1f5f9; color: var(--alx-primary); }
      .alx-btn-speak:focus-visible { outline: 2px solid var(--alx-focus); }
      .alx-btn-speak.speaking { background-color: #eff6ff; border-color: var(--alx-primary); color: var(--alx-primary); }
      .alx-voice-note { font-size: 11px; color: var(--alx-text-muted); margin-top: 6px; }
      .alx-rec-bar {
        display: none; flex-wrap: wrap; align-items: center; gap: 8px;
        margin-top: 8px; padding: 8px 10px; border: 1px solid #fecaca; border-radius: 8px; background: #fff1f2;
      }
      .alx-rec-bar[data-active="true"] { display: flex; }
      .alx-rec-dot {
        width: 10px; height: 10px; border-radius: 50%; background: #dc2626;
        animation: alx-pulse 1.2s infinite ease-in-out;
      }
      .alx-rec-dot.paused { background: #ca8a04; animation: none; }
      .alx-rec-timer { font-variant-numeric: tabular-nums; font-weight: 700; font-size: 13px; color: #991b1b; min-width: 3rem; }
      .alx-rec-meter { flex: 1 1 60px; height: 8px; border-radius: 9999px; background: #fecaca; overflow: hidden; min-width: 48px; }
      .alx-rec-meter > span { display: block; height: 100%; width: 0%; background: #dc2626; transition: width 80ms linear; }
      .alx-rec-actions { display: flex; flex-wrap: wrap; gap: 6px; }
      .alx-rec-actions button {
        min-height: 44px; min-width: 44px; padding: 6px 12px; border-radius: 6px;
        border: 1px solid var(--alx-border); background: #fff; color: var(--alx-text);
        font-size: 12px; font-weight: 600; cursor: pointer; font-family: inherit;
      }
      .alx-rec-actions button:focus-visible { outline: 2px solid var(--alx-focus); }
      .alx-rec-actions .alx-rec-stop { background: #dc2626; color: #fff; border-color: #b91c1c; }
      .alx-review-panel {
        display: none; flex-direction: column; gap: 8px; margin-top: 8px;
        padding: 10px; border: 1px solid var(--alx-border); border-radius: 8px; background: #f8fafc;
      }
      .alx-review-panel[data-active="true"] { display: flex; }
      .alx-review-panel textarea {
        width: 100%; min-height: 72px; resize: vertical; border: 1px solid var(--alx-border);
        border-radius: 6px; padding: 8px; font: inherit; color: var(--alx-text); box-sizing: border-box;
      }
      .alx-review-actions { display: flex; flex-wrap: wrap; gap: 6px; }
      .alx-review-actions button {
        min-height: 44px; padding: 6px 12px; border-radius: 6px; border: 1px solid var(--alx-border);
        background: #fff; font-size: 12px; font-weight: 600; cursor: pointer; font-family: inherit;
      }
      .alx-review-actions .alx-review-send { background: var(--alx-primary); color: #fff; border-color: var(--alx-primary); }
      .alx-typing { display: inline-flex; gap: 4px; align-items: center; padding: 4px 0; }
      .alx-typing span {
        width: 6px; height: 6px; border-radius: 50%; background: #94a3b8;
        animation: alx-bounce 1.2s infinite ease-in-out;
      }
      .alx-typing span:nth-child(2) { animation-delay: 0.15s; }
      .alx-typing span:nth-child(3) { animation-delay: 0.3s; }
      @keyframes alx-bounce {
        0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
        40% { transform: translateY(-4px); opacity: 1; }
      }
      .alx-msg-actions { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
      .alx-msg-actions button {
        min-height: 32px; padding: 4px 10px; border-radius: 4px; border: 1px solid var(--alx-border);
        background: #fff; color: var(--alx-text-muted); font-size: 11px; font-weight: 600;
        cursor: pointer; font-family: inherit;
      }
      .alx-msg-actions button:focus-visible { outline: 2px solid var(--alx-focus); }
      .alx-answer-badge.fallback { background: #fff7ed; color: #c2410c; border: 1px solid #fed7aa; }
      .alx-bubble-error { background: #fef2f2; border: 1px solid #fecaca; color: #991b1b; }
      @media (prefers-reduced-motion: reduce) {
        .alx-launcher, .alx-dialog, .alx-btn-voice.listening, .alx-rec-dot, .alx-typing span {
          transition: none !important; animation: none !important;
        }
      }
      .alx-status-bar {
        display: flex; align-items: center; justify-content: space-between; gap: 8px;
        padding: 4px 16px; border-bottom: 1px solid var(--alx-border); background: #f8fafc;
        font-size: 11px; font-weight: 600;
      }
      .alx-status-pill {
        display: inline-flex; align-items: center; gap: 6px; padding: 2px 8px; border-radius: 9999px;
        background: #e2e8f0; color: #334155;
      }
      .alx-status-pill.online { background: #dcfce7; color: #166534; }
      .alx-status-pill.offline { background: #fee2e2; color: #991b1b; }
      .alx-status-pill.syncing { background: #dbeafe; color: #1d4ed8; }
      .alx-status-dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
      .alx-btn-pack {
        background: transparent; border: 1px solid var(--alx-border); border-radius: 4px;
        padding: 2px 8px; font-size: 11px; font-weight: 600; cursor: pointer; font-family: inherit;
        color: var(--alx-text); min-height: 28px;
      }
      .alx-btn-pack:focus-visible { outline: 2px solid var(--alx-focus); }
      .alx-answer-badge {
        display: inline-block; margin-top: 6px; margin-right: 6px; padding: 1px 7px; border-radius: 9999px;
        font-size: 10px; font-weight: 700; letter-spacing: 0.2px;
      }
      .alx-answer-badge.local { background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; }
      .alx-answer-badge.cloud { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
      .alx-answer-badge.fallback { background: #fff7ed; color: #c2410c; border: 1px solid #fed7aa; }
      .alx-answer-badge.cache { background: #f5f3ff; color: #5b21b6; border: 1px solid #ddd6fe; }
      .alx-answer-badge.general { background: #f0f9ff; color: #0369a1; border: 1px solid #bae6fd; }
      .alx-answer-badge.mixed { background: #fdf4ff; color: #a21caf; border: 1px solid #f5d0fe; }
      .alx-answer-badge.faq { background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; }
      .alx-answer-badge.careers { background: #fffbeb; color: #b45309; border: 1px solid #fde68a; }
      .alx-answer-badge.social { background: #f8fafc; color: #475569; border: 1px solid #e2e8f0; }
    </style>

    <button type="button" class="alx-launcher" id="alx-launcher" aria-haspopup="dialog" aria-expanded="false" aria-label="Ask Tutor - AI Learning Assistant">
      <svg aria-hidden="true" viewBox="0 0 24 24">
        <path d="M12 2C6.48 2 2 6.48 2 12c0 1.85.5 3.58 1.38 5.08L2 22l5.08-1.38C8.42 21.5 10.15 22 12 22c5.52 0 10-4.48 10-10S17.52 2 12 2zm1 14h-2v-2h2v2zm0-4h-2V7h2v5z"/>
      </svg>
      <span id="alx-launcher-text">Ask Tutor</span>
    </button>

    <div class="alx-dialog" id="alx-dialog" role="dialog" aria-modal="false" aria-labelledby="alx-title" hidden dir="ltr" lang="en">
      <div class="alx-header">
        <h2 class="alx-header-title" id="alx-title">
          <svg aria-hidden="true" style="width: 20px; height: 20px; fill: var(--alx-primary);" viewBox="0 0 24 24">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9v-2h2v2zm0-4H9V7h2v5z"/>
          </svg>
          <span id="alx-header-label">ALX Learning Assistant</span>
          <span class="alx-scope-badge" id="alx-scope-badge" aria-label="Course scope">VA-1</span>
        </h2>
        <div class="alx-header-controls">
          <button type="button" class="alx-btn-icon" id="alx-sidebar-btn" title="Open chat history" aria-label="Open chat history" aria-expanded="false">☰</button>
          <label class="alx-lang-label" for="alx-lang-select" id="alx-lang-label">Language</label>
          <select class="alx-lang-select" id="alx-lang-select" aria-label="Select response language"></select>
          <button type="button" class="alx-btn-icon" id="alx-newchat-btn" title="New chat" aria-label="New chat">＋</button>
          <button type="button" class="alx-btn-resize" id="alx-maximize-btn" title="Expand chat" aria-label="Expand chat">⛶</button>
          <button type="button" class="alx-btn-icon" id="alx-close-btn" aria-label="Close Assistant">✕</button>
        </div>
      </div>

      <div class="alx-body">
        <div class="alx-sidebar-backdrop" id="alx-sidebar-backdrop" data-open="false" hidden></div>
        <aside class="alx-sidebar" id="alx-sidebar" aria-label="Chat history">
          <div class="alx-sidebar-head">
            <button type="button" class="alx-btn-newchat" id="alx-sidebar-new">New chat</button>
            <input type="search" class="alx-search-chats" id="alx-search-chats" placeholder="Search chats" aria-label="Search chats" />
          </div>
          <div class="alx-conv-list" id="alx-conv-list" role="list"></div>
        </aside>
        <div class="alx-main">
      <div class="alx-status-bar" id="alx-status-bar" role="status" aria-live="polite">
        <span class="alx-status-pill online" id="alx-conn-status"><span class="alx-status-dot" aria-hidden="true"></span><span id="alx-conn-label">Online</span></span>
        <span class="alx-status-pill offline" id="alx-pending-badge" hidden></span>
        <button type="button" class="alx-btn-pack" id="alx-pending-send" hidden>Send queued</button>
        <button type="button" class="alx-btn-pack" id="alx-pending-discard" hidden>Discard</button>
        <button type="button" class="alx-btn-pack" id="alx-pack-btn">Download for offline</button>
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

      <div class="alx-messages" id="alx-messages" role="log" aria-live="polite" aria-atomic="false">
        <div class="alx-welcome-wrap" id="alx-welcome-wrap">
          <div class="alx-bubble alx-bubble-assistant" id="alx-welcome" lang="en" dir="ltr"></div>
          <div class="alx-suggestions" id="alx-suggestions" aria-label="Suggested prompts"></div>
        </div>
      </div>

      <div class="alx-input-area">
        <form class="alx-input-form" id="alx-form">
          <div class="alx-composer-wrap">
            <label for="alx-input" class="alx-lang-label" id="alx-input-label">Type your question</label>
            <textarea class="alx-input-field" id="alx-input" placeholder="Ask a question about this lesson..." rows="1" required></textarea>
            <div class="alx-composer-hint" id="alx-composer-hint">Enter to send · Shift+Enter for a new line</div>
          </div>
          <button type="button" class="alx-btn-voice" id="alx-voice-btn" aria-label="Voice input - Speak your question" aria-pressed="false" title="Voice input">
            <svg aria-hidden="true" viewBox="0 0 24 24">
              <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5-3c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
            </svg>
          </button>
          <button type="submit" class="alx-btn-send" id="alx-send-btn" aria-label="Send message">Send</button>
        </form>
        <div class="alx-rec-bar" id="alx-rec-bar" data-active="false" role="status" aria-live="polite">
          <span class="alx-rec-dot" id="alx-rec-dot" aria-hidden="true"></span>
          <span class="alx-rec-timer" id="alx-rec-timer">0:00</span>
          <div class="alx-rec-meter" id="alx-rec-meter" aria-hidden="true"><span id="alx-rec-level"></span></div>
          <div class="alx-rec-actions">
            <button type="button" id="alx-rec-pause" data-i18n="rec_pause">Pause</button>
            <button type="button" class="alx-rec-stop" id="alx-rec-stop" data-i18n="rec_stop">Stop</button>
            <button type="button" id="alx-rec-discard" data-i18n="rec_discard">Discard</button>
          </div>
        </div>
        <div class="alx-review-panel" id="alx-review-panel" data-active="false">
          <label for="alx-review-text" class="alx-lang-label" id="alx-review-label">Edit transcript</label>
          <textarea id="alx-review-text" rows="3"></textarea>
          <audio id="alx-review-audio" controls hidden></audio>
          <div class="alx-review-actions">
            <button type="button" id="alx-review-replay" data-i18n="rec_replay">Replay</button>
            <button type="button" id="alx-review-retry" data-i18n="rec_retry">Retry transcription</button>
            <button type="button" id="alx-review-discard" data-i18n="rec_discard">Discard</button>
            <button type="button" class="alx-review-send" id="alx-review-send" data-i18n="send">Send</button>
          </div>
        </div>
        <div class="alx-voice-note" id="alx-voice-note" hidden></div>
      </div>
        </div>
      </div>
      <button type="button" class="alx-resize-handle" id="alx-resize-handle" aria-label="Resize chat window" title="Drag to resize"></button>
    </div>
  `;

  class AlxAssistant extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: 'open' });
      this.shadowRoot.appendChild(TEMPLATE.content.cloneNode(true));

      this.isOpen = false;
      this.uiPack = UI;
      this.langMeta = LANG_META;
      const saved = this._readSavedLang();
      this.currentLang = this.getAttribute('data-lang') || saved || 'auto';
      this.apiUrl = this.getAttribute('data-api') || 'http://localhost:8000/api';
      this.scopeBadge = this.shadowRoot.getElementById('alx-scope-badge');
      this.scope = this.detectScope();
      this.updateScopeBadge();
      this.ownerId = this._getOrCreateOwnerId();
      this.sessionId = 'anon-' + Math.random().toString(36).substring(2, 9);
      this.conversationId = null;
      this._conversations = [];
      this._sidebarOpen = true;
      this.sessionLang = null;
      this.serverStt = false;
      this._sttProbeDone = false;
      this.voiceRecorder = null;
      this._activeUploadSession = null;
      this._voiceTimings = null;
      this.isSubmitting = false;
      this._lastUserMessage = null;
      this._ttsController = { utterance: null, bubbleId: null, paused: false };
      this.ttsVoices = [];
      this.speechSupported = false;
      this.ttsSupported = typeof window !== 'undefined' && 'speechSynthesis' in window;

      this.launcher = this.shadowRoot.getElementById('alx-launcher');
      this.dialog = this.shadowRoot.getElementById('alx-dialog');
      this.closeBtn = this.shadowRoot.getElementById('alx-close-btn');
      this.clearBtn = null;
      this.maximizeBtn = this.shadowRoot.getElementById('alx-maximize-btn');
      this.resizeHandle = this.shadowRoot.getElementById('alx-resize-handle');
      this._dialogMaximized = false;
      this._resizeState = null;
      this.sidebarBtn = this.shadowRoot.getElementById('alx-sidebar-btn');
      this.newChatBtn = this.shadowRoot.getElementById('alx-newchat-btn');
      this.sidebar = this.shadowRoot.getElementById('alx-sidebar');
      this.sidebarBackdrop = this.shadowRoot.getElementById('alx-sidebar-backdrop');
      this.sidebarNewBtn = this.shadowRoot.getElementById('alx-sidebar-new');
      this.searchChats = this.shadowRoot.getElementById('alx-search-chats');
      this.convList = this.shadowRoot.getElementById('alx-conv-list');
      this.welcomeWrap = this.shadowRoot.getElementById('alx-welcome-wrap');
      this.suggestionsEl = this.shadowRoot.getElementById('alx-suggestions');
      this.composerHint = this.shadowRoot.getElementById('alx-composer-hint');
      this.langSelect = this.shadowRoot.getElementById('alx-lang-select');
      this.simpleModeCheck = this.shadowRoot.getElementById('alx-simple-mode');
      this.escalateBtn = this.shadowRoot.getElementById('alx-escalate-btn');
      this.form = this.shadowRoot.getElementById('alx-form');
      this.input = this.shadowRoot.getElementById('alx-input');
      this.voiceBtn = this.shadowRoot.getElementById('alx-voice-btn');
      this.voiceNote = this.shadowRoot.getElementById('alx-voice-note');
      this.recBar = this.shadowRoot.getElementById('alx-rec-bar');
      this.recDot = this.shadowRoot.getElementById('alx-rec-dot');
      this.recTimer = this.shadowRoot.getElementById('alx-rec-timer');
      this.recLevel = this.shadowRoot.getElementById('alx-rec-level');
      this.recPauseBtn = this.shadowRoot.getElementById('alx-rec-pause');
      this.recStopBtn = this.shadowRoot.getElementById('alx-rec-stop');
      this.recDiscardBtn = this.shadowRoot.getElementById('alx-rec-discard');
      this.reviewPanel = this.shadowRoot.getElementById('alx-review-panel');
      this.reviewText = this.shadowRoot.getElementById('alx-review-text');
      this.reviewAudio = this.shadowRoot.getElementById('alx-review-audio');
      this.reviewReplayBtn = this.shadowRoot.getElementById('alx-review-replay');
      this.reviewRetryBtn = this.shadowRoot.getElementById('alx-review-retry');
      this.reviewDiscardBtn = this.shadowRoot.getElementById('alx-review-discard');
      this.reviewSendBtn = this.shadowRoot.getElementById('alx-review-send');
      this.reviewLabel = this.shadowRoot.getElementById('alx-review-label');
      this.messagesContainer = this.shadowRoot.getElementById('alx-messages');
      this.welcomeBubble = this.shadowRoot.getElementById('alx-welcome');
      this.sendBtn = this.shadowRoot.getElementById('alx-send-btn');
      this.connStatus = this.shadowRoot.getElementById('alx-conn-status');
      this.connLabel = this.shadowRoot.getElementById('alx-conn-label');
      this.pendingBadge = this.shadowRoot.getElementById('alx-pending-badge');
      this.pendingSendBtn = this.shadowRoot.getElementById('alx-pending-send');
      this.pendingDiscardBtn = this.shadowRoot.getElementById('alx-pending-discard');
      this.packBtn = this.shadowRoot.getElementById('alx-pack-btn');
      this.connectionState = 'online';
      this.offlineRuntime = null;
      this._syncPrompted = false;
      this._reviewObjectUrl = null;
    }

    _readSavedLang() {
      try {
        return localStorage.getItem('alx-assistant-lang') || '';
      } catch (e) {
        return '';
      }
    }

    _saveLang(code) {
      try {
        localStorage.setItem('alx-assistant-lang', code);
      } catch (e) { /* private browsing */ }
    }

    _getOrCreateOwnerId() {
      const key = 'alx_owner_id';
      try {
        if (typeof window !== 'undefined' && window.localStorage) {
          let id = window.localStorage.getItem(key);
          if (!id) {
            id = 'device-' + Math.random().toString(36).slice(2) + Date.now().toString(36);
            window.localStorage.setItem(key, id);
          }
          return id;
        }
      } catch (e) { /* private browsing */ }
      return 'anon-' + Math.random().toString(36).slice(2, 11);
    }

    _dialogSizeKey() {
      return 'alx_dialog_size_v1';
    }

    _restoreDialogSize() {
      if (!this.dialog) return;
      try {
        const raw = window.localStorage.getItem(this._dialogSizeKey());
        if (!raw) return;
        const saved = JSON.parse(raw);
        if (saved && saved.maximized) {
          this._setMaximized(true, false);
          return;
        }
        if (saved && saved.w && saved.h) {
          this._applyDialogSize(saved.w, saved.h, false);
        }
      } catch (e) { /* ignore */ }
    }

    _persistDialogSize() {
      try {
        if (this._dialogMaximized) {
          window.localStorage.setItem(this._dialogSizeKey(), JSON.stringify({ maximized: true }));
          return;
        }
        const rect = this.dialog.getBoundingClientRect();
        window.localStorage.setItem(this._dialogSizeKey(), JSON.stringify({
          w: Math.round(rect.width),
          h: Math.round(rect.height),
          maximized: false,
        }));
      } catch (e) { /* ignore */ }
    }

    _applyDialogSize(width, height, persist) {
      if (!this.dialog || this._dialogMaximized) return;
      const maxW = Math.max(300, window.innerWidth - 16);
      const maxH = Math.max(360, window.innerHeight - 72);
      const w = Math.min(maxW, Math.max(300, width));
      const h = Math.min(maxH, Math.max(360, height));
      this.dialog.style.width = w + 'px';
      this.dialog.style.height = h + 'px';
      this.dialog.style.setProperty('--alx-dialog-w', w + 'px');
      this.dialog.style.setProperty('--alx-dialog-h', h + 'px');
      if (persist !== false) this._persistDialogSize();
    }

    _setMaximized(on, persist) {
      this._dialogMaximized = !!on;
      if (!this.dialog) return;
      this.dialog.dataset.maximized = this._dialogMaximized ? 'true' : 'false';
      if (this.maximizeBtn) {
        this.maximizeBtn.textContent = this._dialogMaximized ? '❐' : '⛶';
        this.maximizeBtn.title = this._dialogMaximized ? 'Restore chat size' : 'Expand chat';
        this.maximizeBtn.setAttribute('aria-label', this.maximizeBtn.title);
      }
      if (this.resizeHandle) this.resizeHandle.hidden = this._dialogMaximized || window.innerWidth <= 720;
      if (persist !== false) this._persistDialogSize();
    }

    _initResizeControls() {
      if (this.maximizeBtn) {
        this.maximizeBtn.addEventListener('click', () => this._setMaximized(!this._dialogMaximized));
      }
      if (!this.resizeHandle) return;
      const onMove = (clientX, clientY) => {
        if (!this._resizeState) return;
        // Dialog is anchored bottom-right: dragging the top-left handle outward grows it.
        const dx = this._resizeState.startX - clientX;
        const dy = this._resizeState.startY - clientY;
        this._applyDialogSize(this._resizeState.startW + dx, this._resizeState.startH + dy, false);
      };
      const onUp = () => {
        if (!this._resizeState) return;
        this._resizeState = null;
        this._persistDialogSize();
        window.removeEventListener('pointermove', pointerMove);
        window.removeEventListener('pointerup', onUp);
        window.removeEventListener('pointercancel', onUp);
      };
      const pointerMove = (e) => onMove(e.clientX, e.clientY);
      this.resizeHandle.addEventListener('pointerdown', (e) => {
        if (this._dialogMaximized || window.innerWidth <= 480) return;
        e.preventDefault();
        const rect = this.dialog.getBoundingClientRect();
        this._resizeState = {
          startX: e.clientX,
          startY: e.clientY,
          startW: rect.width,
          startH: rect.height,
        };
        try { this.resizeHandle.setPointerCapture(e.pointerId); } catch (err) { /* noop */ }
        window.addEventListener('pointermove', pointerMove);
        window.addEventListener('pointerup', onUp);
        window.addEventListener('pointercancel', onUp);
      });
      window.addEventListener('resize', () => {
        if (window.innerWidth <= 480) {
          this._setMaximized(false, false);
          if (this.dialog) {
            this.dialog.style.width = '';
            this.dialog.style.height = '';
          }
          return;
        }
        if (!this._dialogMaximized && this.dialog) {
          const rect = this.dialog.getBoundingClientRect();
          this._applyDialogSize(rect.width, rect.height, false);
        }
        if (this.resizeHandle) this.resizeHandle.hidden = this._dialogMaximized || window.innerWidth <= 720;
      });
    }

    _ownerHeaders(extra) {
      const headers = Object.assign({ 'X-Owner-Id': this.ownerId }, extra || {});
      return headers;
    }

    _storageKey() {
      return 'alx_chat_history_' + (this.scope || 'default');
    }

    _loadStoredHistory() {
      // Refresh always starts a new empty session; history lives in sidebar / server / IndexedDB.
      return [];
    }

    _saveStoredHistory() {
      // Intentionally no localStorage restore-on-refresh for the active thread.
    }

    clearChatHistory() {
      this.startNewConversation({ focus: true });
    }

    _restoreStoredHistoryUI() {
      // no-op: refresh = empty welcome
    }

    _escapeHtml(s) {
      return String(s || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    }

    _renderMarkdown(text) {
      let src = this._escapeHtml(text);
      const blocks = [];
      src = src.replace(/```([\s\S]*?)```/g, (_, code) => {
        const i = blocks.length;
        blocks.push('<pre><code>' + code.trim() + '</code></pre>');
        return '\u0000MD' + i + '\u0000';
      });
      src = src.replace(/`([^`]+)`/g, '<code>$1</code>');
      src = src.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
      src = src.replace(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
      const lines = src.split('\n');
      let html = '';
      let inUl = false;
      let inOl = false;
      const closeLists = () => {
        if (inUl) { html += '</ul>'; inUl = false; }
        if (inOl) { html += '</ol>'; inOl = false; }
      };
      for (const line of lines) {
        if (line.indexOf('\u0000MD') === 0) {
          closeLists();
          const m = line.match(/\u0000MD(\d+)\u0000/);
          if (m) html += blocks[Number(m[1])] || '';
          continue;
        }
        if (/^[-*]\s+/.test(line)) {
          if (!inUl) { closeLists(); html += '<ul>'; inUl = true; }
          html += '<li>' + line.replace(/^[-*]\s+/, '') + '</li>';
          continue;
        }
        if (/^\d+\.\s+/.test(line)) {
          if (!inOl) { closeLists(); html += '<ol>'; inOl = true; }
          html += '<li>' + line.replace(/^\d+\.\s+/, '') + '</li>';
          continue;
        }
        closeLists();
        if (!line.trim()) continue;
        html += '<p>' + line + '</p>';
      }
      closeLists();
      return html || '<p></p>';
    }

    _renderWelcome() {
      this.messagesContainer.innerHTML = '';
      if (!this.welcomeWrap) {
        this.welcomeWrap = document.createElement('div');
        this.welcomeWrap.className = 'alx-welcome-wrap';
        this.welcomeWrap.id = 'alx-welcome-wrap';
      }
      if (!this.welcomeBubble) {
        this.welcomeBubble = document.createElement('div');
        this.welcomeBubble.className = 'alx-bubble alx-bubble-assistant';
        this.welcomeBubble.id = 'alx-welcome';
      }
      if (!this.suggestionsEl) {
        this.suggestionsEl = document.createElement('div');
        this.suggestionsEl.className = 'alx-suggestions';
        this.suggestionsEl.id = 'alx-suggestions';
      }
      this.welcomeBubble.textContent = this.t('welcome');
      this.suggestionsEl.innerHTML = '';
      const title = document.createElement('div');
      title.style.cssText = 'width:100%;font-size:12px;font-weight:700;color:var(--alx-text-muted)';
      title.textContent = this.t('suggestions_title');
      this.suggestionsEl.appendChild(title);
      ['suggest_1', 'suggest_2', 'suggest_3', 'suggest_4'].forEach((key) => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'alx-suggestion';
        btn.textContent = this.t(key);
        btn.addEventListener('click', () => {
          this.input.value = this.t(key);
          this.handleSubmit({ preventDefault() {} });
        });
        this.suggestionsEl.appendChild(btn);
      });
      this.welcomeWrap.innerHTML = '';
      this.welcomeWrap.appendChild(this.welcomeBubble);
      this.welcomeWrap.appendChild(this.suggestionsEl);
      this.messagesContainer.appendChild(this.welcomeWrap);
    }

    async startNewConversation(opts) {
      const options = opts || {};
      this.chatHistory = [];
      this.sessionId = 'anon-' + Math.random().toString(36).substring(2, 9);
      this.conversationId = null;
      this._lastUserMessage = null;
      this._renderWelcome();
      if (navigator.onLine) {
        try {
          const res = await fetch(this.apiUrl + '/conversations', {
            method: 'POST',
            headers: this._ownerHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({
              course_id: this.scope || 'course:va-1',
              language: this.languageForApi(),
              title: 'New chat',
            }),
          });
          if (res.ok) {
            const conv = await res.json();
            this.conversationId = conv.id;
            if (this.offlineRuntime && this.offlineRuntime.upsertConversation) {
              await this.offlineRuntime.upsertConversation(Object.assign({}, conv, { owner_id: this.ownerId }));
            }
          }
        } catch (e) { /* offline create below */ }
      }
      if (!this.conversationId && this.offlineRuntime && this.offlineRuntime.upsertConversation) {
        const local = await this.offlineRuntime.upsertConversation({
          owner_id: this.ownerId,
          course_id: this.scope || 'course:va-1',
          language: this.languageForApi(),
          title: 'New chat',
        });
        this.conversationId = local.id;
      }
      await this.refreshConversationList();
      if (options.focus && this.input) this.input.focus();
    }

    async refreshConversationList(q) {
      if (!this.convList) return;
      let conversations = [];
      let groups = null;
      const query = (q != null ? q : (this.searchChats && this.searchChats.value) || '').trim();
      if (navigator.onLine) {
        try {
          const url = this.apiUrl + '/conversations' + (query ? ('?q=' + encodeURIComponent(query)) : '');
          const res = await fetch(url, { headers: this._ownerHeaders() });
          if (res.ok) {
            const data = await res.json();
            conversations = data.conversations || [];
            groups = data.groups || null;
          }
        } catch (e) { /* fall through */ }
      }
      if (!conversations.length && this.offlineRuntime && this.offlineRuntime.listLocalConversations) {
        conversations = await this.offlineRuntime.listLocalConversations(this.ownerId, query);
      }
      this._conversations = conversations;
      this.convList.innerHTML = '';
      const order = [
        ['today', this.t('today')],
        ['yesterday', this.t('yesterday')],
        ['previous_7_days', this.t('previous_7_days')],
        ['older', this.t('older')],
      ];
      const renderItem = (conv) => {
        const row = document.createElement('div');
        row.className = 'alx-conv-item' + (conv.id === this.conversationId ? ' active' : '');
        row.setAttribute('role', 'listitem');
        const openBtn = document.createElement('button');
        openBtn.type = 'button';
        openBtn.className = 'alx-conv-open';
        openBtn.textContent = conv.title || this.t('new_chat');
        openBtn.title = conv.title || this.t('new_chat');
        openBtn.addEventListener('click', () => this.openConversation(conv.id));
        const actions = document.createElement('div');
        actions.className = 'alx-conv-actions';
        const renameBtn = document.createElement('button');
        renameBtn.type = 'button';
        renameBtn.textContent = '✎';
        renameBtn.title = this.t('rename_chat');
        renameBtn.setAttribute('aria-label', this.t('rename_chat'));
        renameBtn.addEventListener('click', () => this.renameConversation(conv.id, conv.title));
        const delBtn = document.createElement('button');
        delBtn.type = 'button';
        delBtn.textContent = '✕';
        delBtn.title = this.t('delete_chat');
        delBtn.setAttribute('aria-label', this.t('delete_chat'));
        delBtn.addEventListener('click', () => this.deleteConversation(conv.id));
        actions.appendChild(renameBtn);
        actions.appendChild(delBtn);
        row.appendChild(openBtn);
        row.appendChild(actions);
        this.convList.appendChild(row);
      };
      if (groups) {
        let any = false;
        order.forEach(([key, label]) => {
          const items = groups[key] || [];
          if (!items.length) return;
          any = true;
          const lab = document.createElement('div');
          lab.className = 'alx-conv-group-label';
          lab.textContent = label;
          this.convList.appendChild(lab);
          items.forEach(renderItem);
        });
        if (!any) {
          const empty = document.createElement('div');
          empty.className = 'alx-conv-group-label';
          empty.textContent = this.t('empty_history');
          this.convList.appendChild(empty);
        }
      } else if (conversations.length) {
        conversations.forEach(renderItem);
      } else {
        const empty = document.createElement('div');
        empty.className = 'alx-conv-group-label';
        empty.textContent = this.t('empty_history');
        this.convList.appendChild(empty);
      }
    }

    async openConversation(conversationId) {
      let detail = null;
      if (navigator.onLine) {
        try {
          const res = await fetch(this.apiUrl + '/conversations/' + encodeURIComponent(conversationId), {
            headers: this._ownerHeaders(),
          });
          if (res.ok) detail = await res.json();
        } catch (e) { /* offline */ }
      }
      if (!detail && this.offlineRuntime) {
        const conv = await this.offlineRuntime.getLocalConversation(conversationId);
        const messages = await this.offlineRuntime.listLocalMessages(conversationId);
        if (conv) detail = Object.assign({}, conv, { messages: messages || [] });
      }
      if (!detail) return;
      this.conversationId = detail.id;
      this.chatHistory = [];
      this.messagesContainer.innerHTML = '';
      const msgs = detail.messages || [];
      if (!msgs.length) {
        this._renderWelcome();
      } else {
        for (const m of msgs) {
          if (m.role === 'user') {
            this.appendMessage(m.content, 'user', m.language || this.uiLangCode());
            this.chatHistory.push({ role: 'user', content: m.content, lang: m.language });
          } else if (m.role === 'assistant') {
            const bubble = this.appendMessage(m.content, 'assistant', m.language || this.uiLangCode(), m.citations || []);
            if (bubble && (m.source_type || m.answer_source)) {
              this.appendAnswerBadge(bubble, m.source_type || this.mapAnswerSource(m));
            }
            this.chatHistory.push({
              role: 'assistant', content: m.content, lang: m.language, citations: m.citations || [],
            });
          }
        }
      }
      this.setSidebarOpen(window.matchMedia('(max-width: 720px)').matches ? false : this._sidebarOpen);
      await this.refreshConversationList();
    }

    async renameConversation(conversationId, currentTitle) {
      const next = window.prompt(this.t('rename_chat'), currentTitle || '');
      if (next == null) return;
      const title = String(next).trim();
      if (!title) return;
      if (navigator.onLine) {
        try {
          await fetch(this.apiUrl + '/conversations/' + encodeURIComponent(conversationId), {
            method: 'PATCH',
            headers: this._ownerHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({ title }),
          });
        } catch (e) { /* ignore */ }
      }
      if (this.offlineRuntime && this.offlineRuntime.getLocalConversation) {
        const local = await this.offlineRuntime.getLocalConversation(conversationId);
        if (local) {
          local.title = title;
          local.updated_at = new Date().toISOString();
          await this.offlineRuntime.upsertConversation(local);
        }
      }
      await this.refreshConversationList();
    }

    async deleteConversation(conversationId) {
      if (!window.confirm(this.t('delete_chat') + '?')) return;
      if (navigator.onLine) {
        try {
          await fetch(this.apiUrl + '/conversations/' + encodeURIComponent(conversationId), {
            method: 'DELETE',
            headers: this._ownerHeaders(),
          });
        } catch (e) { /* ignore */ }
      }
      if (this.offlineRuntime && this.offlineRuntime.deleteLocalConversation) {
        await this.offlineRuntime.deleteLocalConversation(conversationId);
      }
      if (this.conversationId === conversationId) {
        await this.startNewConversation({ focus: false });
      } else {
        await this.refreshConversationList();
      }
    }

    async persistTurn(userMessage, data) {
      if (!this.conversationId) {
        await this.startNewConversation({ focus: false });
      }
      if (!this.conversationId) return;
      const payload = {
        user_message: userMessage,
        assistant_message: (data && data.answer) || '',
        language: (data && data.language) || this.uiLangCode(),
        provider: (data && data.provider) || '',
        answer_source: (data && data.answer_source) || '',
        source_type: (data && data.source_type) || '',
        cache_hit: !!(data && data.cache_hit),
        citations: (data && data.citations) || [],
        metadata: {
          connectivity: (data && data.connectivity) || (navigator.onLine ? 'online' : 'offline'),
          fallback_reason: (data && data.fallback_reason) || null,
        },
      };
      if (navigator.onLine) {
        try {
          const res = await fetch(
            this.apiUrl + '/conversations/' + encodeURIComponent(this.conversationId) + '/messages',
            {
              method: 'POST',
              headers: this._ownerHeaders({ 'Content-Type': 'application/json' }),
              body: JSON.stringify(payload),
            },
          );
          if (res.ok) {
            const body = await res.json();
            if (body.conversation) this.conversationId = body.conversation.id;
            if (this.offlineRuntime) {
              if (body.conversation) await this.offlineRuntime.upsertConversation(body.conversation);
              if (body.user) await this.offlineRuntime.saveLocalMessage(body.user);
              if (body.assistant) await this.offlineRuntime.saveLocalMessage(body.assistant);
            }
            await this.refreshConversationList();
            return;
          }
        } catch (e) { /* fall through to local */ }
      }
      if (this.offlineRuntime && this.offlineRuntime.saveLocalMessage) {
        await this.offlineRuntime.saveLocalMessage({
          conversation_id: this.conversationId,
          role: 'user',
          content: userMessage,
          language: payload.language,
        });
        if (payload.assistant_message) {
          await this.offlineRuntime.saveLocalMessage({
            conversation_id: this.conversationId,
            role: 'assistant',
            content: payload.assistant_message,
            language: payload.language,
            provider: payload.provider,
            answer_source: payload.answer_source,
            source_type: payload.source_type,
            cache_hit: payload.cache_hit,
            citations: payload.citations,
            metadata: payload.metadata,
          });
        }
        await this.refreshConversationList();
      }
    }

    setSidebarOpen(open) {
      this._sidebarOpen = !!open;
      if (!this.sidebar) return;
      const mobile = window.matchMedia('(max-width: 720px)').matches;
      if (mobile) {
        this.sidebar.hidden = !this._sidebarOpen;
        if (this.sidebarBackdrop) {
          this.sidebarBackdrop.hidden = !this._sidebarOpen;
          this.sidebarBackdrop.dataset.open = this._sidebarOpen ? 'true' : 'false';
        }
      } else {
        this.sidebar.hidden = !this._sidebarOpen;
        if (this.sidebarBackdrop) {
          this.sidebarBackdrop.hidden = true;
          this.sidebarBackdrop.dataset.open = 'false';
        }
      }
      if (this.sidebarBtn) {
        this.sidebarBtn.setAttribute('aria-expanded', this._sidebarOpen ? 'true' : 'false');
        this.sidebarBtn.setAttribute('aria-label', this._sidebarOpen ? this.t('close_sidebar') : this.t('open_sidebar'));
        this.sidebarBtn.title = this._sidebarOpen ? this.t('close_sidebar') : this.t('open_sidebar');
      }
    }

    toggleSidebar() {
      this.setSidebarOpen(!this._sidebarOpen);
    }

    effectiveLang() {
      if (this.currentLang && this.currentLang !== 'auto') return this.currentLang;
      if (this.sessionLang) return this.sessionLang;
      return 'am';
    }

    languageForApi() {
      if (this.currentLang && this.currentLang !== 'auto') return this.currentLang;
      if (this.sessionLang) return this.sessionLang;
      return 'auto';
    }

    t(key) {
      const uiLang = this.effectiveLang();
      const pack = this.uiPack[uiLang] || this.uiPack.en;
      return pack[key] || this.uiPack.en[key] || key;
    }

    uiLangCode() {
      return this.effectiveLang();
    }

    rememberLanguage(code) {
      if (code && code !== 'auto' && this.langMeta[code]) {
        this.sessionLang = code;
      }
    }

    detectScope() {
      if (this.getAttribute('data-scope')) return this.getAttribute('data-scope');
      if (this.getAttribute('data-source')) return this.getAttribute('data-source');
      if (this.getAttribute('data-course-id')) return this.getAttribute('data-course-id');
      const metaCourse = document.querySelector('meta[name="course-id"], meta[name="course-scope"], meta[name="course"]');
      if (metaCourse && metaCourse.content) return metaCourse.content.trim();
      if (document.body && document.body.dataset) {
        if (document.body.dataset.courseScope) return document.body.dataset.courseScope;
        if (document.body.dataset.courseId) return document.body.dataset.courseId;
        if (document.body.dataset.course) return document.body.dataset.course;
      }
      try {
        const params = new URLSearchParams(window.location.search);
        const urlCourse = params.get('course_id') || params.get('course') || params.get('scope');
        if (urlCourse) return urlCourse.trim();
      } catch (e) { /* sandboxed */ }
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
      this.buildLanguageOptions();
      this.applyLanguage();
      this.launcher.addEventListener('click', () => this.toggle());
      this.closeBtn.addEventListener('click', () => this.close());
      this._restoreDialogSize();
      this._initResizeControls();
      if (this.sidebarBtn) this.sidebarBtn.addEventListener('click', () => this.toggleSidebar());
      if (this.newChatBtn) this.newChatBtn.addEventListener('click', () => this.startNewConversation({ focus: true }));
      if (this.sidebarNewBtn) this.sidebarNewBtn.addEventListener('click', () => this.startNewConversation({ focus: true }));
      if (this.sidebarBackdrop) this.sidebarBackdrop.addEventListener('click', () => this.setSidebarOpen(false));
      if (this.searchChats) {
        let timer = null;
        this.searchChats.addEventListener('input', () => {
          clearTimeout(timer);
          timer = setTimeout(() => this.refreshConversationList(this.searchChats.value), 200);
        });
      }
      // Refresh = new empty chat (do not restore prior thread into the main pane).
      this.chatHistory = [];
      this._renderWelcome();
      this.setSidebarOpen(!window.matchMedia('(max-width: 720px)').matches);
      this.langSelect.addEventListener('change', () => {
        this.currentLang = this.langSelect.value;
        this._saveLang(this.currentLang);
        this.applyLanguage();
      });
      this.escalateBtn.addEventListener('click', () => this.requestHumanHelp());
      this.form.addEventListener('submit', (e) => this.handleSubmit(e));
      if (this.input) {
        this.input.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            this.handleSubmit(e);
          }
        });
        this.input.addEventListener('input', () => {
          this.input.style.height = 'auto';
          this.input.style.height = Math.min(140, this.input.scrollHeight) + 'px';
        });
      }
      this.initSpeechSynthesis();
      this.loadRemoteLanguagePack();
      // Wire mic immediately; probe STT in the background (do not block first click).
      this.initVoiceInput();
      this.probeServerStt();
      this.bootOffline().then(() => {
        this.startNewConversation({ focus: false });
        this.refreshConversationList();
      });
      this.dialog.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') this.close();
      });
      window.addEventListener('resize', () => this.setSidebarOpen(this._sidebarOpen));
    }

    async bootOffline() {
      this.offlineRuntime = await ensureOfflineRuntime();
      this.registerServiceWorker();
      this.updateConnectionStatus();
      window.addEventListener('online', () => this.onConnectivityChange(true));
      window.addEventListener('offline', () => this.onConnectivityChange(false));
      if (this.packBtn) this.packBtn.addEventListener('click', () => this.downloadCoursePack());
      if (this.pendingSendBtn) this.pendingSendBtn.addEventListener('click', () => this.syncQueuedPending());
      if (this.pendingDiscardBtn) this.pendingDiscardBtn.addEventListener('click', () => this.discardQueuedPending());
      await this.refreshPackButton();
      await this.refreshPendingBadge();
      if (navigator.onLine) {
        this.maybeAutoDownloadPack();
        this.promptSyncIfNeeded();
        this.promptPackRefreshIfNeeded();
      }
    }

    registerServiceWorker() {
      if (!('serviceWorker' in navigator)) return;
      const base = (document.currentScript && document.currentScript.src) || '/widget/assistant.js';
      const swUrl = base.replace(/assistant\.js(\?.*)?$/, 'sw.js$1');
      navigator.serviceWorker.register(swUrl, { scope: base.replace(/assistant\.js(\?.*)?$/, '') }).catch(() => {});
    }

    updateConnectionStatus(state) {
      const online = state != null ? state : (typeof navigator === 'undefined' ? true : navigator.onLine);
      this.connectionState = online ? (this.connectionState === 'syncing' ? 'syncing' : 'online') : 'offline';
      if (!this.connStatus) return;
      this.connStatus.classList.remove('online', 'offline', 'syncing');
      this.connStatus.classList.add(this.connectionState === 'syncing' ? 'syncing' : (online ? 'online' : 'offline'));
      if (this.connLabel) {
        this.connLabel.textContent = this.connectionState === 'syncing' ? this.t('status_syncing')
          : (online ? this.t('connectivity_ai_online') : this.t('connectivity_ai_offline'));
      }
      // Cloud voice / regenerate require network — never pretend they work offline.
      if (this.voiceBtn) {
        this.voiceBtn.disabled = !online;
        this.voiceBtn.title = online ? this.t('voice_aria') : this.t('voice_needs_network');
      }
    }

    async onConnectivityChange(isOnline) {
      this.updateConnectionStatus(isOnline);
      await this.refreshPendingBadge();
      if (isOnline) {
        await this.refreshPackButton();
        this.promptSyncIfNeeded();
        this.promptPackRefreshIfNeeded();
      }
    }

    async refreshPendingBadge() {
      if (!this.offlineRuntime || !this.pendingBadge) return;
      const queued = await this.offlineRuntime.listPending('queued');
      const n = queued.length;
      if (!n) {
        this.pendingBadge.hidden = true;
        if (this.pendingSendBtn) this.pendingSendBtn.hidden = true;
        if (this.pendingDiscardBtn) this.pendingDiscardBtn.hidden = true;
        return;
      }
      this.pendingBadge.hidden = false;
      this.pendingBadge.textContent = this.t('pending_badge').replace('{n}', String(n));
      const showActions = !!navigator.onLine;
      if (this.pendingSendBtn) {
        this.pendingSendBtn.hidden = !showActions;
        this.pendingSendBtn.textContent = this.t('pending_send');
      }
      if (this.pendingDiscardBtn) {
        this.pendingDiscardBtn.hidden = !showActions;
        this.pendingDiscardBtn.textContent = this.t('pending_discard');
      }
    }

    async syncQueuedPending({ skipConfirm } = {}) {
      if (!this.offlineRuntime || !navigator.onLine) return;
      const queued = await this.offlineRuntime.listPending('queued');
      if (!queued.length) return;
      if (!skipConfirm) {
        const ok = window.confirm(this.t('sync_prompt').replace('{n}', String(queued.length)));
        if (!ok) {
          this.appendMessage(this.t('sync_skip'), 'assistant', this.uiLangCode());
          return;
        }
      }
      this.connectionState = 'syncing';
      this.updateConnectionStatus(true);
      const result = await this.offlineRuntime.syncPending(this.apiUrl, { consent: true });
      this.connectionState = 'online';
      this.updateConnectionStatus(true);
      this.appendMessage(this.t('sync_done').replace('{n}', String(result.synced || 0)), 'assistant', this.uiLangCode());
      await this.refreshPendingBadge();
    }

    async discardQueuedPending() {
      if (!this.offlineRuntime) return;
      const result = await this.offlineRuntime.discardPending('queued');
      this.appendMessage(this.t('sync_skip') + ` (${result.discarded || 0})`, 'assistant', this.uiLangCode());
      await this.refreshPendingBadge();
    }

    async promptPackRefreshIfNeeded() {
      if (!this.offlineRuntime || !navigator.onLine || this._packPrompted) return;
      const stale = await this.offlineRuntime.isPackStale(this.apiUrl, this.scope);
      if (!stale.stale || stale.reason === 'missing') return;
      this._packPrompted = true;
      const remote = (stale.remote && stale.remote.kb_version) || 'newer';
      const ok = window.confirm(this.t('pack_refresh_prompt').replace('{remote}', remote));
      if (ok) await this.downloadCoursePack();
    }

    async refreshPackButton() {
      if (!this.packBtn || !this.offlineRuntime) return;
      const record = await this.offlineRuntime.getPackRecord(this.scope);
      if (!record) {
        this.packBtn.textContent = this.t('download_pack');
        this.packBtn.disabled = !navigator.onLine;
        return;
      }
      if (navigator.onLine) {
        const stale = await this.offlineRuntime.isPackStale(this.apiUrl, this.scope);
        if (stale.stale) {
          this.packBtn.textContent = this.t('pack_stale');
          this.packBtn.disabled = false;
          return;
        }
      }
      this.packBtn.textContent = this.t('pack_ready');
      this.packBtn.disabled = false;
    }

    async maybeAutoDownloadPack() {
      if (!this.offlineRuntime || !navigator.onLine) return;
      const existing = await this.offlineRuntime.getPackRecord(this.scope);
      if (existing) return;
      try {
        await this.downloadCoursePack({ quiet: true });
      } catch (e) { /* optional first-visit warm cache */ }
    }

    async downloadCoursePack({ quiet } = {}) {
      if (!this.offlineRuntime) {
        if (!quiet) this.appendMessage(this.t('pack_error'), 'assistant', this.uiLangCode());
        return;
      }
      if (!navigator.onLine) {
        if (!quiet) this.appendMessage(this.t('status_offline') + ': ' + this.t('offline_ai_note'), 'assistant', this.uiLangCode());
        return;
      }
      this.packBtn.textContent = this.t('downloading_pack');
      this.packBtn.disabled = true;
      try {
        const result = await this.offlineRuntime.downloadPack(this.apiUrl, this.scope);
        if (result.quota) {
          this.appendMessage(this.t('pack_quota'), 'assistant', this.uiLangCode());
        } else if (!quiet) {
          this.appendMessage(this.t('pack_ready') + ' · ' + this.t('offline_ai_note'), 'assistant', this.uiLangCode());
        }
        if (navigator.serviceWorker && navigator.serviceWorker.controller) {
          navigator.serviceWorker.controller.postMessage({ type: 'INVALIDATE_PACKS' });
        }
      } catch (err) {
        if (!quiet) this.appendMessage(this.t('pack_error'), 'assistant', this.uiLangCode());
      }
      await this.refreshPackButton();
    }

    async promptSyncIfNeeded() {
      if (!this.offlineRuntime || this._syncPrompted || !navigator.onLine) return;
      const queued = await this.offlineRuntime.listPending('queued');
      await this.refreshPendingBadge();
      if (!queued.length) return;
      this._syncPrompted = true;
      // Visible badge + buttons; confirm remains for consent before personal data leaves the device.
      const ok = window.confirm(this.t('sync_prompt').replace('{n}', String(queued.length)));
      if (!ok) {
        this.appendMessage(this.t('sync_skip'), 'assistant', this.uiLangCode());
        return;
      }
      await this.syncQueuedPending({ skipConfirm: true });
    }

    appendAnswerBadge(bubble, source) {
      if (!source || source === 'none') return;
      const badge = document.createElement('span');
      const kind = this._badgeKind(source);
      badge.className = 'alx-answer-badge ' + kind;
      badge.textContent = this._badgeLabel(source);
      bubble.appendChild(badge);
    }

    _badgeKind(source) {
      const map = {
        fallback: 'fallback',
        cache: 'cache',
        course_grounded: 'cloud',
        general_knowledge: 'general',
        mixed: 'mixed',
        local_course: 'local',
        faq: 'faq',
        local: 'local',
        cloud: 'cloud',
        social: 'social',
        careers: 'careers',
        none: 'social',
      };
      return map[source] || 'faq';
    }

    _badgeLabel(source) {
      const keys = {
        fallback: 'badge_fallback',
        cache: 'badge_cache',
        course_grounded: 'badge_course',
        general_knowledge: 'badge_general',
        mixed: 'badge_mixed',
        local_course: 'badge_local_course',
        faq: 'badge_faq',
        local: 'badge_local',
        cloud: 'badge_cloud',
        social: 'badge_social',
        careers: 'badge_careers',
      };
      const key = keys[source];
      return key ? (this.t(key) || source) : '';
    }


    async loadRemoteLanguagePack() {
      try {
        const res = await fetch(`${this.apiUrl}/languages`);
        if (!res.ok) return;
        const data = await res.json();
        (data.languages || []).forEach((lang) => {
          if (lang.ui) this.uiPack[lang.code] = Object.assign({}, this.uiPack[lang.code] || {}, lang.ui);
          this.langMeta[lang.code] = {
            name: lang.name,
            native: lang.native_name,
            script: lang.script,
            dir: lang.direction,
            speech: lang.speech_recognition,
            tts: lang.speech_synthesis,
          };
        });
        this.buildLanguageOptions();
        this.applyLanguage();
      } catch (e) {
        // Keep the embedded offline pack; text interaction still works.
      }
    }

    buildLanguageOptions() {
      const previous = this.currentLang;
      this.langSelect.innerHTML = '';
      const auto = document.createElement('option');
      auto.value = 'auto';
      auto.textContent = this.t('auto');
      this.langSelect.appendChild(auto);
      LANG_ORDER.forEach((code) => {
        const meta = this.langMeta[code];
        if (!meta) return;
        const opt = document.createElement('option');
        opt.value = code;
        opt.textContent = `${meta.native} (${code.toUpperCase()})`;
        opt.setAttribute('lang', code);
        opt.setAttribute('dir', meta.dir);
        this.langSelect.appendChild(opt);
      });
      this.langSelect.value = LANG_ORDER.includes(previous) || previous === 'auto' ? previous : 'auto';
      this.currentLang = this.langSelect.value;
    }

    applyLanguage() {
      const code = this.uiLangCode();
      const meta = this.langMeta[code] || this.langMeta.en;
      this.dialog.setAttribute('dir', meta.dir);
      this.dialog.setAttribute('lang', code);
      this.launcher.setAttribute('aria-label', this.t('launcher_aria'));
      this.shadowRoot.getElementById('alx-launcher-text').textContent = this.t('launcher');
      this.shadowRoot.getElementById('alx-header-label').textContent = this.t('header');
      this.shadowRoot.getElementById('alx-lang-label').textContent = this.t('language');
      this.langSelect.setAttribute('aria-label', this.t('language_aria'));
      this.closeBtn.setAttribute('aria-label', this.t('close_aria'));
      this.shadowRoot.getElementById('alx-simple-label').textContent = this.t('simple_mode');
      this.simpleModeCheck.setAttribute('aria-label', this.t('simple_mode'));
      this.escalateBtn.textContent = this.t('human_help');
      this.escalateBtn.setAttribute('aria-label', this.t('human_help_aria'));
      this.shadowRoot.getElementById('alx-input-label').textContent = this.t('input_label');
      this.input.placeholder = this.t('placeholder');
      this.sendBtn.textContent = this.t('send');
      this.sendBtn.setAttribute('aria-label', this.t('send_aria'));
      this.voiceBtn.setAttribute('aria-label', this.t('voice_aria'));
      this.welcomeBubble.textContent = this.t('welcome');
      this.welcomeBubble.setAttribute('lang', code);
      this.welcomeBubble.setAttribute('dir', meta.dir);
      if (this.suggestionsEl && this.messagesContainer.contains(this.welcomeWrap)) {
        this._renderWelcome();
      }
      if (this.sidebarNewBtn) this.sidebarNewBtn.textContent = this.t('new_chat');
      if (this.searchChats) this.searchChats.placeholder = this.t('search_chats');
      if (this.composerHint) this.composerHint.textContent = this.t('composer_hint');
      if (this.newChatBtn) {
        this.newChatBtn.title = this.t('new_chat');
        this.newChatBtn.setAttribute('aria-label', this.t('new_chat'));
      }
      this.setSidebarOpen(this._sidebarOpen);
      if (this.packBtn) this.refreshPackButton();
      this.updateConnectionStatus();
      this.refreshVoiceCapabilityHints();
      this._localizeRecControls();
    }

    toggle() {
      if (this.isOpen) this.close();
      else this.open();
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
      this.launcher.focus();
      if (this.voiceRecorder
          && (this.voiceRecorder.state === 'recording' || this.voiceRecorder.state === 'paused')) {
        this.discardRecording();
      }
      this._stopTts();
    }

    speechTag() {
      const code = this.effectiveLang();
      return (this.langMeta[code] || this.langMeta.am || this.langMeta.en).speech;
    }

    async probeServerStt() {
      try {
        const res = await fetch(`${this.apiUrl}/health`);
        if (!res.ok) {
          this._sttProbeDone = true;
          return;
        }
        const data = await res.json();
        this.serverStt = !!(data.speech && data.speech.server_stt);
        this.speechSupported = this.serverStt || this.browserSttSupported;
        if (this.voiceBtn && this.speechSupported) this.voiceBtn.hidden = false;
        this.refreshVoiceCapabilityHints();
      } catch (e) { /* offline — keep optimistic serverStt assumption until proven otherwise */ }
      this._sttProbeDone = true;
    }

    ttsTag() {
      const code = this.uiLangCode();
      return (this.langMeta[code] || this.langMeta.en).tts;
    }

    initSpeechSynthesis() {
      if (!this.ttsSupported) return;
      const refresh = () => {
        this.ttsVoices = window.speechSynthesis.getVoices() || [];
        this.refreshVoiceCapabilityHints();
      };
      refresh();
      if (typeof window.speechSynthesis.onvoiceschanged !== 'undefined') {
        window.speechSynthesis.onvoiceschanged = refresh;
      }
    }

    hasTtsVoice(bcp47) {
      if (!this.ttsSupported) return false;
      if (!this.ttsVoices.length) return true;
      const prefix = (bcp47 || 'en').split('-')[0].toLowerCase();
      return this.ttsVoices.some((v) => (v.lang || '').toLowerCase().startsWith(prefix));
    }

    refreshVoiceCapabilityHints() {
      const notes = [];
      if (!this.speechSupported) notes.push(this.t('voice_unsupported'));
      if (this.ttsSupported && !this.hasTtsVoice(this.ttsTag())) notes.push(this.t('speak_unsupported'));
      if (notes.length) {
        this.voiceNote.hidden = false;
        this.voiceNote.textContent = notes.join(' · ');
      } else if (this.voiceNote && !this.voiceNote.dataset.sticky) {
        this.voiceNote.hidden = true;
        this.voiceNote.textContent = '';
      }
    }

    _showVoiceError(message) {
      if (!this.voiceNote) return;
      this.voiceNote.hidden = false;
      this.voiceNote.dataset.sticky = '1';
      this.voiceNote.textContent = message;
    }

    _clearStickyVoiceNote() {
      if (!this.voiceNote) return;
      delete this.voiceNote.dataset.sticky;
      this.voiceNote.hidden = true;
      this.voiceNote.textContent = '';
    }

    initVoiceInput() {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      this.browserSttSupported = !!SpeechRecognition;
      // Optimistic: assume server STT until probe finishes so the mic is usable immediately.
      if (!this._sttProbeDone) this.serverStt = true;
      this.speechSupported = this.serverStt || this.browserSttSupported
        || !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);

      if (this.browserSttSupported) {
        try {
          this.recognition = new SpeechRecognition();
          this.recognition.continuous = false;
          this.recognition.interimResults = true;
          this.recognition.onresult = (event) => {
            let finalText = '';
            let interim = '';
            for (let i = event.resultIndex; i < event.results.length; i += 1) {
              const piece = event.results[i][0].transcript;
              if (event.results[i].isFinal) finalText += piece;
              else interim += piece;
            }
            this.input.value = (finalText || interim).trim();
          };
          this.recognition.onerror = () => this.stopBrowserListening();
          this.recognition.onend = () => this.stopBrowserListening();
        } catch (err) {
          this.browserSttSupported = false;
        }
      }

      ensureVoiceRecorder().then((VoiceRecorder) => {
        if (!VoiceRecorder) return;
        this.voiceRecorder = new VoiceRecorder({
          maxActiveMs: 60000,
          keepStream: true,
          onStateChange: (evt) => this._onRecorderState(evt),
          onLevel: (level) => {
            if (this.recLevel) this.recLevel.style.width = `${Math.round(level * 100)}%`;
          },
          onTick: ({ activeMs }) => {
            if (this.recTimer) this.recTimer.textContent = formatMmSs(activeMs);
          },
          onError: (err) => this._onRecorderError(err),
        });
      });

      if (this.voiceBtn) {
        this.voiceBtn.addEventListener('click', () => this.handleVoiceButton());
      }
      if (this.recPauseBtn) {
        this.recPauseBtn.addEventListener('click', () => this.togglePauseRecording());
      }
      if (this.recStopBtn) {
        this.recStopBtn.addEventListener('click', () => this.stopAndTranscribe());
      }
      if (this.recDiscardBtn) {
        this.recDiscardBtn.addEventListener('click', () => this.discardRecording());
      }
      if (this.reviewReplayBtn) {
        this.reviewReplayBtn.addEventListener('click', () => this.replayRecording());
      }
      if (this.reviewRetryBtn) {
        this.reviewRetryBtn.addEventListener('click', () => this.retryTranscription());
      }
      if (this.reviewDiscardBtn) {
        this.reviewDiscardBtn.addEventListener('click', () => this.discardRecording());
      }
      if (this.reviewSendBtn) {
        this.reviewSendBtn.addEventListener('click', () => this.sendReviewedTranscript());
      }
      this.refreshVoiceCapabilityHints();
      this._localizeRecControls();
    }

    _localizeRecControls() {
      if (this.recPauseBtn) {
        const paused = this.voiceRecorder && this.voiceRecorder.state === 'paused';
        this.recPauseBtn.textContent = this.t(paused ? 'rec_resume' : 'rec_pause');
      }
      if (this.recStopBtn) this.recStopBtn.textContent = this.t('rec_stop');
      if (this.recDiscardBtn) this.recDiscardBtn.textContent = this.t('rec_discard');
      if (this.reviewReplayBtn) this.reviewReplayBtn.textContent = this.t('rec_replay');
      if (this.reviewRetryBtn) this.reviewRetryBtn.textContent = this.t('rec_retry');
      if (this.reviewDiscardBtn) this.reviewDiscardBtn.textContent = this.t('rec_discard');
      if (this.reviewSendBtn) this.reviewSendBtn.textContent = this.t('send');
      if (this.reviewLabel) this.reviewLabel.textContent = this.t('rec_edit');
    }

    handleVoiceButton() {
      if (!navigator.onLine) {
        this._showVoiceError(this.t('voice_needs_network'));
        return;
      }
      const rec = this.voiceRecorder;
      if (rec && (rec.state === 'recording' || rec.state === 'paused'
          || rec.state === 'requesting_permission')) {
        this.stopAndTranscribe();
        return;
      }
      if (this._browserListening) {
        this.stopBrowserListening();
        return;
      }
      // Prefer server STT (optimistic until probe says otherwise).
      if (this.serverStt || !this._sttProbeDone) {
        this.startServerRecording();
      } else if (this.browserSttSupported) {
        this.startBrowserRecognition();
      } else {
        this._showVoiceError(this.t('voice_unsupported'));
      }
    }

    startBrowserRecognition() {
      if (!this.recognition) return;
      this.recognition.lang = this.speechTag();
      this._browserListening = true;
      if (this.voiceBtn) {
        this.voiceBtn.classList.add('listening');
        this.voiceBtn.setAttribute('aria-pressed', 'true');
        this.voiceBtn.setAttribute('aria-label', this.t('voice_stop_aria'));
      }
      this.input.placeholder = this.t('listening');
      try {
        this.recognition.start();
      } catch (err) {
        console.warn('Could not start recognition:', err);
        this.stopBrowserListening();
      }
    }

    stopBrowserListening() {
      this._browserListening = false;
      if (this.recognition) {
        try { this.recognition.stop(); } catch (e) { /* already stopped */ }
      }
      if (this.voiceBtn) {
        this.voiceBtn.classList.remove('listening');
        this.voiceBtn.setAttribute('aria-pressed', 'false');
        this.voiceBtn.setAttribute('aria-label', this.t('voice_aria'));
      }
      this.input.placeholder = this.t('placeholder');
    }

    async startServerRecording() {
      this._clearStickyVoiceNote();
      this.hideReviewPanel();
      if (!this.voiceRecorder) {
        const VoiceRecorder = await ensureVoiceRecorder();
        if (!VoiceRecorder) {
          if (this.browserSttSupported) {
            this.startBrowserRecognition();
            return;
          }
          this._showVoiceError(this.t('mic_unsupported'));
          return;
        }
        this.voiceRecorder = new VoiceRecorder({
          maxActiveMs: 60000,
          keepStream: true,
          onStateChange: (evt) => this._onRecorderState(evt),
          onLevel: (level) => {
            if (this.recLevel) this.recLevel.style.width = `${Math.round(level * 100)}%`;
          },
          onTick: ({ activeMs }) => {
            if (this.recTimer) this.recTimer.textContent = formatMmSs(activeMs);
          },
          onError: (err) => this._onRecorderError(err),
        });
      }
      this._voiceTimings = { micClickAt: performance.now() };
      this.showRecBar(true);
      if (this.voiceNote) {
        this.voiceNote.hidden = false;
        this.voiceNote.textContent = this.t('rec_permission');
      }
      try {
        const sessionId = await this.voiceRecorder.start();
        this._voiceTimings.micReadyAt = performance.now();
        this._voiceTimings.sessionId = sessionId;
        if (typeof console !== 'undefined' && console.debug) {
          console.debug('[alx-voice] mic_ready_ms',
            Math.round(this._voiceTimings.micReadyAt - this._voiceTimings.micClickAt));
        }
      } catch (err) {
        this.showRecBar(false);
        this._onRecorderError(err);
      }
    }

    _onRecorderState(evt) {
      const state = evt.to;
      if (this.voiceBtn) {
        const active = state === 'recording' || state === 'paused' || state === 'requesting_permission';
        this.voiceBtn.classList.toggle('listening', active);
        this.voiceBtn.setAttribute('aria-pressed', active ? 'true' : 'false');
        this.voiceBtn.setAttribute('aria-label', active ? this.t('voice_stop_aria') : this.t('voice_aria'));
      }
      if (state === 'recording') {
        this.showRecBar(true);
        if (this.recDot) this.recDot.classList.remove('paused');
        if (this.recPauseBtn) this.recPauseBtn.textContent = this.t('rec_pause');
        this.input.placeholder = this.t('listening');
        this._clearStickyVoiceNote();
      } else if (state === 'paused') {
        this.showRecBar(true);
        if (this.recDot) this.recDot.classList.add('paused');
        if (this.recPauseBtn) this.recPauseBtn.textContent = this.t('rec_resume');
        if (this.voiceNote) {
          this.voiceNote.hidden = false;
          this.voiceNote.textContent = this.t('rec_paused');
        }
      } else if (state === 'processing') {
        this.showRecBar(false);
        this.input.placeholder = this.t('transcribing');
      } else if (state === 'idle' || state === 'error') {
        this.showRecBar(false);
        if (state === 'idle') this.input.placeholder = this.t('placeholder');
      }
      this._localizeRecControls();
    }

    _onRecorderError(err) {
      const code = (err && err.code) || '';
      let msg = this.t('mic_unsupported');
      if (code === 'permission_denied') msg = this.t('mic_permission_denied');
      else if (code === 'no_device') msg = this.t('mic_no_device');
      else if (code === 'limit_reached') msg = this.t('recording_limit');
      else if (code === 'empty_audio') msg = this.t('stt_failed');
      this._showVoiceError(msg);
      this.showRecBar(false);
    }

    showRecBar(active) {
      if (this.recBar) this.recBar.setAttribute('data-active', active ? 'true' : 'false');
    }

    showReviewPanel(active) {
      if (this.reviewPanel) this.reviewPanel.setAttribute('data-active', active ? 'true' : 'false');
    }

    hideReviewPanel() {
      this.showReviewPanel(false);
      if (this._reviewObjectUrl) {
        try { URL.revokeObjectURL(this._reviewObjectUrl); } catch (e) { /* noop */ }
        this._reviewObjectUrl = null;
      }
      if (this.reviewAudio) {
        this.reviewAudio.pause();
        this.reviewAudio.removeAttribute('src');
        this.reviewAudio.hidden = true;
      }
    }

    togglePauseRecording() {
      const rec = this.voiceRecorder;
      if (!rec) return;
      try {
        if (rec.state === 'recording') rec.pause();
        else if (rec.state === 'paused') rec.resume();
      } catch (err) {
        this._onRecorderError(err);
      }
    }

    async stopAndTranscribe() {
      const rec = this.voiceRecorder;
      if (!rec || (rec.state !== 'recording' && rec.state !== 'paused')) return;
      try {
        const result = await rec.stop();
        await this.uploadForTranscription(result);
      } catch (err) {
        this._onRecorderError(err);
      }
    }

    discardRecording() {
      if (this.voiceRecorder) this.voiceRecorder.discard();
      this.hideReviewPanel();
      this.showRecBar(false);
      this._activeUploadSession = null;
      if (this.reviewText) this.reviewText.value = '';
      this.input.placeholder = this.t('placeholder');
      this._clearStickyVoiceNote();
      if (this.voiceBtn) {
        this.voiceBtn.classList.remove('listening');
        this.voiceBtn.setAttribute('aria-pressed', 'false');
        this.voiceBtn.setAttribute('aria-label', this.t('voice_aria'));
      }
    }

    replayRecording() {
      const blob = this.voiceRecorder && this.voiceRecorder.blob;
      if (!blob || !this.reviewAudio) return;
      if (!this._reviewObjectUrl) {
        this._reviewObjectUrl = URL.createObjectURL(blob);
        this.reviewAudio.src = this._reviewObjectUrl;
      }
      this.reviewAudio.hidden = false;
      this.reviewAudio.play().catch(() => {});
    }

    async retryTranscription() {
      const rec = this.voiceRecorder;
      if (!rec || !rec.blob) return;
      try {
        const payload = rec.beginRetry();
        await this.uploadForTranscription(payload);
      } catch (err) {
        this._onRecorderError(err);
      }
    }

    sendReviewedTranscript() {
      const text = (this.reviewText && this.reviewText.value || '').trim();
      if (!text) return;
      this.input.value = text;
      this.hideReviewPanel();
      if (this.voiceRecorder && this.voiceRecorder.state === 'transcribed') {
        // Keep blob until next start; mark idle for UI.
        try { this.voiceRecorder.discard(); } catch (e) { /* noop */ }
      }
      this.form.requestSubmit();
    }

    async uploadForTranscription(result) {
      const sessionId = result.sessionId;
      this._activeUploadSession = sessionId;
      const blob = result.blob;
      if (!blob || !blob.size) {
        this._showVoiceError(this.t('stt_failed'));
        return;
      }
      this._voiceTimings = this._voiceTimings || {};
      this._voiceTimings.blobReadyAt = performance.now();
      this._voiceTimings.uploadBytes = blob.size;

      this.input.placeholder = this.t('rec_uploading');
      if (this.voiceNote) {
        this.voiceNote.hidden = false;
        this.voiceNote.textContent = this.t('rec_uploading');
      }

      const form = new FormData();
      const ext = (result.mimeType || 'audio/webm').includes('mp4') ? 'mp4' : 'webm';
      form.append('audio', blob, `speech.${ext}`);
      form.append('language', this.languageForApi());

      const uploadStarted = performance.now();
      try {
        if (this.voiceNote) this.voiceNote.textContent = this.t('transcribing');
        this.input.placeholder = this.t('transcribing');
        const res = await fetch(`${this.apiUrl}/transcribe`, { method: 'POST', body: form });
        // Race guard: ignore stale uploads if a newer session started.
        if (this._activeUploadSession !== sessionId) return;
        const uploadEnded = performance.now();
        this._voiceTimings.uploadMs = Math.round(uploadEnded - uploadStarted);
        if (!res.ok) {
          let detail = this.t('stt_failed');
          try {
            const errBody = await res.json();
            if (errBody && errBody.detail) detail = String(errBody.detail);
          } catch (e) { /* noop */ }
          if (this.voiceRecorder) this.voiceRecorder.markError({ code: 'stt_failed', message: detail });
          this._showVoiceError(detail);
          this.showReviewPanel(!!blob);
          if (this.reviewText) this.reviewText.value = '';
          return;
        }
        const data = await res.json();
        if (this._activeUploadSession !== sessionId) return;
        this._voiceTimings.serverTimings = data.timings || null;
        this._voiceTimings.renderAt = performance.now();
        if (typeof console !== 'undefined' && console.debug) {
          console.debug('[alx-voice] timings', {
            mic_ready_ms: this._voiceTimings.micReadyAt
              ? Math.round(this._voiceTimings.micReadyAt - this._voiceTimings.micClickAt) : null,
            upload_ms: this._voiceTimings.uploadMs,
            upload_bytes: this._voiceTimings.uploadBytes,
            server: this._voiceTimings.serverTimings,
          });
        }
        // Never show a fake transcript — only real Whisper text.
        if (!data.text || !String(data.text).trim()) {
          if (this.voiceRecorder) this.voiceRecorder.markError({ code: 'empty', message: 'empty' });
          this._showVoiceError(this.t('stt_failed'));
          return;
        }
        if (this.voiceRecorder) this.voiceRecorder.markTranscribed();
        this.rememberLanguage(data.language_used || this.effectiveLang());
        if (this.reviewText) this.reviewText.value = String(data.text).trim();
        this.input.value = String(data.text).trim();
        this.showReviewPanel(true);
        if (this.voiceNote) {
          this.voiceNote.hidden = false;
          this.voiceNote.textContent = this.t('rec_ready');
        }
        this.input.placeholder = this.t('placeholder');
      } catch (err) {
        if (this._activeUploadSession !== sessionId) return;
        if (this.voiceRecorder) this.voiceRecorder.markError({ code: 'stt_failed', message: String(err) });
        this._showVoiceError(this.t('stt_failed'));
        this.showReviewPanel(!!blob);
      }
    }

    stopListening() {
      // Compatibility shim for older call sites.
      if (this._browserListening) this.stopBrowserListening();
      const rec = this.voiceRecorder;
      if (rec && (rec.state === 'recording' || rec.state === 'paused')) {
        this.stopAndTranscribe();
      }
    }

    appendMessage(text, sender, lang = 'auto', citations = []) {
      const bubble = document.createElement('div');
      bubble.className = `alx-bubble alx-bubble-${sender}`;
      const resolved = (lang && lang !== 'auto' && this.langMeta[lang]) ? lang : this.uiLangCode();
      const meta = this.langMeta[resolved] || this.langMeta.en;
      bubble.setAttribute('lang', resolved);
      bubble.setAttribute('dir', meta.dir);

      const textNode = document.createElement('div');
      if (sender === 'assistant') {
        textNode.className = 'alx-md';
        textNode.innerHTML = this._renderMarkdown(text);
      } else {
        textNode.textContent = text;
      }
      bubble.appendChild(textNode);

      if (citations && citations.length > 0) {
        const citeBox = document.createElement('div');
        citeBox.className = 'alx-citations';
        const citeTitle = document.createElement('div');
        citeTitle.className = 'alx-citations-title';
        citeTitle.textContent = this.t('citations');
        citeBox.appendChild(citeTitle);
        const list = document.createElement('ul');
        list.className = 'alx-citations-list';
        citations.forEach((c) => {
          const item = document.createElement('li');
          const link = document.createElement('a');
          link.className = 'alx-citation-link';
          let cleanUrl = c.url || '#';
          if (cleanUrl !== '#' && !cleanUrl.startsWith('/') && !cleanUrl.startsWith('http')) {
            cleanUrl = '/' + cleanUrl;
          }
          link.href = cleanUrl;
          link.textContent = `${c.title} — ${c.section}`;
          link.setAttribute('aria-label', `${this.t('citation_aria')}: ${c.section}`);
          link.addEventListener('click', (e) => {
            const hashMatch = cleanUrl.match(/#([a-zA-Z0-9_\-]+)/);
            if (!hashMatch) return;
            const anchorId = hashMatch[1];
            const targetEl = document.getElementById(anchorId) ||
              document.querySelector(`[name="${anchorId}"]`) ||
              document.querySelector(`[data-anchor="${anchorId}"]`);
            if (!targetEl) return;
            e.preventDefault();
            targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
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
          });
          item.appendChild(link);
          list.appendChild(item);
        });
        citeBox.appendChild(list);
        bubble.appendChild(citeBox);
      }

      if (sender === 'assistant') {
        this._attachMessageActions(bubble, text, resolved, { allowRegenerate: true });
      }

      this.messagesContainer.appendChild(bubble);
      this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
      return bubble;
    }

    _attachMessageActions(bubble, text, lang, opts) {
      const actions = document.createElement('div');
      actions.className = 'alx-msg-actions';
      const copyBtn = document.createElement('button');
      copyBtn.type = 'button';
      copyBtn.textContent = this.t('copy');
      copyBtn.addEventListener('click', async () => {
        try {
          await navigator.clipboard.writeText(text);
          copyBtn.textContent = this.t('copied');
          setTimeout(() => { copyBtn.textContent = this.t('copy'); }, 1500);
        } catch (e) {
          copyBtn.textContent = this.t('copy');
        }
      });
      actions.appendChild(copyBtn);

      if (opts && opts.allowRegenerate) {
        const regenBtn = document.createElement('button');
        regenBtn.type = 'button';
        regenBtn.textContent = this.t('regenerate');
        regenBtn.disabled = !navigator.onLine;
        regenBtn.title = navigator.onLine ? this.t('regenerate') : this.t('offline_ai_note');
        regenBtn.addEventListener('click', () => this.regenerateLastAnswer());
        actions.appendChild(regenBtn);
      }

      if (this.ttsSupported) {
        const speakBtn = document.createElement('button');
        speakBtn.type = 'button';
        speakBtn.className = 'alx-btn-speak';
        speakBtn.innerHTML = `<span class="alx-speak-label">${this.t('listen')}</span>`;
        const labelSpan = speakBtn.querySelector('.alx-speak-label');
        const bubbleId = `tts-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
        bubble.dataset.ttsId = bubbleId;
        const bcp = (this.langMeta[lang] || this.langMeta.en).tts;
        if (!this.hasTtsVoice(bcp)) speakBtn.title = this.t('speak_unsupported');
        speakBtn.addEventListener('click', () => this._toggleTts(bubbleId, text, bcp, speakBtn, labelSpan));
        actions.appendChild(speakBtn);
      }
      bubble.appendChild(actions);
    }

    _resetAllSpeakButtons() {
      this.shadowRoot.querySelectorAll('.alx-btn-speak').forEach((btn) => {
        btn.classList.remove('speaking', 'paused');
        const label = btn.querySelector('.alx-speak-label');
        if (label) label.textContent = this.t('listen');
        btn.setAttribute('aria-label', this.t('listen_aria'));
      });
    }

    _stopTts() {
      if (typeof window !== 'undefined' && window.speechSynthesis) {
        try { window.speechSynthesis.cancel(); } catch (e) { /* noop */ }
      }
      this._ttsController = { utterance: null, bubbleId: null, paused: false };
      this._resetAllSpeakButtons();
    }

    _toggleTts(bubbleId, text, bcp, speakBtn, labelSpan) {
      if (!this.ttsSupported) return;
      const syn = window.speechSynthesis;
      const ctrl = this._ttsController;

      // Same bubble currently speaking → pause or resume.
      if (ctrl.bubbleId === bubbleId && syn.speaking) {
        if (!ctrl.paused && typeof syn.pause === 'function') {
          syn.pause();
          ctrl.paused = true;
          speakBtn.classList.add('paused');
          labelSpan.textContent = this.t('resume_tts');
          return;
        }
        if (ctrl.paused && typeof syn.resume === 'function') {
          syn.resume();
          ctrl.paused = false;
          speakBtn.classList.remove('paused');
          labelSpan.textContent = this.t('pause_tts');
          return;
        }
        // Fallback browsers without pause: stop.
        this._stopTts();
        return;
      }

      // Different bubble or idle → start fresh (no overlapping audio).
      this._stopTts();
      if (!this.hasTtsVoice(bcp) && this.ttsVoices.length) {
        this._showVoiceError(this.t('speak_unsupported'));
        return;
      }
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = bcp;
      const voice = this.ttsVoices.find((v) => (v.lang || '').toLowerCase().startsWith(bcp.split('-')[0].toLowerCase()));
      if (voice) utterance.voice = voice;
      utterance.onend = () => {
        this._ttsController = { utterance: null, bubbleId: null, paused: false };
        this._resetAllSpeakButtons();
      };
      utterance.onerror = () => {
        this._ttsController = { utterance: null, bubbleId: null, paused: false };
        this._resetAllSpeakButtons();
        this._showVoiceError(this.t('speak_unsupported'));
      };
      this._ttsController = { utterance, bubbleId, paused: false };
      speakBtn.classList.add('speaking');
      labelSpan.textContent = this.t('pause_tts');
      speakBtn.setAttribute('aria-label', this.t('stop_aria'));
      syn.speak(utterance);
    }

    mapAnswerSource(data) {
      if (!data) return 'none';
      const status = data.status || '';
      if (status === 'not_found' || status === 'out_of_scope' || status === 'needs_clarification') {
        return 'none';
      }
      if (data.fallback_reason) return 'fallback';
      // Prefer Phase 7 source_type when the API provides it — but never trust
      // course_grounded / Gemini labels on empty or failed answers.
      const st = data.source_type;
      if (st && st !== 'none') return st;
      if (st === 'none') return 'none';
      if (data.cache_hit) return 'cache';
      const src = data.answer_source || data.source || '';
      if (!src || src === 'none') return 'none';
      if (src === 'cache') return 'cache';
      if (src === 'cloud_general') return 'general_knowledge';
      if (src === 'cloud') return 'course_grounded';
      if (src === 'faq') return 'faq';
      if (src === 'local') return 'local_course';
      if (src === 'social') return 'social';
      if (src === 'careers') return 'careers';
      return 'none';
    }

    _createTypingBubble(online) {
      const statusBubble = document.createElement('div');
      statusBubble.className = 'alx-bubble alx-bubble-status';
      statusBubble.setAttribute('aria-live', 'polite');
      statusBubble.setAttribute('aria-label', this.t('typing'));
      const typing = document.createElement('div');
      typing.className = 'alx-typing';
      typing.innerHTML = '<span></span><span></span><span></span>';
      const label = document.createElement('span');
      label.style.marginLeft = '8px';
      label.textContent = online ? this.t('loading') : this.t('loading_local');
      statusBubble.appendChild(typing);
      statusBubble.appendChild(label);
      return statusBubble;
    }

    _setSubmitting(active) {
      this.isSubmitting = !!active;
      if (this.sendBtn) this.sendBtn.disabled = !!active;
      if (this.input) this.input.disabled = !!active;
    }

    async handleSubmit(e) {
      e.preventDefault();
      if (this.isSubmitting) return;
      const query = this.input.value.trim();
      if (!query) return;
      await this._sendChat(query, { regenerate: false });
    }

    async regenerateLastAnswer() {
      if (!navigator.onLine) {
        this._showVoiceError(this.t('offline_ai_note'));
        return;
      }
      if (!this._lastUserMessage || this.isSubmitting) return;
      await this._sendChat(this._lastUserMessage, { regenerate: true, skipUserBubble: true });
    }

    async retryLastUserMessage() {
      if (!this._lastUserMessage || this.isSubmitting) return;
      await this._sendChat(this._lastUserMessage, { regenerate: false });
    }

    async _sendChat(query, options) {
      const opts = options || {};
      this._setSubmitting(true);
      this.scope = this.detectScope();
      this.updateScopeBadge();
      this._lastUserMessage = query;
      if (!opts.skipUserBubble) {
        if (this.welcomeWrap && this.messagesContainer.contains(this.welcomeWrap)) {
          this.welcomeWrap.remove();
        }
        this.appendMessage(query, 'user', this.uiLangCode());
      }
      this.input.value = '';
      if (this.input && this.input.style) this.input.style.height = 'auto';
      this.hideReviewPanel();

      const online = typeof navigator === 'undefined' ? true : navigator.onLine;
      const statusBubble = this._createTypingBubble(online);
      this.messagesContainer.appendChild(statusBubble);
      this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;

      const recentHistory = (this.chatHistory || []).slice(-6).map((t) => ({ role: t.role, content: t.content }));
      if (!opts.skipUserBubble) {
        this.chatHistory = this.chatHistory || [];
        this.chatHistory.push({ role: 'user', content: query, lang: this.uiLangCode() });
        this._saveStoredHistory();
      }

      const payload = {
        session: this.sessionId,
        message: query,
        language: this.languageForApi(),
        mode: this.simpleModeCheck.checked ? 'simple' : 'normal',
        scope: this.scope,
        history: recentHistory,
        regenerate: !!opts.regenerate,
      };

      try {
        if (online) {
          const res = await fetch(`${this.apiUrl}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          });
          statusBubble.remove();
          if (!res.ok) throw new Error('Server returned ' + res.status);
          const data = await res.json();
          this.rememberLanguage(data.language);
          data.source = this.mapAnswerSource(data);
          this.renderAssistantResponse(data);
          if (this.offlineRuntime) {
            await this.offlineRuntime.appendHistory({
              session: this.sessionId, scope: this.scope, role: 'assistant',
              message: data.answer, status: data.status, source: data.source === 'local' ? 'local' : 'cloud',
            });
            await this._cacheAnswerLocally(payload, data);
          }
        } else {
          await this.answerOffline(payload, statusBubble);
        }
      } catch (err) {
        statusBubble.remove();
        // Browser may still be "online" while the assistant backend is down — use the pack.
        const usedPack = await this._tryOfflineFallback(payload);
        if (!usedPack) {
          this._appendErrorBubble(this.t('offline_error'));
        }
      } finally {
        this._setSubmitting(false);
      }
    }

    async _cacheAnswerLocally(payload, data) {
      if (!this.offlineRuntime || !this.offlineRuntime.saveCachedAnswer) return;
      if (!data || data.status !== 'answered' || !data.answer) return;
      try {
        const pack = await this.offlineRuntime.getPack(payload.scope || this.scope);
        await this.offlineRuntime.saveCachedAnswer({
          scope: payload.scope || this.scope,
          language: data.language || payload.language || 'en',
          question: payload.message,
          simple: payload.mode === 'simple',
          kb_version: pack ? pack.kb_version : '',
          provider: data.provider,
          answer_source: data.answer_source || data.source,
          status: data.status,
          answer: data.answer,
          citations: data.citations || [],
          confidence: data.confidence,
        });
      } catch (e) { /* optional local cache */ }
    }

    async _tryOfflineFallback(payload) {
      if (!this.offlineRuntime) return false;
      const scope = payload.scope || this.scope;
      const pack = await this.offlineRuntime.getPack(scope);
      if (!pack) return false;
      if (typeof navigator !== 'undefined' && navigator.onLine) {
        this.appendMessage(this.t('offline_using_pack'), 'assistant', this.uiLangCode());
      }
      await this.answerOffline(payload, null);
      return true;
    }

    _appendErrorBubble(message) {
      const bubble = document.createElement('div');
      bubble.className = 'alx-bubble alx-bubble-assistant alx-bubble-error';
      bubble.textContent = message;
      const actions = document.createElement('div');
      actions.className = 'alx-msg-actions';
      const retryBtn = document.createElement('button');
      retryBtn.type = 'button';
      retryBtn.textContent = this.t('retry');
      retryBtn.addEventListener('click', () => {
        bubble.remove();
        this.retryLastUserMessage();
      });
      actions.appendChild(retryBtn);
      bubble.appendChild(actions);
      this.messagesContainer.appendChild(bubble);
      this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    async answerOffline(payload, statusBubble) {
      if (statusBubble) statusBubble.remove();
      if (!this.offlineRuntime) {
        this.appendMessage(this.t('offline_no_pack'), 'assistant', this.uiLangCode());
        return;
      }
      const pack = await this.offlineRuntime.getPack(payload.scope || this.scope);
      if (!pack) {
        this.appendMessage(this.t('offline_no_pack'), 'assistant', this.uiLangCode());
        return;
      }
      const language = this.currentLang === 'auto' ? this.uiLangCode() : this.currentLang;
      let data = null;
      if (this.offlineRuntime.getCachedAnswer) {
        data = await this.offlineRuntime.getCachedAnswer({
          scope: payload.scope || this.scope,
          language,
          question: payload.message,
          simple: payload.mode === 'simple',
          kb_version: pack.kb_version,
        });
      }
      if (!data) {
        data = this.offlineRuntime.answerLocally(pack, Object.assign({}, payload, { language }));
      }
      data.connectivity = 'offline';
      data.course_id = payload.scope || this.scope || pack.scope;
      if (data.cache_hit) {
        data.answer_source = 'cache';
        data.source_type = 'cache';
      } else if (data.status === 'answered') {
        data.answer_source = data.answer_source || 'local';
        data.source_type = 'local_course';
      } else {
        data.source_type = data.source_type || 'none';
      }
      data.source = this.mapAnswerSource(data);
      this.renderAssistantResponse(data);
      await this.offlineRuntime.appendHistory({
        session: this.sessionId, scope: this.scope, role: 'assistant',
        message: data.answer, status: data.status, source: 'local',
      });
      if (data.status === 'answered') {
        await this._cacheAnswerLocally(payload, data);
      }
      if (data.status === 'not_found') {
        await this.offlineRuntime.recordUnanswered({
          session: this.sessionId, scope: this.scope, message: payload.message, language,
        });
        await this.offlineRuntime.enqueuePending('question', payload);
      }
    }

    renderAssistantResponse(data) {
      if (this.welcomeWrap && this.messagesContainer.contains(this.welcomeWrap)) {
        this.welcomeWrap.remove();
      }
      if (data && data.answer) {
        this.chatHistory = this.chatHistory || [];
        this.chatHistory.push({
          role: 'assistant',
          content: data.answer,
          lang: data.language,
          citations: data.citations || [],
        });
        this._saveStoredHistory();
      }
      const beforeCount = this.messagesContainer.children.length;
      this.appendMessage(data.answer, 'assistant', data.language, data.citations || []);
      const bubble = this.messagesContainer.children[this.messagesContainer.children.length - 1];
      if (bubble && beforeCount < this.messagesContainer.children.length) {
        const source = data.source || this.mapAnswerSource(data);
        this.appendAnswerBadge(bubble, source);
      }
      if (this._lastUserMessage) {
        this.persistTurn(this._lastUserMessage, data || {});
      }
    }

    async requestHumanHelp() {
      if (!window.confirm(this.t('escalate_confirm'))) return;
      const payload = { session: this.sessionId, language: this.uiLangCode(), reason: 'Need tutor assistance' };
      if (!navigator.onLine) {
        if (this.offlineRuntime) {
          const queued = await this.offlineRuntime.enqueuePending('escalation', payload);
          if (queued.quota) this.appendMessage(this.t('pack_quota'), 'assistant', this.uiLangCode());
          else this.appendMessage(this.t('sync_skip') + ' · ' + this.t('offline_ai_note'), 'assistant', this.uiLangCode());
        } else {
          this.appendMessage(this.t('escalate_fail'), 'assistant', this.uiLangCode());
        }
        return;
      }
      try {
        const res = await fetch(`${this.apiUrl}/escalate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error('Server returned ' + res.status);
        const ticket = await res.json();
        const message = this.t('escalate_ok')
          .replace('{ticket}', ticket.ticket_id)
          .replace('{url}', ticket.jitsi_room_url);
        this.appendMessage(message, 'assistant', this.uiLangCode());
        window.open(ticket.jitsi_room_url, '_blank', 'noopener,noreferrer');
      } catch (err) {
        if (this.offlineRuntime) {
          await this.offlineRuntime.enqueuePending('escalation', payload);
        }
        this.appendMessage(this.t('escalate_fail'), 'assistant', this.uiLangCode());
      }
    }
  }

  customElements.define('alx-assistant', AlxAssistant);

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
