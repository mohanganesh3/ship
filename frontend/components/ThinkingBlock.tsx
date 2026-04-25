import { Ionicons } from '@expo/vector-icons';
import React, { useEffect, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import Animated, {
    Easing,
    useAnimatedStyle,
    useSharedValue,
    withRepeat,
    withSequence,
    withTiming,
} from 'react-native-reanimated';
import { Colors, Fonts, Radius, Space } from '../constants/theme';
import { useTheme } from '../providers/ThemeProvider';
import { MarkdownRenderer } from './MarkdownRenderer';

interface ThinkingBlockProps {
  content: string;
  thinkTime: number | null;
  isStreaming?: boolean;
  isThinking?: boolean;
}

export function ThinkingBlock({ content, thinkTime, isStreaming = false, isThinking = false }: ThinkingBlockProps) {
  const { colors } = useTheme();
  const [expanded, setExpanded] = useState(isStreaming);
  const pulse = useSharedValue(0.4);
  const glow = useSharedValue(0);
  const scrollRef = React.useRef<ScrollView>(null);

  useEffect(() => {
    if (isStreaming) {
      setExpanded(true);
      pulse.value = withRepeat(
        withSequence(
          withTiming(1, { duration: 1200, easing: Easing.bezier(0.4, 0, 0.2, 1) }),
          withTiming(0.4, { duration: 1200, easing: Easing.bezier(0.4, 0, 0.2, 1) })
        ),
        -1
      );
    } else {
      // Auto-collapse when finished (Claude style)
      setExpanded(false);
      pulse.value = withTiming(0.4, { duration: 500 });
      // Success flash when thinking ends
      glow.value = withSequence(
        withTiming(1, { duration: 300 }),
        withTiming(0, { duration: 800 })
      );
    }
  }, [isStreaming]);

  useEffect(() => {
    if (!isStreaming || !expanded) return;
    const id = requestAnimationFrame(() => {
      scrollRef.current?.scrollToEnd({ animated: false });
    });
    return () => cancelAnimationFrame(id);
  }, [content, expanded, isStreaming]);

  const pulseStyle = useAnimatedStyle(() => ({
    opacity: pulse.value,
  }));

  const glowStyle = useAnimatedStyle(() => ({
    shadowOpacity: glow.value * 0.5,
    shadowColor: Colors.amber,
    shadowRadius: glow.value * 10,
    backgroundColor: glow.value > 0 
      ? `rgba(212, 148, 58, ${glow.value * 0.08})` 
      : 'transparent',
  }));

  if (!content && !isStreaming) return null;

  const statusLabel = isStreaming
    ? (isThinking ? 'Optimizing Plan...' : 'Plan Ready')
    : (thinkTime ? `Reasoning Verified (${thinkTime.toFixed(1)}s)` : 'Advisory Reasoning');

  const streamingContent = formatStreamingThinking(content);

  return (
    <View style={styles.container}>
      <Pressable 
        onPress={() => !isStreaming && setExpanded(p => !p)} 
        disabled={isStreaming}
        style={({ pressed }) => [
          styles.header, 
          pressed && { opacity: 0.7 }
        ]}
      >
        <Animated.View style={[styles.labelRow, glowStyle]}>
          <Animated.View style={[styles.dot, pulseStyle]} />
          <Text style={[styles.label, { color: Colors.text3 }]}>
            {statusLabel}
          </Text>
          {!isStreaming && (
             <Ionicons 
               name={expanded ? "chevron-up" : "chevron-down"} 
               size={11} 
               color={Colors.text4} 
             />
          )}
        </Animated.View>
      </Pressable>

      {expanded && (content || isStreaming) ? (
        <View style={styles.contentWrapper}>
          <View style={[
            styles.glassCard,
            isStreaming && styles.streamingCard,
            { backgroundColor: colors.bgSurface, borderColor: colors.borderSubtle },
          ]}>
            {isStreaming ? (
              <ScrollView
                ref={scrollRef}
                style={styles.streamingScroll}
                contentContainerStyle={styles.streamingScrollContent}
                showsVerticalScrollIndicator={false}
                nestedScrollEnabled
              >
                <Text style={[styles.contentText, { color: colors.text3 }]}>
                  {streamingContent || 'Thinking…'}
                </Text>
              </ScrollView>
            ) : (
              <MarkdownRenderer content={content} color={colors.text3} />
            )}
          </View>
        </View>
      ) : null}
    </View>
  );
}

function formatStreamingThinking(content: string): string {
  return content
    .replace(/```[\s\S]*?```/g, '')
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/\*(.*?)\*/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/^[\-•]\s+/gm, '• ')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

const styles = StyleSheet.create({
  container: {
    marginBottom: Space.md,
  },
  header: {
    paddingVertical: Space.xs,
  },
  labelRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: Colors.amber,
  },
  label: {
    fontFamily: Fonts.mono,
    fontSize: 10,
    letterSpacing: 0.8,
    textTransform: 'uppercase',
  },
  contentWrapper: {
    marginTop: Space.xs,
    paddingLeft: 4,
  },
  glassCard: {
    padding: Space.md,
    borderRadius: Radius.sm,
    borderWidth: 1,
    borderLeftWidth: 3,
    borderLeftColor: Colors.amber,
    overflow: 'hidden',
  },
  streamingCard: {
    maxHeight: 180,
  },
  streamingScroll: {
    maxHeight: 160,
  },
  streamingScrollContent: {
    paddingBottom: 4,
  },
  contentText: {
    fontFamily: Fonts.mono,
    fontSize: 12,
    lineHeight: 19,
    opacity: 0.8,
  },
});
