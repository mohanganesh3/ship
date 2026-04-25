import React, { useEffect } from 'react';
import { View, StyleSheet } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withTiming,
  Easing,
  interpolate,
} from 'react-native-reanimated';
import { Colors } from '../constants/theme';

export const ThinkingGlow = () => {
  const progress = useSharedValue(0);

  useEffect(() => {
    progress.value = withRepeat(
      withTiming(1, { 
        duration: 2500, 
        easing: Easing.bezier(0.4, 0, 0.2, 1) 
      }),
      -1,
      true
    );
  }, []);

  const glow1 = useAnimatedStyle(() => ({
    transform: [{ scale: interpolate(progress.value, [0, 1], [0.8, 1.2]) }],
    opacity: interpolate(progress.value, [0, 1], [0.1, 0.3]),
  }));

  const glow2 = useAnimatedStyle(() => ({
    transform: [{ scale: interpolate(progress.value, [0, 1], [0.6, 1.5]) }],
    opacity: interpolate(progress.value, [0, 1], [0.05, 0.15]),
  }));

  return (
    <View style={styles.container}>
      <Animated.View style={[styles.circle, glow2, { backgroundColor: Colors.amber }]} />
      <Animated.View style={[styles.circle, glow1, { backgroundColor: Colors.thinking }]} />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
    alignItems: 'center',
    overflow: 'hidden',
    zIndex: -1,
  },
  circle: {
    position: 'absolute',
    width: 60,
    height: 60,
    borderRadius: 30,
  },
});
