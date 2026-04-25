import { Ionicons } from '@expo/vector-icons';
import { Audio } from 'expo-av';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
    PermissionsAndroid,
    Platform,
    Pressable, StyleSheet,
    Text, TextInput,
    View,
} from 'react-native';
import Animated, {
    Easing,
    useAnimatedStyle,
    useSharedValue,
    withRepeat,
    withSequence, withTiming,
} from 'react-native-reanimated';
import { Colors, Fonts, Radius, Space, Type } from '../constants/theme';
import { useTheme } from '../providers/ThemeProvider';
import { logger } from '../services/Logger';
import { VoiceService } from '../services/VoiceService';
import { SendArrowIcon } from './icons';

import * as Haptics from 'expo-haptics';

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);
const TAG = 'INPUT-UI';

/**
 * 2026 Premium Visualizer: Pulsing bars reflecting "activity"
 */
function Waveform() {
  const bars = [0, 1, 2, 3, 4];
  return (
    <View style={styles.waveformContainer}>
      {bars.map((i) => (
        <WaveformBar key={i} delay={i * 100} />
      ))}
    </View>
  );
}

function WaveformBar({ delay }: { delay: number }) {
  const heightVal = useSharedValue(4);
  useEffect(() => {
    heightVal.value = withRepeat(
      withSequence(
        withTiming(16, { duration: 400 + delay / 2, easing: Easing.bezier(0.4, 0, 0.2, 1) }),
        withTiming(6, { duration: 300 + delay / 2 })
      ),
      -1,
      true
    );
  }, []);

  const style = useAnimatedStyle(() => ({
    height: heightVal.value,
  }));

  return <Animated.View style={[styles.waveBar, style]} />;
}

interface InputTrayProps {
  onSend: (text: string) => void;
  initialValue?: string;
  disabled?: boolean;
  placeholder?: string;
}

export function InputTray({ onSend, initialValue = '', disabled = false, placeholder }: InputTrayProps) {
  const { colors } = useTheme();
  const [text, setText] = useState(initialValue);
  const [recordingState, setRecordingState] = useState<'idle' | 'recording' | 'transcribing'>('idle');
  const [voiceHint, setVoiceHint] = useState<string>('');
  const hintTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const recordingStartTimeRef = useRef<number>(0);

  const sendScale = useSharedValue(1);
  const micPulse = useSharedValue(1);

  const isRecording = recordingState === 'recording';
  const isTranscribing = recordingState === 'transcribing';

  useEffect(() => {
    setText(initialValue);
  }, [initialValue]);

  useEffect(() => {
    return () => {
      if (hintTimerRef.current) clearTimeout(hintTimerRef.current);
    };
  }, []);

  const showVoiceHint = useCallback((message: string) => {
    if (hintTimerRef.current) clearTimeout(hintTimerRef.current);
    setVoiceHint(message);
    hintTimerRef.current = setTimeout(() => setVoiceHint(''), 3500);
  }, []);

  async function startRecording() {
    if (recordingState !== 'idle') return;
    try {
      const readiness = await VoiceService.getReadiness();
      if (!readiness.available) {
        showVoiceHint(readiness.reason || 'Voice is not ready.');
        return;
      }

      if (Platform.OS !== 'web') {
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
      }

      const perm = await Audio.requestPermissionsAsync();
      if (perm.status !== 'granted') {
        showVoiceHint('Microphone permission is required for voice input.');
        return;
      }

      if (Platform.OS === 'android') {
        const androidPerm = await PermissionsAndroid.request(
          PermissionsAndroid.PERMISSIONS.RECORD_AUDIO,
        );
        if (androidPerm !== PermissionsAndroid.RESULTS.GRANTED) {
          showVoiceHint('Microphone permission is required for voice input.');
          return;
        }
      }
      
      const started = await VoiceService.startRealtimeCapture();
      if (!started) {
        showVoiceHint('Could not start voice capture.');
        return;
      }

      recordingStartTimeRef.current = Date.now();
      setRecordingState('recording');
      setVoiceHint('Recording… tap mic again to stop');
      micPulse.value = withRepeat(withTiming(1.3, { duration: 600 }), -1, true);
    } catch (err) {
      logger.error(TAG, 'Mic start error', err);
      showVoiceHint('Could not start recording on this device.');
      setRecordingState('idle');
    }
  }

  async function stopRecording() {
    if (recordingState !== 'recording') return;
    
    if (Platform.OS !== 'web') {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    }

    micPulse.value = withTiming(1);
    const durationMs = Date.now() - recordingStartTimeRef.current;

    try {
      setRecordingState('transcribing');

      const result = await VoiceService.stopRealtimeCapture(durationMs);
      if (result) {
        setText(prev => prev ? `${prev} ${result}` : result);
        if (Platform.OS !== 'web') Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
        setVoiceHint('Voice captured');
      } else {
        setVoiceHint('No speech detected. Try speaking clearly and closer to mic.');
      }
    } catch (err) {
      logger.error(TAG, 'Mic stop error', err);
      showVoiceHint('Could not transcribe audio.');
    } finally {
      setRecordingState('idle');
    }
  }

  const toggleRecording = useCallback(async () => {
    if (disabled || isTranscribing) return;
    if (recordingState === 'recording') {
      await stopRecording();
      return;
    }
    await startRecording();
  }, [disabled, isTranscribing, recordingState]);

  const handleSend = useCallback(() => {
    const trimmed = text.trim();
    if (!trimmed || disabled || isTranscribing) return;
    
    if (Platform.OS !== 'web') {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    }

    sendScale.value = withSequence(
      withTiming(0.85, { duration: 100 }),
      withTiming(1, { duration: 100 })
    );
    onSend(trimmed);
    setText('');
  }, [text, disabled, isTranscribing, onSend]);

  const sendStyle = useAnimatedStyle(() => ({ transform: [{ scale: sendScale.value }] }));
  const micStyle = useAnimatedStyle(() => ({
    transform: [{ scale: micPulse.value }],
  }));

  const hasText = text.trim().length > 0;
  const micIcon = isTranscribing ? 'sync' : isRecording ? 'mic' : 'mic-outline';
  const micColor = isRecording ? Colors.amber : isTranscribing ? Colors.amber : colors.text3;

  return (
    <View style={[styles.container, { backgroundColor: colors.bgPage }]}>
      <View style={[styles.pill, { 
        backgroundColor: isRecording ? 'rgba(212, 148, 58, 0.05)' : colors.bgSurface, 
        borderColor: isRecording ? Colors.amber : colors.borderMedium 
      }]}>
        <AnimatedPressable
          onPress={() => void toggleRecording()}
          style={[styles.micBtn, micStyle]}
          disabled={disabled || isTranscribing}
        >
          <Ionicons name={micIcon as any} size={22} color={micColor} />
        </AnimatedPressable>

        <TextInput
          style={[styles.input, { color: colors.text1 }]}
          value={text}
          onChangeText={setText}
          onSubmitEditing={handleSend}
          submitBehavior="submit"
          placeholder={
            isTranscribing ? 'Transcribing...' :
            isRecording ? '' :
            (placeholder || 'Ask Maritime AI...')
          }
          placeholderTextColor={colors.text2} // Higher contrast for maritime visibility
          multiline
          maxLength={2000}
          editable={!disabled && !isTranscribing && !isRecording}
          blurOnSubmit={false}
          autoCorrect
          autoCapitalize="sentences"
          enablesReturnKeyAutomatically
          returnKeyType="send"
          textAlignVertical="top"
        />

        {isRecording && <Waveform />}

        {hasText && !isRecording && !isTranscribing && (
          <AnimatedPressable
            onPress={handleSend}
            style={[styles.sendBtn, sendStyle]}
            disabled={disabled}
          >
            <SendArrowIcon size={16} color="#000" />
          </AnimatedPressable>
        )}
      </View>
      {!!voiceHint && (
        <Text style={[styles.voiceHint, { color: colors.text3 }]}>{voiceHint}</Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: Space.screenPadding,
    paddingVertical: Space.sm,
    paddingBottom: Platform.OS === 'ios' ? 34 : Space.md,
  },
  pill: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    borderWidth: 1.5,
    borderRadius: Radius.xl,
    paddingHorizontal: Space.md,
    paddingVertical: 10,
    minHeight: 56,
    maxHeight: 180,
    gap: Space.sm,
  },
  input: {
    flex: 1,
    fontFamily: Fonts.body,
    fontSize: Type.base.fontSize,
    lineHeight: Type.base.lineHeight,
    paddingVertical: 4,
  },
  waveformContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
    height: 36,
    paddingRight: 8,
  },
  waveBar: {
    width: 3,
    backgroundColor: Colors.amber,
    borderRadius: 2,
  },
  micBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendBtn: {
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: Colors.amber,
    alignItems: 'center',
    justifyContent: 'center',
  },
  voiceHint: {
    marginTop: 6,
    marginLeft: 8,
    fontFamily: Fonts.body,
    fontSize: 12,
    lineHeight: 16,
  },
});
