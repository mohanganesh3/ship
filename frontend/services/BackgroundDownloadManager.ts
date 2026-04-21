/**
 * BackgroundDownloadManager
 * 
 * - Uses @notifee/react-native to establish a true Foreground Service (dataSync payload).
 * - Survives App Swipes and recents-pause due to Android foreground rules.
 */

import notifee, { AndroidImportance, AndroidColor } from '@notifee/react-native';
import { Platform } from 'react-native';

const CHANNEL_ID     = 'maritime_download';
const NOTIF_ID       = 'maritime-neural-download';

let _isActive = false;
let _lastNotifTime = 0;
let _resolveForegroundTask: (() => void) | null = null;

// ─── Setup ────────────────────────────────────────────────────────────────────

export async function setupNotificationChannel(): Promise<void> {
  if (Platform.OS !== 'android') return;
  try {
    await notifee.createChannel({
      id:          CHANNEL_ID,
      name:        'Maritime Neural Download',
      importance:  AndroidImportance.DEFAULT,
      vibration:   false,
      lights:      false,
    });
  } catch (e) {
    console.warn('[BGDownload] Channel setup:', e);
  }
}

/**
 * Request notification permission with Notifee.
 * Returns true if granted.
 */
export async function requestNotificationPermission(): Promise<boolean> {
  try {
    const settings = await notifee.requestPermission();
    return settings.authorizationStatus >= 1; // 1 = AUTHORIZED
  } catch {
    return false;
  }
}

export async function isNotificationPermissionGranted(): Promise<boolean> {
  try {
    const settings = await notifee.getNotificationSettings();
    return settings.authorizationStatus >= 1;
  } catch {
    return false;
  }
}

/** Global foreground service resolver */
export function __bindForegroundTask(resolver: () => void) {
  _resolveForegroundTask = resolver;
}

// ─── Session ──────────────────────────────────────────────────────────────────

export async function startDownloadSession(fileName: string): Promise<void> {
  if (_isActive) return;
  _isActive = true;
  await _post({
    title:    `⚓ Maritime AI  ·  Connecting…`,
    body:     `Preparing to download ${fileName}`,
    progress: 0,
    ongoing:  true,
    indeterminate: true,
  });
}

export async function updateDownloadProgress(opts: {
  fileName:  string;
  progress:  number;
  speed?:    string;
  received?: string;
  total?:    string;
}): Promise<void> {
  if (!_isActive) return;
  const now = Date.now();
  if (now - _lastNotifTime < 2500) return; // throttle
  _lastNotifTime = now;

  const pct = Math.round(opts.progress * 100);
  const speedPart = opts.speed    ? `   ${opts.speed}` : '';
  const sizePart  = opts.received ? `   ${opts.received}${opts.total ? ` / ${opts.total}` : ''}` : '';

  await _post({
    title:    `⚓ Maritime AI  ·  ${pct}% complete`,
    body:     `${opts.fileName}${speedPart}${sizePart}`,
    progress: opts.progress,
    ongoing:  true,
    indeterminate: false,
  });
}

export async function finishDownloadSession(): Promise<void> {
  _isActive = false;
  if (_resolveForegroundTask) {
    _resolveForegroundTask();
    _resolveForegroundTask = null;
  }
  await _post({
    title:   `✦ Maritime AI  ·  Ready for Deployment`,
    body:    `Neural weights anchored. All systems nominal. Tap to open.`,
    progress: 1,
    ongoing:  false,
    indeterminate: false,
  });
}

export async function failDownloadSession(reason: string): Promise<void> {
  _isActive = false;
  if (_resolveForegroundTask) {
    _resolveForegroundTask();
    _resolveForegroundTask = null;
  }
  await _post({
    title:   `⚡ Maritime AI  ·  Download Failed`,
    body:    `${reason.slice(0, 100)}  —  Tap the app to retry.`,
    progress: 0,
    ongoing:  false,
    indeterminate: false,
  });
}

export async function dismissDownloadNotification(): Promise<void> {
  try { await notifee.cancelNotification(NOTIF_ID); } catch {}
}

// ─── Internal ─────────────────────────────────────────────────────────────────

interface NotifOpts {
  title:         string;
  body:          string;
  progress:      number;
  ongoing:       boolean;
  indeterminate: boolean;
}

async function _post(p: NotifOpts): Promise<void> {
  try {
    const granted = await isNotificationPermissionGranted();
    if (!granted) {
      console.log('[BGDownload] Skip posting notif: Permission not granted.');
      return;
    }

    console.log(`[BGDownload] Posting notification: ${p.title} (${Math.round(p.progress * 100)}%)`);

    await notifee.displayNotification({
      id: NOTIF_ID,
      title: p.title,
      body: p.body,
      android: {
        channelId: CHANNEL_ID,
        ongoing: p.ongoing,
        asForegroundService: p.ongoing, 
        color: '#D4943A',
        onlyAlertOnce: true,
        showTimestamp: true,
        autoCancel: !p.ongoing,
        progress: p.ongoing ? {
          max: 100,
          current: Math.round(p.progress * 100),
          indeterminate: p.indeterminate,
        } : undefined,
      },
    });
  } catch (e) {
    console.error('[BGDownload] Display notification error:', e);
  }
}
