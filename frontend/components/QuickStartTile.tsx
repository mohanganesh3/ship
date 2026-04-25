/**
 * QuickStartTile v2 — 2-column horizontal layout with description
 *
 * Each tile: icon left, title + description right.
 * Full-width text, proper wrapping, no cramming.
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
} from 'react-native-reanimated';
import { Pressable } from 'react-native';
import { Colors, Fonts, Type, Space, Radius } from '../constants/theme';
import { useTheme } from '../providers/ThemeProvider';
import { EngineBlockIcon, LifebuoyIcon, CompassIcon, GearIcon } from './icons';

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

interface QuickStartTileProps {
  title: string;
  description: string;
  icon: string;
  onPress: () => void;
}

const ICONS: Record<string, React.FC<{ size?: number; color?: string }>> = {
  'engine-block': EngineBlockIcon,
  'lifebuoy': LifebuoyIcon,
  'compass': CompassIcon,
  'gear': GearIcon,
};

export function QuickStartTile({ title, description, icon, onPress }: QuickStartTileProps) {
  const { colors } = useTheme();
  const scale = useSharedValue(1);

  const animStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  const IconComponent = ICONS[icon] || CompassIcon;

  return (
    <AnimatedPressable
      onPress={onPress}
      onPressIn={() => { scale.value = withTiming(0.97, { duration: 80 }); }}
      onPressOut={() => { scale.value = withTiming(1, { duration: 80 }); }}
      style={[styles.tile, animStyle, { backgroundColor: colors.bgSurface, borderColor: colors.borderSubtle }]}
      accessibilityLabel={`${title}: ${description}`}
    >
      <View style={[styles.iconWrap, { backgroundColor: colors.bgElevated }]}>
        <IconComponent size={20} color={Colors.amber} />
      </View>
      <View style={styles.textCol}>
        <Text style={[styles.title, { color: colors.text1 }]}>{title}</Text>
        <Text style={[styles.desc, { color: colors.text3 }]} numberOfLines={2}>{description}</Text>
      </View>
    </AnimatedPressable>
  );
}

const styles = StyleSheet.create({
  tile: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: Radius.md,
    borderWidth: StyleSheet.hairlineWidth,
    padding: Space.lg,
    gap: Space.md,
  },
  iconWrap: {
    width: 40,
    height: 40,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  textCol: {
    flex: 1,
    gap: 2,
  },
  title: {
    fontFamily: Fonts.bodySemibold,
    fontSize: Type.sm.fontSize,
    lineHeight: Type.sm.lineHeight,
  },
  desc: {
    fontFamily: Fonts.body,
    fontSize: Type.xs.fontSize,
    lineHeight: Type.xs.lineHeight,
  },
});
