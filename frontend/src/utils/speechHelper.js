// ── Text-to-Speech helper using the Web Speech API ──
// No external dependencies — runs natively in all modern browsers.

let currentUtterance = null;

/**
 * Strip markdown-style bold markers and other noise so the spoken
 * text sounds natural.
 */
function cleanTextForSpeech(text) {
  return text
    .replace(/\*\*(.*?)\*\*/g, '$1') // remove **bold** markers
    .replace(/__(.*?)__/g, '$1')     // remove __underline__ markers
    .replace(/[#>*`~\-]/g, '')       // remove misc markdown chars
    .replace(/\n{2,}/g, '. ')        // turn double newlines into pauses
    .replace(/\n/g, ' ')             // single newlines → space
    .trim();
}

const SpeechHelper = {
  /** Returns true when the browser supports the Web Speech API. */
  isSupported() {
    return 'speechSynthesis' in window;
  },

  /**
   * Speak the given text.
   * @param {string} text     Plain or lightly-marked-up text.
   * @param {object} options  Optional overrides: rate, pitch, volume, lang, voice, onEnd, onError.
   */
  speak(text, options = {}) {
    if (!this.isSupported()) {
      console.warn('Text-to-speech is not supported in this browser.');
      return;
    }

    // Cancel anything currently playing
    this.stop();

    const cleaned = cleanTextForSpeech(text);
    if (!cleaned) return;

    const utterance = new SpeechSynthesisUtterance(cleaned);
    utterance.rate   = options.rate   ?? 1;
    utterance.pitch  = options.pitch  ?? 1;
    utterance.volume = options.volume ?? 1;
    utterance.lang   = options.lang   || 'en-US';

    if (options.voice) {
      utterance.voice = options.voice;
    }

    utterance.onend   = () => { currentUtterance = null; options.onEnd?.();  };
    utterance.onerror = (e) => { currentUtterance = null; options.onError?.(e); };

    currentUtterance = utterance;
    window.speechSynthesis.speak(utterance);
  },

  /** Stop any ongoing speech. */
  stop() {
    if (this.isSupported()) {
      window.speechSynthesis.cancel();
    }
    currentUtterance = null;
  },

  /** Returns true when the synthesiser is currently speaking. */
  isSpeaking() {
    return this.isSupported() && window.speechSynthesis.speaking;
  },

  /** Return the list of available voices (async-safe). */
  getVoices() {
    if (!this.isSupported()) return [];
    return window.speechSynthesis.getVoices();
  },

  /**
   * Preload voices — call once on app startup so they're ready
   * when the user first triggers speech.
   */
  preloadVoices() {
    if (!this.isSupported()) return;
    // Some browsers load voices asynchronously; this forces it:
    window.speechSynthesis.getVoices();
    if (typeof window.speechSynthesis.onvoiceschanged !== 'undefined') {
      window.speechSynthesis.onvoiceschanged = () => {
        window.speechSynthesis.getVoices();
      };
    }
  },
};

export default SpeechHelper;
