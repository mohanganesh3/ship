/**
 * ThreadListItem v2 — Cleaner, no inline action buttons
 *
 * Actions (pin/delete) are conceptual swipe actions.
 * Main view: title + preview + time. Pinned = tiny amber dot.
 */
import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { Colors, Fonts, Type, Space } from '../constants/theme';
import { useTheme } from '../providers/ThemeProvider';
import type { Thread } from '../stores/threadStore';

interface ThreadListItemProps {
  thread: Thread;
  index: number;
  onPress: (thread: Thread) => void;
}

export const ThreadListItem = React.memo(function ThreadListItem({
  thread,
  index,
  onPress,
}: ThreadListItemProps) {
  const { colors } = useTheme();

  return (
    <Animated.View entering={FadeInDown.duration(200).delay(index * 40)}>
      <Pressable
        onPress={() => onPress(thread)}
        style={({ pressed }) => [
          styles.row,
          { borderBottomColor: colors.borderSubtle },
          pressed && { backgroundColor: colors.bgSurface },
        ]}
        accessibilityLabel={`Conversation: ${thread.title}`}
      >
        {/* Pin indicator */}
        {thread.pinned && <View style={styles.pinDot} />}

        <View style={styles.textCol}>
          <Text style={[styles.title, { color: colors.text1 }]} numberOfLines={1}>
            {thread.title}
          </Text>
          <Text style={[styles.preview, { color: colors.text3 }]} numberOfLines={1}>
            {thread.preview || 'No messages yet'}
          </Text>
        </View>

        <Text style={[styles.time, { color: colors.text4 }]}>
          {formatRelativeTime(thread.updatedAt)}
        </Text>
      </Pressable>
    </Animated.View>
  );
});

export function DateSeparator({ label }: { label: string }) {
  const { colors } = useTheme();
  return (
    <View style={styles.separator}>
      <Text style={[styles.sepText, { color: colors.text4 }]}>{label}</Text>
    </View>
  );
}

export function getDateGroup(timestamp: number): string {
  const now = new Date();
  const date = new Date(timestamp);
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  if (date >= today) return 'Today';
  if (date >= yesterday) return 'Yesterday';
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function formatRelativeTime(ts: number): string {
  const diff = Date.now() - ts;
  const m = Math.floor(diff / 60000);
  const h = Math.floor(diff / 3600000);
  const d = Math.floor(diff / 86400000);
  if (m < 1) return 'Now';
  if (m < 60) return `${m}m`;
  if (h < 24) return `${h}h`;
  if (d === 1) return 'Yesterday';
  if (d < 7) return `${d}d`;
  return new Date(ts).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: Space.screenPadding,
    paddingVertical: 14,
    borderBottomWidth: StyleSheet.hairlineWidth,
    gap: Space.md,
  },
  pinDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: Colors.amber,
  },
  textCol: {
    flex: 1,
    gap: 3,
  },
  title: {
    fontFamily: Fonts.bodySemibold,
    fontSize: Type.md.fontSize,
    lineHeight: Type.md.lineHeight,
  },
  preview: {
    fontFamily: Fonts.body,
    fontSize: Type.sm.fontSize,
    lineHeight: Type.sm.lineHeight,
  },
  time: {
    fontFamily: Fonts.body,
    fontSize: Type.xs.fontSize,
  },
  separator: {
    paddingHorizontal: Space.screenPadding,
    paddingTop: Space.xl,
    paddingBottom: Space.sm,
  },
  sepText: {
    fontFamily: Fonts.bodySemibold,
    fontSize: Type.xs.fontSize,
    letterSpacing: 0.5,
    textTransform: 'uppercase',
  },
});
