/**
 * ScreenHeader v2 — Simpler, no mono text in chrome
 */
import React, { useEffect } from 'react';
import { Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import Animated, {
    Easing,
    useAnimatedStyle,
    useSharedValue,
    withRepeat,
    withTiming,
} from 'react-native-reanimated';
import { Colors, Fonts, Space, Type } from '../constants/theme';
import { useTheme } from '../providers/ThemeProvider';
import { useAppStore } from '../stores/appStore';
import { AnchorIcon, ChevronLeftIcon } from './icons';

interface ScreenHeaderProps {
  title: string;
  onBack?: () => void;
  showStatus?: boolean;
}

export function ScreenHeader({ title, onBack, showStatus = false }: ScreenHeaderProps) {
  const { colors } = useTheme();
  const modelStatus = useAppStore(s => s.modelStatus);
  const pulse = useSharedValue(1);
  const rotation = useSharedValue(0);

  useEffect(() => {
    const shouldAnimate = modelStatus === 'loading' || modelStatus === 'active';

    if (shouldAnimate) {
      pulse.value = withRepeat(
        withTiming(0.3, { duration: 900, easing: Easing.inOut(Easing.ease) }),
        -1,
        true,
      );

      rotation.value = 0;
      rotation.value = withRepeat(
        withTiming(360, { duration: 2600, easing: Easing.linear }),
        -1,
        false,
      );
    } else {
      pulse.value = 1;
      rotation.value = 0;
    }
  }, [modelStatus]);

  const dotAnim = useAnimatedStyle(() => ({
    opacity: modelStatus === 'loading' ? pulse.value : 1,
  }));

  const radarAnim = useAnimatedStyle(() => ({
    transform: [{ rotate: `${rotation.value}deg` }],
    opacity: modelStatus === 'error' ? 0.7 : 1,
  }));

  const statusColor = modelStatus === 'active' ? Colors.success : Colors.amber;

  return (
    <View style={[styles.container, { backgroundColor: colors.bgPage, borderBottomColor: colors.borderSubtle }]}>
      <View style={styles.left}>
        {onBack && (
          <Pressable onPress={onBack} style={styles.backBtn} hitSlop={12}>
            <ChevronLeftIcon size={22} color={colors.text1} />
          </Pressable>
        )}
        <Text style={[styles.title, { color: colors.text1 }]} numberOfLines={1}>
          {title}
        </Text>
      </View>
      {showStatus && (
        <View style={styles.statusWrap}>
          <View style={[styles.radarBaseRing, { borderColor: statusColor }]} />
          <Animated.View style={[styles.radarSweep, radarAnim]}>
            <View style={[styles.sweepArc, { borderTopColor: statusColor }]} />
          </Animated.View>
          <View style={[styles.centerMarker, { backgroundColor: colors.bgPage }]}> 
            <AnchorIcon size={10} color={statusColor} />
          </View>
          <Animated.View style={[styles.statusDot, { backgroundColor: statusColor }, dotAnim]} />
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: Space.screenPadding,
    paddingTop: Platform.OS === 'web' ? Space.lg : 54,
    paddingBottom: Space.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  left: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
    gap: Space.sm,
  },
  backBtn: {
    width: Space.tapTarget,
    height: Space.tapTarget,
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: -Space.sm,
  },
  title: {
    fontFamily: Fonts.bodySemibold,
    fontSize: Type.lg.fontSize,
    lineHeight: Type.lg.lineHeight,
    flex: 1,
  },
  statusDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    position: 'absolute',
    top: 6,
    left: 6,
  },
  statusWrap: {
    width: 20,
    height: 20,
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
  },
  radarBaseRing: {
    width: 18,
    height: 18,
    borderRadius: 9,
    borderWidth: 1,
    opacity: 0.28,
    position: 'absolute',
  },
  centerMarker: {
    width: 12,
    height: 12,
    borderRadius: 6,
    alignItems: 'center',
    justifyContent: 'center',
    position: 'absolute',
    zIndex: 3,
  },
  radarSweep: {
    width: 18,
    height: 18,
    borderRadius: 9,
    position: 'absolute',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1,
  },
  sweepArc: {
    width: 18,
    height: 18,
    borderRadius: 9,
    borderWidth: 1.5,
    borderColor: 'transparent',
    opacity: 0.9,
  },
});
