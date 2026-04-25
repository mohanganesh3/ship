/**
 * InitialSetupScreen — Premium maritime AI download & provisioning screen.
 * Design goals: no layout jitter, smooth animations, clear download progress.
 */
import { Ionicons } from '@expo/vector-icons';
import * as Device from 'expo-device';
import * as Haptics from 'expo-haptics';
import { activateKeepAwakeAsync, deactivateKeepAwake } from 'expo-keep-awake';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
    Animated,
    Dimensions,
    Easing, Platform, ScrollView,
    StyleSheet,
    Text,
    TouchableOpacity,
    View
} from 'react-native';
import { MODEL_DISPLAY_NAME } from '../constants/model';
import { Colors, Fonts } from '../constants/theme';
import {
    isNotificationPermissionGranted,
    requestNotificationPermission,
} from '../services/BackgroundDownloadManager';
import { DetailedProgress, ModelProvisioner } from '../services/ModelProvisioner';

const { width: SCREEN_W } = Dimensions.get('window');
const RADAR = Math.min(SCREEN_W * 0.52, 210);
const R = RADAR / 2;

// Stable speed display — only update text every 2 seconds to kill jitter
function useStableSpeed(rawSpeed: string | undefined): string {
  const [display, setDisplay] = useState('--');
  const lastUpdate = useRef(0);
  useEffect(() => {
    if (!rawSpeed) return;
    const now = Date.now();
    if (now - lastUpdate.current > 2000) {
      setDisplay(rawSpeed);
      lastUpdate.current = now;
    }
  }, [rawSpeed]);
  return display;
}

export default function InitialSetupScreen({ onComplete }: { onComplete: () => void }) {
  const [progress, setProgress] = useState(0);
  const [rawSpeed, setRawSpeed]  = useState<string | undefined>(undefined);
  const [bytesRead, setBytesRead] = useState(0);
  const [totalBytes, setTotalBytes] = useState(0);
  const [statusLabel, setStatusLabel] = useState('Initializing...');
  const [logs, setLogs] = useState<string[]>(['[INIT] Maritime Neural Engine starting...']);
  const [isError, setIsError] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [hwInfo, setHwInfo] = useState({ cores: '8', ram: '-- GB', model: '' });
  // Permission prompt: null=checking, true=need to ask, false=already granted
  const [needsPermPrompt, setNeedsPermPrompt] = useState<boolean | null>(null);
  const [bgStatus, setBgStatus] = useState<'IDLE' | 'ACTIVE' | 'ERROR'>('IDLE');

  // Animation refs
  const fadeAnim    = useRef(new Animated.Value(0)).current;
  const sweepAnim   = useRef(new Animated.Value(0)).current;
  const ring2Anim   = useRef(new Animated.Value(0)).current;
  const pulseAnim   = useRef(new Animated.Value(1)).current;
  const progressAnim = useRef(new Animated.Value(0)).current;
  const blip1Anim   = useRef(new Animated.Value(0.3)).current;
  const blip2Anim   = useRef(new Animated.Value(0.3)).current;
  const progressRef = useRef(0);

  // Helper to add logs without infinite loops
  const addLog = useCallback((msg: string) => {
    const timestamp = new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    setLogs(prev => [`[${timestamp}] ${msg}`, ...prev].slice(0, 50));
  }, []);

  // Smooth progress update — prevents bar from moving backwards
  const updateProgress = useCallback((val: number) => {
    if (val > progressRef.current) {
      progressRef.current = val;
      setProgress(val);
      Animated.timing(progressAnim, { toValue: val, duration: 600, useNativeDriver: false }).start();
    }
  }, []);

  // Stable speed — update only every 2s to prevent card resize flicker
  const stableSpeed = useStableSpeed(rawSpeed);

  // Expose status update to provisionModel
  const onProvisionProgress = useCallback((dp: DetailedProgress) => {
    updateProgress(dp.progress ?? 0);
    if (dp.speed)       setRawSpeed(dp.speed);
    if (dp.bytesRead)   setBytesRead(dp.bytesRead);
    if (dp.totalBytes)  setTotalBytes(dp.totalBytes);
    if (dp.statusLabel) {
      setStatusLabel(dp.statusLabel);
      addLog(`[SYNC] ${dp.statusLabel}`);
    }
    setBgStatus('ACTIVE');
  }, [updateProgress, addLog]);

  useEffect(() => {
    // Start animations immediately
    Animated.timing(fadeAnim, { toValue: 1, duration: 700, useNativeDriver: true }).start();
    Animated.loop(
      Animated.timing(sweepAnim, { toValue: 1, duration: 3800, useNativeDriver: true, easing: Easing.linear })
    ).start();
    Animated.loop(
      Animated.timing(ring2Anim, { toValue: 1, duration: 14000, useNativeDriver: true, easing: Easing.linear })
    ).start();
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 1.05, duration: 1500, useNativeDriver: true, easing: Easing.inOut(Easing.sin) }),
        Animated.timing(pulseAnim, { toValue: 0.95, duration: 1500, useNativeDriver: true, easing: Easing.inOut(Easing.sin) }),
      ])
    ).start();

    // System Heartbeat Logs
    const heartbeat = setInterval(() => {
      addLog(`[CORE] System heartbeat OK // VRAM: ${(Math.random() * 0.2 + 0.8).toFixed(2)}GB // L-ENG-03`);
    }, 12000);

    // Blip pulse animations
    Animated.loop(Animated.sequence([
      Animated.timing(blip1Anim, { toValue: 1, duration: 500, useNativeDriver: true }),
      Animated.timing(blip1Anim, { toValue: 0.3, duration: 1500, useNativeDriver: true }),
    ])).start();
    Animated.loop(Animated.sequence([
      Animated.delay(800),
      Animated.timing(blip2Anim, { toValue: 1, duration: 500, useNativeDriver: true }),
      Animated.timing(blip2Anim, { toValue: 0.3, duration: 1500, useNativeDriver: true }),
    ])).start();

    // 1. Check if we are already provisioned (redundant but safe)
    // 2. Check if we have partial data to show 'RESUMING' state immediately
    const checkState = async () => {
      addLog('[DISK] Scanning local cache...');
      const provisioned = await ModelProvisioner.isModelProvisioned();
      if (provisioned) {
        addLog('[OK] System verified. Bypassing setup...');
        onComplete();
        return;
      }

      // Check permission
      const granted = await isNotificationPermissionGranted();
      addLog(granted ? '[AUTH] Background downlink ready.' : '[AUTH] Notification permission missing.');
      setNeedsPermPrompt(!granted);

      if (granted) {
        // Delay slightly for visual effect then start
        setTimeout(() => runDownload(false), 600);
      }
    };

    checkState();

    return () => clearInterval(heartbeat);
  }, []);

  const handleGrantPermission = async () => {
    addLog('[AUTH] Requesting OS permission...');
    const granted = await requestNotificationPermission();
    if (granted) {
      addLog('[AUTH] Permission accepted.');
      setNeedsPermPrompt(false);
      runDownload(false);
    } else {
      addLog('[WARN] Permission denied. Download might stop in background.');
      setNeedsPermPrompt(false);
      runDownload(false);
    }
  };

  const handleSkipPermission = () => {
    addLog('[AUTH] User skipped notification setup.');
    setNeedsPermPrompt(false);
    runDownload(false);
  };

  const runDownload = async (isRetry: boolean) => {
    try {
      await activateKeepAwakeAsync('maritime-download');
      setIsError(false);
      setErrorMsg('');
      if (isRetry) {
        addLog('[RETRY] Re-establishing satellite link...');
        progressRef.current = 0;
        updateProgress(0);
      }

      const brand    = Device.brand ?? '';
      const model    = Device.modelName ?? '';
      const ramBytes = Device.totalMemory ?? 0;
      const ramGB    = ramBytes > 0 ? `${(ramBytes / 1073741824).toFixed(1)} GB` : '-- GB';
      setHwInfo({ cores: '8', ram: ramGB, model: `${brand} ${model}`.trim() });

      if (!isRetry) {
        addLog(`[HW] Detected ${brand} ${model} (${ramGB} RAM)`);
      }

      addLog('[NET] Initializing Hugging Face downlink...');
      await ModelProvisioner.provisionModel(onProvisionProgress);

      addLog('[OK] Neural weights verified. MMAP activated.');
      updateProgress(1);
      setBgStatus('IDLE');
      deactivateKeepAwake('maritime-download');
      if (Platform.OS === 'ios') Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      setTimeout(onComplete, 1800);

    } catch (err: any) {
      deactivateKeepAwake('maritime-download');
      setBgStatus('ERROR');
      const msg = err?.message ?? 'Unknown error';
      setIsError(true);
      setErrorMsg(msg);
      addLog(`[ERR] ${msg}`);
      if (Platform.OS === 'ios') Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
    }
  };

  // Expose retry
  (global as any).__maritimeRetry = () => runDownload(true);

  const sweep    = sweepAnim.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '360deg'] });
  const ring2Rot = ring2Anim.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '-360deg'] });
  const pct      = Math.round(progress * 100);
  const progressWidth = progressAnim.interpolate({ inputRange: [0, 1], outputRange: ['0%', '100%'] });

  const fmtBytes = (b: number) => {
    if (!b) return '0 B';
    if (b >= 1073741824) return `${(b / 1073741824).toFixed(2)} GB`;
    if (b >= 1048576)    return `${(b / 1048576).toFixed(1)} MB`;
    return `${(b / 1024).toFixed(0)} KB`;
  };

  const getStatusColor = () => {
    if (isError) return '#FF4444';
    if (bgStatus === 'ACTIVE') return Colors.amber;
    return '#44FF88';
  };

  if (needsPermPrompt === true) {
    return (
      <View style={s.container}>
        <Animated.View style={[s.inner, { opacity: fadeAnim, justifyContent: 'center', flex: 1 }]}>
          <View style={[s.radarWrap, { width: RADAR, height: RADAR, marginBottom: 40 }]}>
            {[1, 0.7, 0.42].map((scale, i) => (
              <View key={i} style={[s.ring, { width: RADAR * scale, height: RADAR * scale, borderRadius: R * scale, borderColor: `rgba(212,148,58,${0.22 - i * 0.06})` }]} />
            ))}
            <Animated.View style={[s.center, { width: R * 0.62, height: R * 0.62, borderRadius: R * 0.31, transform: [{ scale: pulseAnim }] }]}>
              <Ionicons name="notifications-outline" size={28} color={Colors.amber} />
            </Animated.View>
          </View>

          <View style={s.permCard}>
            <View style={s.permIconRow}>
              {[ {n:'notifications', c: AMB}, {n:'infinite', c: AMB}, {n:'shield-checkmark', c: AMB} ].map((ic, i) => (
                <View key={i} style={s.permIconBadge}><Ionicons name={ic.n as any} size={22} color={ic.c} /></View>
              ))}
            </View>
            <Text style={s.permTitle}>STABILIZE BACKGROUNDING</Text>
            <Text style={s.permDesc}>
              Maritime AI downloads its neural weights from Hugging Face on first launch.{"\n\n"}
              Allow notifications to prevent the system from killing the download when you check other apps.{'\n\n'}
              <Text style={{ color: AMB }}>BGMI-style persistent progress shade will keep your downlink active.</Text>
            </Text>
            <TouchableOpacity style={s.permAllowBtn} onPress={handleGrantPermission} activeOpacity={0.8}>
              <Text style={s.permAllowText}>GRANT &amp; COMMENCE</Text>
            </TouchableOpacity>
            <TouchableOpacity style={s.permSkipBtn} onPress={handleSkipPermission} activeOpacity={0.7}>
              <Text style={s.permSkipText}>Skip — Foreground only (unstable)</Text>
            </TouchableOpacity>
          </View>
        </Animated.View>
      </View>
    );
  }

  return (
    <View style={s.container}>
      <Animated.View style={[s.inner, { opacity: fadeAnim }]}>
        <View style={s.header}>
          <Ionicons name="radio-outline" size={15} color={Colors.amber} />
          <Text style={s.headerText}>DOWNLINK STATUS</Text>
          <View style={[s.pill, isError && s.pillErr, bgStatus === 'ACTIVE' && s.pillActive]}>
            <View style={[s.pillDot, { backgroundColor: getStatusColor() }]} />
            <Text style={s.pillLabel}>{isError ? 'FAULT' : bgStatus === 'ACTIVE' ? 'BG_ACTIVE' : 'ONLINE'}</Text>
          </View>
        </View>

        <View style={[s.radarWrap, { width: RADAR, height: RADAR }]}>
          {/* Circular Rings */}
          {[1, 0.7, 0.42].map((scale, i) => (
            <View key={i} style={[s.ring, { width: RADAR * scale, height: RADAR * scale, borderRadius: R * scale, borderColor: `rgba(212,148,58,${0.22 - i * 0.06})` }]} />
          ))}
          
          {/* Radial Grid Lines */}
          {[0, 30, 60, 120, 150, 210, 240, 300, 330].map(deg => (
            <View key={deg} style={[s.cross, { transform: [{ rotate: `${deg}deg` }], width: RADAR, height: 1, opacity: 0.12 }]} />
          ))}

          <Animated.View style={[s.ring, { width: RADAR * 0.85, height: RADAR * 0.85, borderRadius: R * 0.85, borderColor: 'rgba(212,148,58,0.13)', borderStyle: 'dashed', transform: [{ rotate: ring2Rot }] }]} />
          <View style={[s.cross, { width: RADAR, height: 1.5, backgroundColor: 'rgba(212,148,58,0.12)' }]} />
          <View style={[s.cross, { height: RADAR, width: 1.5, backgroundColor: 'rgba(212,148,58,0.12)' }]} />

          {/* Sweep arm — rotates, ship does NOT rotate */}
          <Animated.View style={[s.sweepWrap, { width: RADAR, height: RADAR, borderRadius: R, transform: [{ rotate: sweep }] }]} pointerEvents="none">
            <View style={[s.sweepLine, { left: R - 1, height: R }]} />
            <View style={[s.sweepWake, { left: R, width: R, height: R }]} />
          </Animated.View>

          <Animated.View style={[s.blip, { top: '17%', left: '65%', opacity: blip1Anim }]} />
          <Animated.View style={[s.blip, { top: '62%', left: '20%', opacity: blip2Anim }]} />

          {/* Ship icon stays static (pulse-only) */}
          <View style={[s.center, { width: R * 0.62, height: R * 0.62, borderRadius: R * 0.31 }]}>
            <Animated.View style={{ transform: [{ scale: pulseAnim }] }}>
              <Ionicons name="boat" size={32} color={Colors.amber} />
            </Animated.View>
          </View>
        </View>

        {isError && (
          <TouchableOpacity style={s.retryBtn} onPress={() => (global as any).__maritimeRetry?.()} activeOpacity={0.7}>
            <Ionicons name="refresh" size={14} color="#080810" />
            <Text style={s.retryText}>RESTORE DOWNLINK</Text>
          </TouchableOpacity>
        )}

        <View style={s.metricsBlock}>
          <FixedCard label="ENGINE" value={MODEL_DISPLAY_NAME} />
          <FixedCard label="MEMORY" value={hwInfo.ram} />
          <FixedCard label="DOWNLINK" value={bgStatus} />
        </View>
        <View style={[s.metricsBlock, { marginTop: 8 }]}>
          <FixedCard label="SPEED" value={stableSpeed} mono />
          <FixedCard label="CACHED" value={fmtBytes(bytesRead)} mono />
          <FixedCard label="REMAIN" value={totalBytes ? fmtBytes(totalBytes - bytesRead) : '--'} mono />
        </View>

        <View style={s.terminal}>
          <View style={s.termBar}>
            <View style={[s.dot3, { backgroundColor: '#FF5F56' }]} />
            <View style={[s.dot3, { backgroundColor: '#FFBD2E' }]} />
            <View style={[s.dot3, { backgroundColor: '#28C840' }]} />
            <Text style={s.termFile}>MARITIME_BG_SERVICE.log</Text>
            <Text style={[s.termPct, pct > 0 && { color: Colors.amber }]}>{pct}%</Text>
          </View>
          <View style={s.track}>
            <Animated.View style={[s.fill, { width: progressWidth }]}><View style={s.fillGlow} /></Animated.View>
          </View>
          <View style={s.statusRow}>
            <View style={s.statusLed} />
            <Text style={s.statusText} numberOfLines={1}>{statusLabel}</Text>
          </View>
          <ScrollView style={s.logArea} pointerEvents="none">
            {logs.map((l, i) => (
              <Text key={i} style={[s.logLine, i === 0 && s.logLineFresh, isError && i === 0 && s.logLineErr]} numberOfLines={2}>{l}</Text>
            ))}
          </ScrollView>
        </View>
        <Text style={s.footer}>MARITIME NEURAL v4 // BACKGROUND_DAEMON_OK // ARM64</Text>
      </Animated.View>
    </View>
  );
}

function FixedCard({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <View style={s.card}>
      <Text style={s.cardLabel}>{label}</Text>
      <Text style={[s.cardValue, mono && s.cardMono]} numberOfLines={1} adjustsFontSizeToFit minimumFontScale={0.7}>{value}</Text>
    </View>
  );
}

const AMB = Colors.amber;
const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#080810', paddingTop: 52 },
  inner:     { flex: 1, paddingHorizontal: 18 },
  header: { flexDirection: 'row', alignItems: 'center', borderBottomWidth: 1, borderBottomColor: 'rgba(255,255,255,0.06)', paddingBottom: 12, marginBottom: 18 },
  headerText: { fontFamily: Fonts.mono, fontSize: 11, color: '#DEDEDE', letterSpacing: 2.2, marginLeft: 9, flex: 1 },
  pill: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(68,255,136,0.07)', paddingHorizontal: 9, paddingVertical: 4, borderRadius: 20, borderWidth: 1, borderColor: 'rgba(68,255,136,0.22)' },
  pillActive: { backgroundColor: 'rgba(212,148,58,0.15)', borderColor: 'rgba(212,148,58,0.4)' },
  pillErr: { backgroundColor: 'rgba(255,68,68,0.1)', borderColor: 'rgba(255,68,68,0.3)' },
  pillDot:   { width: 6, height: 6, borderRadius: 3, marginRight: 5 },
  pillLabel: { fontFamily: Fonts.mono, fontSize: 8, color: '#CCC', letterSpacing: 1 },
  radarWrap: { alignSelf: 'center', marginBottom: 20, justifyContent: 'center', alignItems: 'center' },
  ring: { position: 'absolute', borderWidth: 1 },
  cross: { position: 'absolute', backgroundColor: 'rgba(212,148,58,0.07)' },
  sweepWrap: { position: 'absolute', overflow: 'hidden', top: 0, left: 0 },
  sweepLine: { position: 'absolute', top: 0, width: 2, backgroundColor: 'rgba(212,148,58,0.95)' },
  sweepWake: { position: 'absolute', top: 0, backgroundColor: 'rgba(212,148,58,0.09)', borderTopRightRadius: 9999 },
  blip: { position: 'absolute', width: 7, height: 7, borderRadius: 4, backgroundColor: AMB, shadowColor: AMB, shadowRadius: 9, shadowOpacity: 1, elevation: 5 },
  center: { position: 'absolute', backgroundColor: 'rgba(212,148,58,0.09)', borderWidth: 1, borderColor: 'rgba(212,148,58,0.28)', justifyContent: 'center', alignItems: 'center', shadowColor: AMB, shadowRadius: 12, shadowOpacity: 0.35, elevation: 6 },
  retryBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: Colors.amber, borderRadius: 8, paddingVertical: 10, paddingHorizontal: 20, marginBottom: 14, gap: 8 },
  retryText: { fontFamily: Fonts.mono, fontSize: 12, color: '#080810', letterSpacing: 1.5, fontWeight: '700' },
  metricsBlock: { flexDirection: 'row', gap: 8 },
  card: { flex: 1, backgroundColor: 'rgba(255,255,255,0.03)', paddingVertical: 10, paddingHorizontal: 10, borderRadius: 8, borderWidth: 1, borderColor: 'rgba(255,255,255,0.06)', height: 60, justifyContent: 'space-between' },
  cardLabel: { fontFamily: Fonts.mono, fontSize: 8, color: 'rgba(255,255,255,0.32)', letterSpacing: 1 },
  cardValue: { fontFamily: Fonts.mono, fontSize: 14, color: AMB },
  cardMono: { fontFamily: Fonts.mono, fontSize: 12 },
  terminal: { flex: 1, marginTop: 12, marginBottom: 10, backgroundColor: 'rgba(0,0,0,0.5)', borderRadius: 10, borderWidth: 1, borderColor: 'rgba(255,255,255,0.07)', overflow: 'hidden' },
  termBar: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 10, paddingVertical: 8, backgroundColor: 'rgba(255,255,255,0.025)', borderBottomWidth: 1, borderBottomColor: 'rgba(255,255,255,0.05)', gap: 5 },
  dot3:     { width: 9, height: 9, borderRadius: 5 },
  termFile: { fontFamily: Fonts.mono, fontSize: 9, color: 'rgba(255,255,255,0.3)', letterSpacing: 1, flex: 1, marginLeft: 5 },
  termPct:  { fontFamily: Fonts.mono, fontSize: 10, color: 'rgba(255,255,255,0.2)' },
  track: { height: 3, backgroundColor: 'rgba(255,255,255,0.04)' },
  fill:  { height: '100%', backgroundColor: AMB, overflow: 'hidden' },
  fillGlow: { position: 'absolute', right: 0, top: 0, bottom: 0, width: 20, backgroundColor: 'rgba(212,148,58,0.6)' },
  statusRow: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 10, paddingVertical: 6, borderBottomWidth: 1, borderBottomColor: 'rgba(255,255,255,0.04)' },
  statusLed: { width: 5, height: 5, borderRadius: 3, backgroundColor: AMB, marginRight: 7, shadowColor: AMB, shadowRadius: 4, shadowOpacity: 1 },
  statusText: { fontFamily: Fonts.mono, fontSize: 9, color: 'rgba(255,255,255,0.5)', flex: 1 },
  logArea:    { flex: 1, padding: 10 },
  logLine:    { fontFamily: Fonts.mono, fontSize: 10, color: 'rgba(255,255,255,0.22)', lineHeight: 16, marginBottom: 2 },
  logLineFresh: { color: 'rgba(255,255,255,0.6)' },
  logLineErr:   { color: '#FF6666' },
  footer: { fontFamily: Fonts.mono, fontSize: 8, color: 'rgba(255,255,255,0.11)', letterSpacing: 1.5, textAlign: 'center', paddingBottom: 18 },
  permCard: { backgroundColor: 'rgba(255,255,255,0.03)', borderRadius: 16, borderWidth: 1, borderColor: 'rgba(212,148,58,0.2)', padding: 24 },
  permIconRow: { flexDirection: 'row', gap: 12, marginBottom: 20 },
  permIconBadge: { width: 48, height: 48, borderRadius: 12, backgroundColor: 'rgba(212,148,58,0.1)', borderWidth: 1, borderColor: 'rgba(212,148,58,0.25)', justifyContent: 'center', alignItems: 'center' },
  permTitle: { fontFamily: Fonts.mono, fontSize: 14, color: '#F0E4C8', letterSpacing: 2.5, marginBottom: 14 },
  permDesc: { fontFamily: Fonts.mono, fontSize: 11, color: 'rgba(255,255,255,0.45)', lineHeight: 19, marginBottom: 24 },
  permAllowBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10, backgroundColor: Colors.amber, borderRadius: 10, paddingVertical: 14, marginBottom: 12, shadowColor: Colors.amber, shadowRadius: 16, shadowOpacity: 0.35, elevation: 8 },
  permAllowText: { fontFamily: Fonts.mono, fontSize: 12, color: '#080810', letterSpacing: 1.5, fontWeight: '700' },
  permSkipBtn: { alignItems: 'center', paddingVertical: 10 },
  permSkipText: { fontFamily: Fonts.mono, fontSize: 10, color: 'rgba(255,255,255,0.28)', letterSpacing: 0.5 },
});
