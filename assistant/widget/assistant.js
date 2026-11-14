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
      listen: 'Listen', listen_aria: 'Listen - Read response aloud', stop: 'Stop', stop_aria: 'Stop - Stop reading aloud',
      speak_unsupported: 'Read-aloud is not available for this language on this device',
      loading: 'Searching course material...',
      offline_error: 'Unable to reach the assistant server. You can connect with a live human helper using the button above.',
      welcome: 'Hello! I am your course assistant. Ask me questions about this lesson. All answers are strictly grounded in course content.',
      citations: 'Course Citations:', citation_aria: 'Go to course source',
      escalate_confirm: 'Would you like to connect with a live tutor? A secure Jitsi meeting link will be created for you to share your screen with explicit consent.',
      escalate_ok: 'Human tutor request dispatched ({ticket})! When you are ready to share your screen, open the secure session: {url}',
      escalate_fail: 'Sorry, the help request could not be sent. Please try again.',
      input_label: 'Type your question', detected: 'Detected language',
      status_online: 'Online', status_offline: 'Offline', status_syncing: 'Synchronizing…',
      badge_local: 'Local answer', badge_cloud: 'Cloud answer',
      download_pack: 'Download for offline', downloading_pack: 'Downloading course pack…',
      pack_ready: 'Course pack ready offline', pack_error: 'Could not download the course pack',
      pack_quota: 'Not enough device storage for the course pack. Free space and try again.',
      pack_stale: 'Course update available — tap to refresh offline pack',
      sync_prompt: 'You have {n} queued offline request(s) that may include personal questions. Sync them to the server now?',
      sync_done: 'Synchronization complete ({n} sent)', sync_skip: 'Kept offline. Nothing was sent.',
      offline_no_pack: 'You are offline and this course is not downloaded yet. Open once online and tap Download for offline.',
      offline_ai_note: 'Offline mode uses downloaded course content only. Cloud AI is unavailable offline.',
      loading_local: 'Searching downloaded course material…',
    },
    am: {
      launcher: 'ረዳት ጠይቅ', launcher_aria: 'ረዳት ጠይቅ - የትምህርት ረዳት', header: 'የALX የትምህርት ረዳት',
      language: 'ቋንቋ', language_aria: 'የመልስ ቋንቋ ይምረጡ', auto: 'በራስ መለየት',
      simple_mode: 'ቀላል ሁነታ', human_help: 'የቀጥታ ረዳት', human_help_aria: 'የቀጥታ ረዳት - ከሰው መምህር ጋር ይገናኙ',
      close_aria: 'ረዳቱን ዝጋ', placeholder: 'ስለዚህ ትምህርት ጥያቄዎን ይጠይቁ...', listening: 'እያዳመጠ ነው... አሁን ይናገሩ',
      send: 'ላክ', send_aria: 'መልእክት ላክ', voice_aria: 'የድምጽ ግቤት - ጥያቄዎን ይናገሩ',
      voice_stop_aria: 'ማዳመጥ አቁም - ማይክሮፎን ንቁ ነው', voice_unsupported: 'የድምጽ ግቤት በዚህ አሳሽ አይገኝም',
      listen: 'አዳምጥ', listen_aria: 'አዳምጥ - መልሱን በድምጽ ያንብቡ', stop: 'አቁም', stop_aria: 'አቁም - ማንበብ አቁም',
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
        position: fixed; bottom: 84px; right: 24px; z-index: 999999; width: 400px;
        max-width: calc(100vw - 32px); height: 580px; max-height: calc(100vh - 110px);
        background: var(--alx-bg); border: 1px solid var(--alx-border); border-radius: var(--alx-radius);
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.18); display: flex; flex-direction: column; overflow: hidden;
      }
      .alx-dialog[hidden] { display: none !important; }
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
        border-radius: 6px; background: #ffffff; color: var(--alx-text); font-family: inherit;
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
      @media (prefers-reduced-motion: reduce) {
        .alx-launcher, .alx-dialog, .alx-btn-voice.listening { transition: none !important; animation: none !important; }
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
      @media (max-width: 420px) {
        .alx-dialog { width: calc(100vw - 16px); right: 8px; bottom: 72px; height: calc(100vh - 96px); }
        .alx-launcher { right: 12px; bottom: 12px; }
        .alx-status-bar { flex-wrap: wrap; }
      }
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
          <label class="alx-lang-label" for="alx-lang-select" id="alx-lang-label">Language</label>
          <select class="alx-lang-select" id="alx-lang-select" aria-label="Select response language"></select>
          <button type="button" class="alx-btn-icon" id="alx-clear-btn" title="Clear chat history" aria-label="Clear chat history">🗑️</button>
          <button type="button" class="alx-btn-icon" id="alx-close-btn" aria-label="Close Assistant">✕</button>
        </div>
      </div>


      <div class="alx-status-bar" id="alx-status-bar" role="status" aria-live="polite">
        <span class="alx-status-pill online" id="alx-conn-status"><span class="alx-status-dot" aria-hidden="true"></span><span id="alx-conn-label">Online</span></span>
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
        <div class="alx-bubble alx-bubble-assistant" id="alx-welcome" lang="en" dir="ltr"></div>
      </div>

      <div class="alx-input-area">
        <form class="alx-input-form" id="alx-form">
          <label for="alx-input" class="alx-lang-label" id="alx-input-label">Type your question</label>
          <input type="text" class="alx-input-field" id="alx-input" placeholder="Ask a question about this lesson..." autocomplete="off" required />
          <button type="button" class="alx-btn-voice" id="alx-voice-btn" aria-label="Voice input - Speak your question" aria-pressed="false" title="Voice input">
            <svg aria-hidden="true" viewBox="0 0 24 24">
              <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5-3c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
            </svg>
          </button>
          <button type="submit" class="alx-btn-send" id="alx-send-btn" aria-label="Send message">Send</button>
        </form>
        <div class="alx-voice-note" id="alx-voice-note" hidden></div>
      </div>
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
      this.sessionId = 'anon-' + Math.random().toString(36).substring(2, 9);
      this.ttsVoices = [];
      this.currentAudio = null;
      this.activeSpeakButtonReset = null;
      this.mediaRecorder = null;
      this.audioStream = null;
      this.audioChunks = [];
      this.hasMediaRecorder = typeof window !== 'undefined' && typeof navigator !== 'undefined' && !!navigator.mediaDevices && !!navigator.mediaDevices.getUserMedia && typeof MediaRecorder !== 'undefined';
      this.speechSupported = this.hasMediaRecorder || (typeof window !== 'undefined' && !!(window.SpeechRecognition || window.webkitSpeechRecognition));
      this.ttsSupported = typeof window !== 'undefined' && (('Audio' in window) || ('speechSynthesis' in window));

      this.launcher = this.shadowRoot.getElementById('alx-launcher');
      this.dialog = this.shadowRoot.getElementById('alx-dialog');
      this.closeBtn = this.shadowRoot.getElementById('alx-close-btn');
      this.clearBtn = this.shadowRoot.getElementById('alx-clear-btn');
      this.langSelect = this.shadowRoot.getElementById('alx-lang-select');
      this.simpleModeCheck = this.shadowRoot.getElementById('alx-simple-mode');
      this.escalateBtn = this.shadowRoot.getElementById('alx-escalate-btn');
      this.form = this.shadowRoot.getElementById('alx-form');
      this.input = this.shadowRoot.getElementById('alx-input');
      this.voiceBtn = this.shadowRoot.getElementById('alx-voice-btn');
      this.voiceNote = this.shadowRoot.getElementById('alx-voice-note');
      this.messagesContainer = this.shadowRoot.getElementById('alx-messages');
      this.welcomeBubble = this.shadowRoot.getElementById('alx-welcome');
      this.sendBtn = this.shadowRoot.getElementById('alx-send-btn');
      this.connStatus = this.shadowRoot.getElementById('alx-conn-status');
      this.connLabel = this.shadowRoot.getElementById('alx-conn-label');
      this.packBtn = this.shadowRoot.getElementById('alx-pack-btn');
      this.connectionState = 'online';
      this.offlineRuntime = null;
      this._syncPrompted = false;
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

    _storageKey() {
      return 'alx_chat_history_' + (this.scope || 'default');
    }

    _loadStoredHistory() {
      try {
        if (typeof window !== 'undefined' && window.localStorage) {
          const raw = window.localStorage.getItem(this._storageKey());
          if (raw) {
            const parsed = JSON.parse(raw);
            if (Array.isArray(parsed)) return parsed;
          }
        }
      } catch (e) {}
      return [];
    }

    _saveStoredHistory() {
      try {
        if (typeof window !== 'undefined' && window.localStorage) {
          window.localStorage.setItem(this._storageKey(), JSON.stringify((this.chatHistory || []).slice(-20)));
        }
      } catch (e) {}
    }

    clearChatHistory() {
      this.stopAllSpeech();
      if (this.isListening) this.stopListening();
      this.chatHistory = [];
      try {
        if (typeof window !== 'undefined' && window.localStorage) {
          window.localStorage.removeItem(this._storageKey());
        }
      } catch (e) {}
      this.messagesContainer.innerHTML = '';
      if (this.welcomeBubble) {
        this.welcomeBubble.textContent = this.t('welcome');
        this.messagesContainer.appendChild(this.welcomeBubble);
      }
    }

    _restoreStoredHistoryUI() {
      if (!Array.isArray(this.chatHistory) || this.chatHistory.length === 0) return;
      for (const turn of this.chatHistory) {
        if (turn.role === 'user') {
          this.appendMessage(turn.content, 'user', turn.lang || this.uiLangCode());
        } else if (turn.role === 'assistant') {
          this.appendMessage(turn.content, 'assistant', turn.lang || this.uiLangCode(), turn.citations || []);
        }
      }
    }

    t(key) {
      const uiLang = this.currentLang === 'auto' ? 'en' : this.currentLang;
      const pack = this.uiPack[uiLang] || this.uiPack.en;
      return pack[key] || this.uiPack.en[key] || key;
    }

    uiLangCode() {
      return this.currentLang === 'auto' ? 'en' : this.currentLang;
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
      if (this.clearBtn) this.clearBtn.addEventListener('click', () => this.clearChatHistory());
      this.chatHistory = this._loadStoredHistory();
      this._restoreStoredHistoryUI();
      this.langSelect.addEventListener('change', () => {
        this.currentLang = this.langSelect.value;
        this._saveLang(this.currentLang);
        this.applyLanguage();
      });
      this.escalateBtn.addEventListener('click', () => this.requestHumanHelp());
      this.form.addEventListener('submit', (e) => this.handleSubmit(e));
      this.initVoiceInput();
      this.initSpeechSynthesis();
      this.loadRemoteLanguagePack();
      this.bootOffline();
      this.dialog.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') this.close();
      });
    }

    async bootOffline() {
      this.offlineRuntime = await ensureOfflineRuntime();
      this.registerServiceWorker();
      this.updateConnectionStatus();
      window.addEventListener('online', () => this.onConnectivityChange(true));
      window.addEventListener('offline', () => this.onConnectivityChange(false));
      if (this.packBtn) this.packBtn.addEventListener('click', () => this.downloadCoursePack());
      await this.refreshPackButton();
      if (navigator.onLine) {
        this.maybeAutoDownloadPack();
        this.promptSyncIfNeeded();
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
          : (online ? this.t('status_online') : this.t('status_offline'));
      }
    }

    async onConnectivityChange(isOnline) {
      this.updateConnectionStatus(isOnline);
      if (isOnline) {
        await this.refreshPackButton();
        this.promptSyncIfNeeded();
      }
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
      if (!queued.length) return;
      this._syncPrompted = true;
      const ok = window.confirm(this.t('sync_prompt').replace('{n}', String(queued.length)));
      if (!ok) {
        this.appendMessage(this.t('sync_skip'), 'assistant', this.uiLangCode());
        return;
      }
      this.connectionState = 'syncing';
      this.updateConnectionStatus(true);
      const result = await this.offlineRuntime.syncPending(this.apiUrl, { consent: true });
      this.connectionState = 'online';
      this.updateConnectionStatus(true);
      this.appendMessage(this.t('sync_done').replace('{n}', String(result.synced || 0)), 'assistant', this.uiLangCode());
    }

    appendAnswerBadge(bubble, source) {
      const badge = document.createElement('span');
      badge.className = 'alx-answer-badge ' + (source === 'local' ? 'local' : 'cloud');
      badge.textContent = source === 'local' ? this.t('badge_local') : this.t('badge_cloud');
      bubble.appendChild(badge);
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
      if (this.packBtn) this.refreshPackButton();
      this.updateConnectionStatus();
      this.refreshVoiceCapabilityHints();
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
      this.stopAllSpeech();
      if (this.isListening) this.stopListening();
      this.isOpen = false;
      this.dialog.setAttribute('hidden', '');
      this.launcher.setAttribute('aria-expanded', 'false');
      this.launcher.focus();
    }

    speechTag() {
      const code = this.uiLangCode();
      return (this.langMeta[code] || this.langMeta.en).speech;
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
      const prefix = (bcp47 || 'en').split('-')[0].toLowerCase();
      // Ethiopian and regional languages supported natively by Addis AI backend voice service
      if (['am', 'ti', 'om', 'en', 'sid', 'wal', 'sw'].includes(prefix)) return true;
      if (!this.ttsVoices.length) return true; // unknown yet — allow attempt; error handler falls back
      return this.ttsVoices.some((v) => (v.lang || '').toLowerCase().startsWith(prefix));
    }

    refreshVoiceCapabilityHints() {
      const notes = [];
      if (!this.speechSupported) notes.push(this.t('voice_unsupported'));
      if (this.ttsSupported && !this.hasTtsVoice(this.ttsTag())) notes.push(this.t('speak_unsupported'));
      if (notes.length) {
        this.voiceNote.hidden = false;
        this.voiceNote.textContent = notes.join(' · ');
      } else {
        this.voiceNote.hidden = true;
        this.voiceNote.textContent = '';
      }
    }

    stopAllSpeech() {
      if (this.currentAudio) {
        try {
          this.currentAudio.pause();
          this.currentAudio.currentTime = 0;
        } catch (_) {}
        this.currentAudio = null;
      }
      if (typeof window !== 'undefined' && window.speechSynthesis && window.speechSynthesis.speaking) {
        window.speechSynthesis.cancel();
      }
      if (this.activeSpeakButtonReset) {
        try { this.activeSpeakButtonReset(); } catch (_) {}
        this.activeSpeakButtonReset = null;
      }
    }

    fallbackBrowserSpeech(text, bcp, setSpeaking) {
      if (typeof window === 'undefined' || !window.speechSynthesis) {
        setSpeaking(false);
        this.voiceNote.hidden = false;
        this.voiceNote.textContent = this.t('speak_unsupported');
        return;
      }
      try {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = bcp;
        const voice = this.ttsVoices.find((v) => (v.lang || '').toLowerCase().startsWith(bcp.split('-')[0].toLowerCase()));
        if (voice) utterance.voice = voice;
        utterance.onend = () => {
          setSpeaking(false);
          this.activeSpeakButtonReset = null;
        };
        utterance.onerror = () => {
          setSpeaking(false);
          this.activeSpeakButtonReset = null;
          this.voiceNote.hidden = false;
          this.voiceNote.textContent = this.t('speak_unsupported');
        };
        this.activeSpeakButtonReset = () => {
          setSpeaking(false);
          if (window.speechSynthesis.speaking) window.speechSynthesis.cancel();
        };
        window.speechSynthesis.speak(utterance);
      } catch (err) {
        setSpeaking(false);
        this.voiceNote.hidden = false;
        this.voiceNote.textContent = this.t('speak_unsupported');
      }
    }

    initVoiceInput() {
      const SpeechRecognition = typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition);
      this.hasMediaRecorder = typeof window !== 'undefined' && typeof navigator !== 'undefined' && !!navigator.mediaDevices && !!navigator.mediaDevices.getUserMedia && typeof MediaRecorder !== 'undefined';

      if (!SpeechRecognition && !this.hasMediaRecorder) {
        this.speechSupported = false;
        if (this.voiceBtn) this.voiceBtn.hidden = true;
        this.refreshVoiceCapabilityHints();
        return;
      }

      this.speechSupported = true;
      this.isListening = false;
      this.mediaRecorder = null;
      this.audioStream = null;
      this.audioChunks = [];

      if (SpeechRecognition) {
        try {
          this.recognition = new SpeechRecognition();
          this.recognition.continuous = false;
          this.recognition.interimResults = true;
          this.recognition.onstart = () => {
            this.isListening = true;
            this.voiceBtn.classList.add('listening');
            this.voiceBtn.setAttribute('aria-pressed', 'true');
            this.voiceBtn.setAttribute('aria-label', this.t('voice_stop_aria'));
            this.input.placeholder = this.t('listening');
          };
          this.recognition.onresult = (event) => {
            this.input.value = Array.from(event.results).map((res) => res[0].transcript).join('');
          };
          this.recognition.onerror = () => this.stopListening();
          this.recognition.onend = () => this.stopListening();
        } catch (e) {
          this.recognition = null;
        }
      }

      if (this.voiceBtn) {
        this.voiceBtn.addEventListener('click', async () => {
          if (this.isListening) {
            this.stopListening();
            return;
          }
          await this.startListening();
        });
      }
    }

    async startListening() {
      const lang = this.uiLangCode();

      if (this.hasMediaRecorder) {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          this.audioStream = stream;
          this.audioChunks = [];

          let mimeType = 'audio/webm';
          if (typeof MediaRecorder.isTypeSupported === 'function') {
            if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
              mimeType = 'audio/webm;codecs=opus';
            } else if (MediaRecorder.isTypeSupported('audio/ogg;codecs=opus')) {
              mimeType = 'audio/ogg;codecs=opus';
            } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
              mimeType = 'audio/mp4';
            }
          }

          const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
          this.mediaRecorder = recorder;

          recorder.ondataavailable = (e) => {
            if (e.data && e.data.size > 0) {
              this.audioChunks.push(e.data);
            }
          };

          recorder.onstart = () => {
            this.isListening = true;
            if (this.voiceBtn) {
              this.voiceBtn.classList.add('listening');
              this.voiceBtn.setAttribute('aria-pressed', 'true');
              this.voiceBtn.setAttribute('aria-label', this.t('voice_stop_aria'));
            }
            this.input.placeholder = this.t('listening');
          };

          recorder.onstop = async () => {
            if (this.audioStream) {
              this.audioStream.getTracks().forEach((t) => t.stop());
              this.audioStream = null;
            }

            const mime = recorder.mimeType || 'audio/webm';
            const audioBlob = new Blob(this.audioChunks, { type: mime });
            this.audioChunks = [];
            this.mediaRecorder = null;

            if (audioBlob.size > 0) {
              await this.transcribeAudioBlob(audioBlob, lang, mime);
            }
          };

          recorder.start();
          return;
        } catch (err) {
          console.warn('getUserMedia/MediaRecorder failed or permission denied, trying SpeechRecognition fallback:', err);
        }
      }

      if (this.recognition) {
        this.recognition.lang = this.speechTag();
        try {
          this.recognition.start();
        } catch (err) {
          console.warn('Could not start recognition:', err);
          this.stopListening();
          this.refreshVoiceCapabilityHints();
        }
      } else {
        this.stopListening();
        this.voiceNote.hidden = false;
        this.voiceNote.textContent = this.t('voice_unsupported');
      }
    }

    stopListening() {
      this.isListening = false;
      if (this.voiceBtn) {
        this.voiceBtn.classList.remove('listening');
        this.voiceBtn.setAttribute('aria-pressed', 'false');
        this.voiceBtn.setAttribute('aria-label', this.t('voice_aria'));
      }
      this.input.placeholder = this.t('placeholder');

      if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
        try {
          this.mediaRecorder.stop();
        } catch (_) {}
      }
      if (this.recognition) {
        try {
          this.recognition.stop();
        } catch (_) {}
      }
      this.input.focus();
    }

    async transcribeAudioBlob(audioBlob, lang, mime) {
      const origPlaceholder = this.input.placeholder;
      this.input.placeholder = 'Transcribing...';
      try {
        const transcribeUrl = `${this.apiUrl}/voice/transcribe?language=${encodeURIComponent(lang)}`;
        const res = await fetch(transcribeUrl, {
          method: 'POST',
          headers: {
            'Content-Type': mime || 'audio/webm',
          },
          body: audioBlob,
        });

        if (res.ok) {
          const data = await res.json();
          if (data && data.text) {
            const current = this.input.value.trim();
            this.input.value = current ? `${current} ${data.text}` : data.text;
            this.input.focus();
          }
        } else {
          console.warn('Voice transcription server response:', res.status);
        }
      } catch (err) {
        console.warn('Voice transcription network error:', err);
      } finally {
        this.input.placeholder = origPlaceholder;
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
      textNode.textContent = text;
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

      if (sender === 'assistant' && this.ttsSupported) {
        const speakBtn = document.createElement('button');
        speakBtn.type = 'button';
        speakBtn.className = 'alx-btn-speak';
        speakBtn.innerHTML = `
          <svg aria-hidden="true" viewBox="0 0 24 24" style="width: 14px; height: 14px; fill: currentColor;">
            <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
          </svg>
          <span class="alx-speak-label">${this.t('listen')}</span>
        `;
        const labelSpan = speakBtn.querySelector('.alx-speak-label');
        const setSpeaking = (speaking) => {
          speakBtn.classList.toggle('speaking', speaking);
          labelSpan.textContent = speaking ? this.t('stop') : this.t('listen');
          speakBtn.setAttribute('aria-label', speaking ? this.t('stop_aria') : this.t('listen_aria'));
        };
        setSpeaking(false);
        const bcp = (this.langMeta[resolved] || this.langMeta.en).tts;
        if (!this.hasTtsVoice(bcp)) {
          speakBtn.title = this.t('speak_unsupported');
        }
        speakBtn.addEventListener('click', async () => {
          if (speakBtn.classList.contains('speaking')) {
            this.stopAllSpeech();
            return;
          }

          this.stopAllSpeech();
          const langCode = (resolved || 'en').split('-')[0].toLowerCase();
          setSpeaking(true);
          this.activeSpeakButtonReset = () => setSpeaking(false);

          let serverPlayed = false;
          try {
            const speakUrl = `${this.apiUrl}/voice/speak?text=${encodeURIComponent(text.slice(0, 1000))}&language=${encodeURIComponent(langCode)}`;
            const res = await fetch(speakUrl);
            if (res.ok) {
              const blob = await res.blob();
              if (blob && blob.size > 0 && typeof Audio !== 'undefined') {
                const audioUrl = URL.createObjectURL(blob);
                const audio = new Audio(audioUrl);
                this.currentAudio = audio;
                audio.onended = () => {
                  URL.revokeObjectURL(audioUrl);
                  setSpeaking(false);
                  if (this.currentAudio === audio) this.currentAudio = null;
                  this.activeSpeakButtonReset = null;
                };
                audio.onerror = () => {
                  URL.revokeObjectURL(audioUrl);
                  this.currentAudio = null;
                  this.fallbackBrowserSpeech(text, bcp, setSpeaking);
                };
                await audio.play();
                serverPlayed = true;
              }
            }
          } catch (e) {
            // Server voice unavailable or network error
          }

          if (!serverPlayed) {
            this.fallbackBrowserSpeech(text, bcp, setSpeaking);
          }
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
      this.appendMessage(query, 'user', this.uiLangCode());
      this.input.value = '';

      const online = typeof navigator === 'undefined' ? true : navigator.onLine;
      const statusBubble = document.createElement('div');
      statusBubble.className = 'alx-bubble alx-bubble-status';
      statusBubble.textContent = online ? this.t('loading') : this.t('loading_local');
      this.messagesContainer.appendChild(statusBubble);
      this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;

      const recentHistory = (this.chatHistory || []).slice(-4).map(t => ({ role: t.role, content: t.content }));
      this.chatHistory = this.chatHistory || [];
      this.chatHistory.push({ role: 'user', content: query, lang: this.uiLangCode() });
      this._saveStoredHistory();

      const payload = {
        session: this.sessionId,
        message: query,
        language: this.currentLang,
        mode: this.simpleModeCheck.checked ? 'simple' : 'normal',
        scope: this.scope,
        history: recentHistory,
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
          data.source = data.source || 'cloud';
          this.renderAssistantResponse(data);
          if (this.offlineRuntime) {
            await this.offlineRuntime.appendHistory({
              session: this.sessionId, scope: this.scope, role: 'assistant',
              message: data.answer, status: data.status, source: 'cloud',
            });
          }
        } else {
          await this.answerOffline(payload, statusBubble);
        }
      } catch (err) {
        statusBubble.remove();
        if (!online || (this.offlineRuntime && !(typeof navigator !== 'undefined' && navigator.onLine))) {
          await this.answerOffline(payload, null);
        } else {
          this.appendMessage(this.t('offline_error'), 'assistant', this.uiLangCode());
        }
      }
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
      const data = this.offlineRuntime.answerLocally(pack, Object.assign({}, payload, { language }));
      data.source = 'local';
      this.renderAssistantResponse(data);
      await this.offlineRuntime.appendHistory({
        session: this.sessionId, scope: this.scope, role: 'assistant',
        message: data.answer, status: data.status, source: 'local',
      });
      if (data.status === 'not_found') {
        await this.offlineRuntime.recordUnanswered({
          session: this.sessionId, scope: this.scope, message: payload.message, language,
        });
        await this.offlineRuntime.enqueuePending('question', payload);
      }
    }

    renderAssistantResponse(data) {
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
        this.appendAnswerBadge(bubble, data.source === 'local' ? 'local' : 'cloud');
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
