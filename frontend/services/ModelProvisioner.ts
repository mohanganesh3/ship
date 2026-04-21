/**
 * ModelProvisioner v4 — Bulletproof download with size validation.
 *
 * KEY FIXES vs v3:
 * 1. EXPECTED_LLM_SIZE = exact byte count from HuggingFace x-linked-size header
 * 2. Download detects 200 vs 206: if server ignores Range and sends full file,
 *    we delete the corrupt/appended file and retry from 0.
 * 3. Done marker is ONLY written after verifying final file size >= EXPECTED_LLM_SIZE.
 * 4. Status 416 is treated as "file already present" only if size is correct.
 */
import * as FileSystem from 'expo-file-system/legacy';
import { Platform } from 'react-native';
import ReactNativeBlobUtil from 'react-native-blob-util';
import { MODEL_REPO_ID } from '../constants/model';
import {
    failDownloadSession,
    finishDownloadSession,
    startDownloadSession,
    updateDownloadProgress,
} from './BackgroundDownloadManager';

const MODEL_NAME   = 'model.gguf';
const WHISPER_NAME = 'whisper-tiny.bin';
const BASE = FileSystem.documentDirectory!;

const INTERNAL_MODEL_PATH   = `${BASE}${MODEL_NAME}`;
const INTERNAL_WHISPER_PATH = `${BASE}${WHISPER_NAME}`;

const LLM_URLS = [
  `https://huggingface.co/${MODEL_REPO_ID}/resolve/main/model.gguf?download=true`,
  `https://huggingface.co/${MODEL_REPO_ID}/resolve/main/model.gguf`,
  `https://hf-mirror.com/${MODEL_REPO_ID}/resolve/main/model.gguf?download=true`,
  `https://hf-mirror.com/${MODEL_REPO_ID}/resolve/main/model.gguf`,
];
const WHISPER_URLS = [
  `https://huggingface.co/${MODEL_REPO_ID}/resolve/main/whisper-tiny.bin?download=true`,
  `https://huggingface.co/${MODEL_REPO_ID}/resolve/main/whisper-tiny.bin`,
  `https://hf-mirror.com/${MODEL_REPO_ID}/resolve/main/whisper-tiny.bin?download=true`,
  `https://hf-mirror.com/${MODEL_REPO_ID}/resolve/main/whisper-tiny.bin`,
];

// Exact sizes from HuggingFace x-linked-size header (verified 2026-04-24)
const EXPECTED_LLM_BYTES    = 1_107_409_280; // 1.03 GB
const EXPECTED_WHISPER_BYTES =    77_691_713; // ~74 MB
const SIZE_SLACK_BYTES = 256;

const DONE_MARKER_PATH = `${BASE}.maritime_done`;

interface ArtifactState {
  llmSize: number;
  whisperSize: number;
  llmReady: boolean;
  whisperReady: boolean;
}

function isFullyProvisioned(state: ArtifactState): boolean {
  return state.llmReady && state.whisperReady;
}

export interface DetailedProgress {
  progress:    number;
  speed?:      string;
  bytesRead?:  number;
  totalBytes?: number;
  statusLabel?: string;
}

const fmtBytes = (b?: number) => {
  if (!b || isNaN(b))  return '0 B';
  if (b >= 1073741824) return `${(b / 1073741824).toFixed(2)} GB`;
  if (b >= 1048576)    return `${(b / 1048576).toFixed(1)} MB`;
  return `${(b / 1024).toFixed(0)} KB`;
};

const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

function isArtifactSizeValid(size: number, expectedBytes: number): boolean {
  return size > 0 && Math.abs(size - expectedBytes) <= SIZE_SLACK_BYTES;
}

async function getFileSize(uri: string): Promise<number> {
  try {
    const info = await FileSystem.getInfoAsync(uri);
    return info.exists ? ((info as any).size ?? 0) : 0;
  } catch {
    return 0;
  }
}

async function deleteUriIfExists(uri: string): Promise<void> {
  try {
    await FileSystem.deleteAsync(uri, { idempotent: true });
  } catch {}
}

async function getArtifactState(): Promise<ArtifactState> {
  const [llmSize, whisperSize] = await Promise.all([
    getFileSize(INTERNAL_MODEL_PATH),
    getFileSize(INTERNAL_WHISPER_PATH),
  ]);

  return {
    llmSize,
    whisperSize,
    llmReady: isArtifactSizeValid(llmSize, EXPECTED_LLM_BYTES),
    whisperReady: isArtifactSizeValid(whisperSize, EXPECTED_WHISPER_BYTES),
  };
}

async function writeDoneMarker(state: ArtifactState): Promise<void> {
  try {
    await FileSystem.writeAsStringAsync(DONE_MARKER_PATH, JSON.stringify({
      ts: Date.now(),
      v: 5,
      llmSize: state.llmSize,
      whisperSize: state.whisperSize,
      llmReady: state.llmReady,
      whisperReady: state.whisperReady,
    }));
    console.log('[ModelProvisioner] Done marker written ✓');
  } catch (e) {
    console.warn('[ModelProvisioner] Could not write done marker:', e);
  }
}

let _isProvisioning = false;

/**
 * Download a file with resume support. Returns true on success.
 *
 * Handles three server behaviours:
 *   206 Partial Content → resume appended correctly ✓
 *   200 OK (Range ignored) → delete corrupt file, return false (will retry from 0 next call)
 *   416 Range Not Satisfiable → file already at full size, verify and return true
 */
async function downloadResumable(opts: {
  url:         string;
  dest:        string;
  fileName:    string;
  expectedBytes: number;
  weightStart: number;
  weightTotal: number;
  onProgress:  (p: DetailedProgress) => void;
}): Promise<boolean> {
  const { url, dest, fileName, expectedBytes, weightStart, weightTotal, onProgress } = opts;

  const destPath = dest.replace('file://', '');

  // Check existing file size for resume
  let existingSize = await getFileSize(dest);

  if (isArtifactSizeValid(existingSize, expectedBytes)) {
    console.log(`[ModelProvisioner] ${fileName}: already complete at ${fmtBytes(existingSize)}`);
    onProgress({ progress: weightStart + weightTotal, statusLabel: `${fileName} ready` });
    return true;
  }
  if (existingSize > expectedBytes + SIZE_SLACK_BYTES) {
    console.warn(
      `[ModelProvisioner] ${fileName}: oversized local file ${fmtBytes(existingSize)}. Deleting corrupt copy.`,
    );
    await deleteUriIfExists(dest);
    existingSize = 0;
  }

  let lastBytes     = 0;
  let lastTime      = Date.now();
  let lastNotifTime = Date.now();

  try {
    const headers: Record<string, string> = {};
    if (existingSize > 0) {
      headers['Range'] = `bytes=${existingSize}-`;
      console.log(`[ModelProvisioner] Resuming ${fileName} from ${fmtBytes(existingSize)}`);
    } else {
      console.log(`[ModelProvisioner] Starting fresh download of ${fileName} (${fmtBytes(expectedBytes)} expected)`);
    }

    const host = url.includes('hf-mirror') ? 'hf-mirror.com' : 'huggingface.co';
    onProgress({ progress: weightStart, statusLabel: `Connecting to ${host}...` });

    const req = ReactNativeBlobUtil.config({
      path: existingSize > 0 ? `${destPath}?append=true` : destPath,
      overwrite: existingSize <= 0,
      appendExt: undefined,
    }).fetch('GET', url, headers);

    req.progress((receivedStr, totalStr) => {
      const receivedThisReq = parseInt(receivedStr, 10);
      const totalRemaining  = parseInt(totalStr, 10);
      const now = Date.now();

      const totalSize    = existingSize + (totalRemaining > 0 ? totalRemaining : 0);
      const currentPos   = existingSize + receivedThisReq;
      const fileProgress = totalSize > 0 ? currentPos / totalSize : 0;
      const globalProgress = weightStart + (fileProgress * weightTotal);

      if (now - lastNotifTime > 1500) {
        const bps   = ((receivedThisReq - lastBytes) / (now - lastTime)) * 1000;
        const speed = fmtBytes(bps) + '/s';

        onProgress({
          progress:    globalProgress,
          speed,
          bytesRead:   currentPos,
          totalBytes:  totalSize,
          statusLabel: `Syncing ${fileName}...`,
        });

        lastBytes     = receivedThisReq;
        lastTime      = now;
        lastNotifTime = now;

        updateDownloadProgress({ fileName, progress: globalProgress, speed,
          received: fmtBytes(currentPos), total: fmtBytes(totalSize) });
      }
    });

    const res    = await req;
    const status = res.info().status;
    console.log(`[ModelProvisioner] ${fileName} HTTP status: ${status}`);

    // --- Handle 416 Range Not Satisfiable ---
    if (status === 416) {
      // Server says our range-start exceeds the file. Verify actual on-disk size.
      const finalSize = await getFileSize(dest);
      if (isArtifactSizeValid(finalSize, expectedBytes)) {
        console.log(`[ModelProvisioner] 416 — ${fileName} already complete at ${fmtBytes(finalSize)} ✓`);
        return true;
      }
      // File is smaller than expected despite 416 — something is wrong; fail and restart.
      console.warn(`[ModelProvisioner] 416 but ${fileName} only ${fmtBytes(finalSize)} — deleting and retrying from 0`);
      await deleteUriIfExists(dest);
      return false;
    }

    if (status < 200 || status >= 300) {
      console.warn(`[ModelProvisioner] ${fileName} unexpected status: ${status}`);
      return false;
    }

    if (status === 200 && existingSize > 0) {
      console.warn(
        `[ModelProvisioner] Server ignored Range for ${fileName}. Deleting corrupt append and retrying fresh.`,
      );
      await deleteUriIfExists(dest);
      return false;
    }

    const finalSize = await getFileSize(dest);
    console.log(
      `[ModelProvisioner] ${fileName} download finished. On-disk: ${fmtBytes(finalSize)} / expected: ${fmtBytes(expectedBytes)}`,
    );

    if (isArtifactSizeValid(finalSize, expectedBytes)) {
      return true;
    }

    if (finalSize > expectedBytes + SIZE_SLACK_BYTES) {
      console.warn(
        `[ModelProvisioner] ${fileName} overshot expected size (${fmtBytes(finalSize)}). Deleting corrupt file and retrying.`,
      );
      await deleteUriIfExists(dest);
      return false;
    }

    console.warn(
      `[ModelProvisioner] ${fileName} truncated! ${fmtBytes(finalSize)} < ${fmtBytes(expectedBytes)}. Will retry.`,
    );
    return false;

  } catch (e) {
    console.warn(`[ModelProvisioner] ${fileName} download exception:`, e);
    // Don't delete partial file — preserve for resume next time
    return false;
  }
}

async function ensureArtifactDownloaded(opts: {
  fileName: string;
  dest: string;
  urls: string[];
  expectedBytes: number;
  weightStart: number;
  weightTotal: number;
  maxAttempts: number;
  onProgress: (p: DetailedProgress) => void;
}): Promise<number> {
  const { fileName, dest, urls, expectedBytes, weightStart, weightTotal, maxAttempts, onProgress } = opts;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    let currentSize = await getFileSize(dest);
    if (isArtifactSizeValid(currentSize, expectedBytes)) {
      console.log(`[ModelProvisioner] ${fileName} already complete (${fmtBytes(currentSize)})`);
      onProgress({ progress: weightStart + weightTotal, statusLabel: `${fileName} ready` });
      return currentSize;
    }

    if (currentSize > expectedBytes + SIZE_SLACK_BYTES) {
      console.warn(
        `[ModelProvisioner] ${fileName} local file is oversized (${fmtBytes(currentSize)}). Resetting.`,
      );
      await deleteUriIfExists(dest);
      currentSize = 0;
    }

    console.log(
      `[ModelProvisioner] ${fileName} attempt ${attempt}/${maxAttempts} — current size: ${fmtBytes(currentSize)}`,
    );
    await startDownloadSession(fileName);

    let ok = false;
    for (const url of urls) {
      ok = await downloadResumable({
        url,
        dest,
        fileName,
        expectedBytes,
        weightStart,
        weightTotal,
        onProgress,
      });
      if (ok) break;
    }

    if (ok) {
      return await getFileSize(dest);
    }

    if (attempt < maxAttempts) {
      console.log(`[ModelProvisioner] ${fileName} attempt ${attempt} incomplete — retrying...`);
      await sleep(2000);
    }
  }

  throw new Error(`${fileName} download failed after ${maxAttempts} attempts. Check network and try again.`);
}

async function ensureVoiceEngineReady(opts: {
  onProgress?: (p: DetailedProgress) => void;
  weightStart?: number;
  weightTotal?: number;
  allowNetwork?: boolean;
} = {}): Promise<boolean> {
  const {
    onProgress,
    weightStart = 0.92,
    weightTotal = 0.08,
    allowNetwork = false,
  } = opts;

  const whisperSize = await getFileSize(INTERNAL_WHISPER_PATH);
  if (isArtifactSizeValid(whisperSize, EXPECTED_WHISPER_BYTES)) {
    console.log(`[ModelProvisioner] Voice Engine already complete (${fmtBytes(whisperSize)})`);
    onProgress?.({ progress: weightStart + weightTotal, statusLabel: 'Voice Engine ready' });
    return true;
  }

  if (whisperSize > 0) {
    console.warn(
      `[ModelProvisioner] Voice Engine local file is incomplete (${fmtBytes(whisperSize)}). Resuming web download.`,
    );
  }

  if (!allowNetwork) {
    console.warn('[ModelProvisioner] Voice Engine missing and network fallback is disabled.');
    return false;
  }

  try {
    const finalWhisperSize = await ensureArtifactDownloaded({
      fileName: 'Voice Engine',
      dest: INTERNAL_WHISPER_PATH,
      urls: WHISPER_URLS,
      expectedBytes: EXPECTED_WHISPER_BYTES,
      weightStart,
      weightTotal,
      maxAttempts: 6,
      onProgress: onProgress ?? (() => {}),
    });
    return isArtifactSizeValid(finalWhisperSize, EXPECTED_WHISPER_BYTES);
  } catch (e) {
    console.warn('[ModelProvisioner] Voice Engine provisioning failed:', e);
    return false;
  }
}

export const ModelProvisioner = {
  async isModelProvisioned(): Promise<boolean> {
    try {
      // 1. Fast path: completion marker written after verified download
      const marker = await FileSystem.getInfoAsync(DONE_MARKER_PATH);
      const state = await getArtifactState();
      if (marker.exists) {
        if (isFullyProvisioned(state)) {
          console.log(
            `[ModelProvisioner] Done marker + valid local artifacts (LLM=${fmtBytes(state.llmSize)}, Whisper=${fmtBytes(state.whisperSize)}) — provisioned ✓`,
          );
          return true;
        }
        console.warn(
          `[ModelProvisioner] Stale done marker (LLM=${fmtBytes(state.llmSize)}, Whisper=${fmtBytes(state.whisperSize)}). Removing.`,
        );
        await FileSystem.deleteAsync(DONE_MARKER_PATH, { idempotent: true });
      }

      console.log(`[ModelProvisioner] LLM: ${fmtBytes(state.llmSize)}, Whisper: ${fmtBytes(state.whisperSize)}`);

      if (isFullyProvisioned(state)) {
        await writeDoneMarker(state);
      }
      return isFullyProvisioned(state);
    } catch (e) {
      console.error('[ModelProvisioner] isModelProvisioned error:', e);
      return false;
    }
  },

  async isVoiceModelProvisioned(): Promise<boolean> {
    const whisperSize = await getFileSize(INTERNAL_WHISPER_PATH);
    return isArtifactSizeValid(whisperSize, EXPECTED_WHISPER_BYTES);
  },

  getInternalModelPath(): string {
    return Platform.OS === 'android'
      ? INTERNAL_MODEL_PATH.replace('file://', '')
      : INTERNAL_MODEL_PATH;
  },

  async ensureVoiceEngineReady(): Promise<boolean> {
    return ensureVoiceEngineReady({ allowNetwork: false });
  },

  async provisionModel(onProgress: (p: DetailedProgress) => void): Promise<void> {
    if (_isProvisioning) { console.log('[ModelProvisioner] Already provisioning — ignoring duplicate call'); return; }
    _isProvisioning = true;

    try {
      const llmInitialSize = await getFileSize(INTERNAL_MODEL_PATH);
      if (isArtifactSizeValid(llmInitialSize, EXPECTED_LLM_BYTES)) {
        console.log(`[ModelProvisioner] Neural Weights already complete (${fmtBytes(llmInitialSize)})`);
        onProgress({ progress: 0.92, statusLabel: 'Neural Weights ready' });
      } else {
        onProgress({ progress: 0, statusLabel: 'Preparing Hugging Face downlink...' });
        await ensureArtifactDownloaded({
          fileName: 'Neural Weights',
          dest: INTERNAL_MODEL_PATH,
          urls: LLM_URLS,
          expectedBytes: EXPECTED_LLM_BYTES,
          weightStart: 0,
          weightTotal: 0.92,
          maxAttempts: 8,
          onProgress,
        });
      }

      const llmVerifiedState = await getArtifactState();
      const llmFinalSize = llmVerifiedState.llmSize;
      const whisperInitialSize = llmVerifiedState.whisperSize;
      console.log(`[ModelProvisioner] Final LLM size: ${fmtBytes(llmFinalSize)} / expected: ${fmtBytes(EXPECTED_LLM_BYTES)}`);
      console.log(`[ModelProvisioner] Current Whisper size: ${fmtBytes(whisperInitialSize)} / expected: ${fmtBytes(EXPECTED_WHISPER_BYTES)}`);

      if (!isArtifactSizeValid(llmFinalSize, EXPECTED_LLM_BYTES)) {
        throw new Error(
          `Model file incomplete: ${fmtBytes(llmFinalSize)} on disk, expected ~${fmtBytes(EXPECTED_LLM_BYTES)}. ` +
          'Please retry.'
        );
      }

      const voiceReady = await ensureVoiceEngineReady({
        onProgress,
        weightStart: 0.92,
        weightTotal: 0.08,
        allowNetwork: true,
      });

      const finalState = await getArtifactState();
      console.log(`[ModelProvisioner] Final Whisper size: ${fmtBytes(finalState.whisperSize)} / expected: ${fmtBytes(EXPECTED_WHISPER_BYTES)}`);

      if (!isFullyProvisioned(finalState)) {
        throw new Error(
          voiceReady
            ? 'Downloads finished, but verification failed. Please retry.'
            : 'Voice engine is incomplete. Please retry to resume provisioning.'
        );
      }

      await writeDoneMarker(finalState);

      await finishDownloadSession();
      onProgress({
        progress: 1,
        statusLabel: voiceReady ? 'Systems Online' : 'Core model ready. Voice engine pending',
      });

    } catch (e: any) {
      await failDownloadSession(e?.message ?? 'Download failed');
      throw e;
    } finally {
      _isProvisioning = false;
    }
  },
};
