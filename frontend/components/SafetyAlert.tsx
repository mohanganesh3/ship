/**
 * SafetyAlert v2 — Inline card, softer design
 *
 * No floating glow or heavy shadow. Subtle red border + dim red background.
 * Pulsing indicator is kept (real UI element) but smaller/quieter.
 */
import React, { useEffect } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withTiming,
  FadeIn,
  Easing,
} from 'react-native-reanimated';
import { Colors, Fonts, Type, Space, Radius } from '../constants/theme';
import { useTheme } from '../providers/ThemeProvider';

interface SafetyAlertProps {
  message?: string;
}

export function SafetyAlert({ message }: SafetyAlertProps) {
  const { colors } = useTheme();
  const pulse = useSharedValue(0.5);

  useEffect(() => {
    pulse.value = withRepeat(
      withTiming(1, { duration: 1200, easing: Easing.inOut(Easing.ease) }),
      -1,
      true,
    );
  }, []);

  const dotStyle = useAnimatedStyle(() => ({ opacity: pulse.value }));

  return (
    <Animated.View
      entering={FadeIn.duration(300)}
      style={[styles.container, { backgroundColor: Colors.dangerDim }]}
    >
      <View style={styles.header}>
        <Animated.View style={[styles.dot, dotStyle]} />
        <Text style={styles.headerText}>Safety Escalation</Text>
      </View>
      <Text style={[styles.body, { color: colors.text2 }]}>
        {message ||
          'This situation requires immediate attention. Escalate to the Master and follow emergency procedures per the Safety Management Manual.'}
      </Text>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    borderRadius: Radius.sm,
    borderLeftWidth: 3,
    borderLeftColor: Colors.danger,
    padding: Space.lg,
    marginBottom: Space.md,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: Space.sm,
  },
  dot: {
    width: 7,
    height: 7,
    borderRadius: 4,
    backgroundColor: Colors.danger,
  },
  headerText: {
    fontFamily: Fonts.bodySemibold,
    fontSize: Type.sm.fontSize,
    color: Colors.danger,
  },
  body: {
    fontFamily: Fonts.body,
    fontSize: Type.sm.fontSize,
    lineHeight: Type.sm.lineHeight,
  },
});
