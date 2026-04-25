/**
 * TypingIndicator v2 — Refined colors for warm charcoal palette
 */
import React, { useEffect } from 'react';
import { View, StyleSheet, Text } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withTiming,
  withDelay,
  withSequence,
  Easing,
  FadeIn,
} from 'react-native-reanimated';
import type { SharedValue } from 'react-native-reanimated';
import { Colors, Space, Radius, Fonts } from '../constants/theme';
import { useTheme } from '../providers/ThemeProvider';
import { AnchorIcon } from './icons';

interface TypingIndicatorProps {
  status?: 'planning' | 'thinking' | 'writing' | 'idle';
}

export function TypingIndicator({ status = 'thinking' }: TypingIndicatorProps) {
  const { colors } = useTheme();
  const s1 = useSharedValue(1);
  const s2 = useSharedValue(1);
  const s3 = useSharedValue(1);

  useEffect(() => {
    const anim = (sv: SharedValue<number>, delay: number) => {
      sv.value = withDelay(
        delay,
        withRepeat(
          withSequence(
            withTiming(1.5, { duration: 350, easing: Easing.inOut(Easing.ease) }),
            withTiming(1, { duration: 350, easing: Easing.inOut(Easing.ease) }),
            withTiming(1, { duration: 500 }),
          ),
          -1,
          false,
        ),
      );
    };
    anim(s1, 0);
    anim(s2, 150);
    anim(s3, 300);
  }, []);

  const a1 = useAnimatedStyle(() => ({ transform: [{ scale: s1.value }] }));
  const a2 = useAnimatedStyle(() => ({ transform: [{ scale: s2.value }] }));
  const a3 = useAnimatedStyle(() => ({ transform: [{ scale: s3.value }] }));

  const getLabel = () => {
    switch (status) {
      case 'planning': return 'Planning Advisory...';
      case 'thinking': return 'Reasoning...';
      case 'writing': return 'Finalizing...';
      default: return 'Standing by...';
    }
  };

  return (
    <View style={[styles.row, { paddingHorizontal: Space.screenPadding }]}>
      <View style={[styles.iconWrap, { backgroundColor: colors.bgSurface }]}>
        <AnchorIcon size={14} color={Colors.amber} />
      </View>
      <View style={[styles.contentBlock, { backgroundColor: colors.bgSurface }]}>
        <View style={styles.dots}>
          <Animated.View style={[styles.dot, a1]} />
          <Animated.View style={[styles.dot, a2]} />
          <Animated.View style={[styles.dot, a3]} />
        </View>
        <Animated.View entering={FadeIn.duration(400)}>
          <Text style={[styles.statusText, { color: colors.text3 }]}>{getLabel()}</Text>
        </Animated.View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: Space.md,
    marginBottom: Space.messageGap,
  },
  iconWrap: {
    width: 24,
    height: 24,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'transparent',
    marginTop: 2,
  },
  contentBlock: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: Radius.lg,
    borderTopLeftRadius: Radius.xs,
  },
  dots: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
  },
  dot: {
    width: 4,
    height: 4,
    borderRadius: 2,
    backgroundColor: Colors.amber,
  },
  statusText: {
    fontFamily: Fonts.mono,
    fontSize: 11,
    letterSpacing: 0.1,
  },
});
