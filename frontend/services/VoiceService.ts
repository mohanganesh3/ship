/**
 * VoiceService — Whisper-based voice transcription with full crash safety.
 *
 * whisper.rn does not fully implement the New Architecture TurboModule spec
 * (getConstants must return a Map). We guard this with dynamic require + try/catch
 * so a transcription failure NEVER crashes the chat screen.
 */
import { Platform } from 'react-native';
import { logger } from './Logger';
import { ModelProvisioner } from './ModelProvisioner';

let whisperContext: any = null;
let isInitializing = false;
let whisperUnavailable = false; // set true permanently if native module fails
let realtimeSession: { stop: () => Promise<void>; subscribe: (cb: (event: any) => void) => void } | null = null;
let realtimeLatestText = '';
let realtimeFinalText = '';
let realtimeLastError = '';
let realtimeLastCode: number | null = null;
const TAG = 'VOICE';

const HALLUCINATION_BLOCKLIST = [
  'gunshot', 'gun shot', 'thank you', 'thanks for watching', 'subscribe',
  'you', 'the', 'a', '...', '. . .', 'silence', 'music', '[music]',
  '[inaudible]', 'okay', 'uh', 'um', 'hmmm', 'mhm',
];

function tryGetInitWhisper(): ((opts: any) => Promise<any>) | null {
  try {
    // Dynamic require so if the native module throws on registration, it's caught here
    const mod = require('whisper.rn');
    const fn = mod?.initWhisper ?? mod?.default?.initWhisper;
    if (typeof fn !== 'function') {
      logger.warn(TAG, 'whisper.rn: initWhisper not found in module exports');
      return null;
    }
    return fn;
  } catch (e: any) {
    logger.warn(TAG, `whisper.rn native module unavailable: ${e?.message ?? e}`);
    return null;
  }
}

export const VoiceService = {
  TAG: 'VOICE-CORE',

  async getReadiness(): Promise<{ available: boolean; reason?: string }> {
    if (whisperUnavailable) {
      return { available: false, reason: 'Voice engine is unavailable on this build.' };
    }

    const initWhisper = tryGetInitWhisper();
    if (!initWhisper) {
      return { available: false, reason: 'Voice module failed to load.' };
    }

    try {
      const FileSystem = require('expo-file-system/legacy');
      const destPath = `${FileSystem.documentDirectory}whisper-tiny.bin`;
      const info = await FileSystem.getInfoAsync(destPath);
      if (!info.exists) {
        const seeded = await ModelProvisioner.ensureVoiceEngineReady();
        if (!seeded) {
          return { available: false, reason: 'Voice model is not downloaded yet.' };
        }
      }
    } catch {
      return { available: false, reason: 'Could not verify voice model state.' };
    }

    return { available: true };
  },

  async init(): Promise<void> {
    if (whisperContext) return;
    if (isInitializing) return;
    if (whisperUnavailable) return;

    isInitializing = true;
    try {
      const initWhisper = tryGetInitWhisper();
      if (!initWhisper) {
        whisperUnavailable = true;
        logger.warn(TAG, 'whisper.rn not functional on this build. Voice input disabled.');
        return;
      }

      logger.info(TAG, 'Initializing Whisper voice engine...');
      const FileSystem = require('expo-file-system/legacy');

      const destPath = `${FileSystem.documentDirectory}whisper-tiny.bin`;
      const info = await FileSystem.getInfoAsync(destPath);
      if (!info.exists) {
        const seeded = await ModelProvisioner.ensureVoiceEngineReady();
        if (!seeded) {
          logger.warn(TAG, 'Whisper model file not found. Voice input disabled until download completes.');
          return;
        }
      }

      const nativePath = Platform.OS === 'android'
        ? destPath.replace('file://', '')
        : destPath;

      whisperContext = await initWhisper({ filePath: nativePath });
      logger.info(TAG, 'Whisper context ready.');
    } catch (err: any) {
      logger.error(TAG, `Whisper init failed: ${err?.message ?? err}`);
      whisperUnavailable = true; // Don't retry on hard failure
    } finally {
      isInitializing = false;
    }
  },

  async transcribe(audioPath: string, recordingDurationMs: number): Promise<string> {
    if (recordingDurationMs < 700) return '';
    if (whisperUnavailable) {
      logger.warn(TAG, 'Transcription skipped: whisper.rn unavailable.');
      return '';
    }

    if (!whisperContext) await this.init();
    if (!whisperContext) {
      logger.warn(TAG, 'Transcription skipped: no whisper context.');
      return '';
    }

    try {
      const res = await (whisperContext as any).transcribe(audioPath, {
        language: 'en',
        beam_size: 1,
        no_context: true,
        suppress_blank: true,
        max_threads: 4,
        audio_ctx: 0,
      });

      const raw: string = (res.result ?? res.text ?? '').trim();
      return this.postProcessTranscript(raw);
    } catch (err: any) {
      logger.error(TAG, `Transcription error: ${err?.message ?? err}`);
      return '';
    }
  },

  async startRealtimeCapture(): Promise<boolean> {
    if (whisperUnavailable) {
      logger.warn(TAG, 'Realtime capture skipped: whisper.rn unavailable.');
      return false;
    }

    if (!whisperContext) await this.init();
    if (!whisperContext) {
      logger.warn(TAG, 'Realtime capture skipped: no whisper context.');
      return false;
    }

    if (realtimeSession) {
      try { await realtimeSession.stop(); } catch {}
      realtimeSession = null;
    }

    realtimeLatestText = '';
    realtimeFinalText = '';
    realtimeLastError = '';
    realtimeLastCode = null;

    try {
      logger.info(TAG, 'Starting realtime voice capture...');
      const session = await (whisperContext as any).transcribeRealtime({
        language: 'en',
        no_context: true,
        suppress_blank: true,
        realtimeAudioSec: 20,
        realtimeAudioMinSec: 1,
        useVad: false,
      });

      session.subscribe((event: any) => {
        const code = typeof event?.code === 'number' ? event.code : null;
        if (code !== null) realtimeLastCode = code;

        const error = (event?.error ?? '').trim();
        if (error) {
          realtimeLastError = error;
          logger.warn(TAG, `Realtime event error: ${error}`);
        }

        const segmentsText = Array.isArray(event?.data?.segments)
          ? event.data.segments.map((s: any) => (s?.text ?? '')).join('')
          : '';
        const text = ((event?.data?.result ?? '') || segmentsText).trim();
        if (text) {
          realtimeLatestText = text;
          if (event?.isCapturing === false) {
            realtimeFinalText = text;
          }
        }
      });

      realtimeSession = session;
      logger.info(TAG, 'Realtime voice capture started.');
      return true;
    } catch (err: any) {
      logger.error(TAG, `Realtime capture start error: ${err?.message ?? err}`);
      realtimeSession = null;
      return false;
    }
  },

  async stopRealtimeCapture(recordingDurationMs: number): Promise<string> {
    if (recordingDurationMs < 700) return '';
    if (!realtimeSession) return '';

    try {
      logger.info(TAG, `Stopping realtime voice capture (durationMs=${recordingDurationMs})...`);
      await realtimeSession.stop();
      const deadline = Date.now() + 2500;
      while (!realtimeFinalText && Date.now() < deadline) {
        await new Promise((resolve) => setTimeout(resolve, 100));
      }
    } catch (err: any) {
      logger.error(TAG, `Realtime capture stop error: ${err?.message ?? err}`);
    } finally {
      realtimeSession = null;
    }

    const raw = (realtimeFinalText || realtimeLatestText).trim();
    logger.info(
      TAG,
      `Realtime voice raw result length=${raw.length}, code=${String(realtimeLastCode)}, error=${realtimeLastError || 'none'}`,
    );
    realtimeLatestText = '';
    realtimeFinalText = '';
    realtimeLastError = '';
    realtimeLastCode = null;
    return this.postProcessTranscript(raw);
  },

  postProcessTranscript(raw: string): string {
    if (!raw) return '';

    const lower = raw.toLowerCase().replace(/[^a-z\s]/g, '').trim();
    const isHallucination = HALLUCINATION_BLOCKLIST.some(h => lower === h);

    if (isHallucination || raw.length < 2) {
      logger.warn(TAG, `Filtered hallucination: "${raw}"`);
      return '';
    }

    return raw;
  },

  async release(): Promise<void> {
    if (realtimeSession) {
      try { await realtimeSession.stop(); } catch (_) {}
      realtimeSession = null;
    }
    if (whisperContext) {
      try { await (whisperContext as any).release(); } catch (_) {}
      whisperContext = null;
    }
  },

  isAvailable(): boolean {
    return !whisperUnavailable;
  },
};
