import React from 'react';
import { ScrollView, Pressable, Text, StyleSheet } from 'react-native';
import { Colors, Fonts, Type, Space, Radius } from '../constants/theme';
import { useTheme } from '../providers/ThemeProvider';

interface QuickActionChipsProps {
  onPress: (text: string) => void;
  disabled?: boolean;
}

const CHIPS = [
  "Scavenge fire procedure",
  "MARPOL ECA limits",
  "Lifeboat drill frequency",
  "Fuel leak in purifier",
  "ISPS Security Level 2",
];

export function QuickActionChips({ onPress, disabled }: QuickActionChipsProps) {
  const { colors, isDark } = useTheme();

  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.container}
      style={styles.scroll}
    >
      {CHIPS.map((chip, i) => (
        <Pressable
          key={i}
          onPress={() => onPress(chip)}
          disabled={disabled}
          style={({ pressed }) => [
            styles.chip,
            {
              backgroundColor: isDark ? colors.bgSurface : Colors.lightBg2,
              borderColor: colors.borderSubtle,
              opacity: disabled ? 0.6 : pressed ? 0.7 : 1,
            }
          ]}
        >
          <Text style={[styles.text, { color: colors.text2 }]}>{chip}</Text>
        </Pressable>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: {
    maxHeight: 48,
  },
  container: {
    paddingHorizontal: Space.screenPadding,
    gap: Space.sm,
    alignItems: 'center',
    height: 48,
  },
  chip: {
    paddingHorizontal: Space.md,
    paddingVertical: 6,
    borderRadius: Radius.lg,
    borderWidth: 1,
  },
  text: {
    fontFamily: Fonts.body,
    fontSize: 13,
  },
});
