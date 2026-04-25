/**
 * ModelLoadingScreen v2 — Simpler, less over-themed
 */
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Animated, {
  Easing,
  FadeIn,
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';
import { Colors, Fonts, Type, Space, LoadingPhrases } from '../constants/theme';
import { AnchorIcon } from './icons';

interface ModelLoadingScreenProps {
  progress: number;
}

export function ModelLoadingScreen({ progress }: ModelLoadingScreenProps) {
  const rotation = useSharedValue(0);
  const [phrase, setPhrase] = useState(0);

  useEffect(() => {
    rotation.value = withRepeat(
      withTiming(360, { duration: 3000, easing: Easing.linear }),
      -1,
      false,
    );
  }, []);

  useEffect(() => {
    const i = setInterval(() => setPhrase(p => (p + 1) % LoadingPhrases.length), 3000);
    return () => clearInterval(i);
  }, []);

  const radarStyle = useAnimatedStyle(() => ({
    transform: [{ rotate: `${rotation.value}deg` }],
  }));

  return (
    <Animated.View entering={FadeIn.duration(400)} style={styles.container}>
      <View style={styles.radarWrap}>
        <View style={styles.radarBase} />
        <Animated.View style={[styles.radarSweep, radarStyle]}>
          <View style={styles.radarArc} />
        </Animated.View>
        <AnchorIcon size={36} color={Colors.amber} />
      </View>

      <Text style={styles.phrase}>{LoadingPhrases[phrase]}</Text>

      <View style={styles.track}>
        <View style={[styles.fill, { width: `${Math.round(progress * 100)}%` }]} />
      </View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.bg1,
    gap: Space.xl,
    padding: Space['2xl'],
  },
  phrase: {
    fontFamily: Fonts.body,
    fontSize: Type.base.fontSize,
    color: Colors.text3,
    textAlign: 'center',
  },
  track: {
    width: 160,
    height: 3,
    borderRadius: 2,
    backgroundColor: Colors.bg3,
    overflow: 'hidden',
  },
  fill: {
    height: '100%',
    borderRadius: 2,
    backgroundColor: Colors.amber,
  },
  radarWrap: {
    width: 54,
    height: 54,
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
  },
  radarBase: {
    position: 'absolute',
    width: 46,
    height: 46,
    borderRadius: 23,
    borderWidth: 1,
    borderColor: Colors.amber,
    opacity: 0.25,
  },
  radarSweep: {
    position: 'absolute',
    width: 46,
    height: 46,
    borderRadius: 23,
    alignItems: 'center',
    justifyContent: 'center',
  },
  radarArc: {
    width: 46,
    height: 46,
    borderRadius: 23,
    borderWidth: 2,
    borderColor: 'transparent',
    borderTopColor: Colors.amber,
    opacity: 0.95,
  },
});
