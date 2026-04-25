import * as Haptics from 'expo-haptics';
import React, { useCallback, useEffect } from 'react';
import { Alert, Platform, Pressable, Share, StyleSheet, Text, View } from 'react-native';
import Animated, {
    FadeIn,
    useAnimatedStyle,
    useSharedValue,
    withRepeat,
    withSequence,
    withTiming,
} from 'react-native-reanimated';
import { Colors, Fonts, Radius, Space, Type } from '../constants/theme';
import { useTheme } from '../providers/ThemeProvider';
import type { Message } from '../stores/chatStore';
import { MarkdownRenderer } from './MarkdownRenderer';
import { ThinkingBlock } from './ThinkingBlock';
import { AnchorIcon, CopyIcon, RefreshIcon } from './icons';

// ── MessageBubble (finalized message) ─────────────────────────────────────
interface MessageBubbleProps { message: Message; onRegenerate?: () => void; }

export const MessageBubble = React.memo(function MessageBubble({ message, onRegenerate }: MessageBubbleProps) {
  const { colors } = useTheme();
  const isUser = message.role === 'user';

  const handleCopy = useCallback(async () => {
    if (Platform.OS !== 'web') {
      try {
        const impactAsync = (Haptics as any)?.impactAsync;
        const feedback = (Haptics as any)?.ImpactFeedbackStyle?.Light;
        if (impactAsync && feedback != null) {
          await impactAsync(feedback);
        }
      } catch {}
    }
    try {
      await Share.share({ message: message.content });
    } catch {
      Alert.alert('Copy failed', 'Could not copy the message.');
    }
  }, [message.content]);

  if (isUser) {
    return (
      <Animated.View entering={FadeIn.duration(200)} style={styles.userRow}>
        <View style={[styles.userBubble, { backgroundColor: colors.bgUserBubble }]}>
          <Text style={[styles.userText, { color: colors.text1 }]}>{message.content}</Text>
        </View>
      </Animated.View>
    );
  }

  return (
    <Animated.View entering={FadeIn.duration(300)} style={styles.aiRow}>
      <View style={styles.aiIconCol}>
        <View style={[styles.aiIcon, { backgroundColor: colors.bgSurface, borderColor: colors.borderSubtle, borderWidth: 1 }]}>
          <AnchorIcon size={14} color={Colors.amber} />
        </View>
      </View>

      <View style={styles.aiContentCol}>
        {message.thinking && (
          <ThinkingBlock
            content={message.thinking}
            thinkTime={message.thinkTime}
            isStreaming={false}
          />
        )}
        <View style={styles.markdownContainer}>
          <MarkdownRenderer content={message.content} />
        </View>

        <View style={styles.actions}>
          {message.tokensUsed != null && (
            <View style={[styles.tokenBadge, { backgroundColor: colors.bgSurface, borderColor: colors.borderSubtle }]}>
              <Text style={[styles.tokenText, { color: colors.text4 }]}>
                {message.tokensUsed} tokens
              </Text>
            </View>
          )}
          <View style={{ flex: 1 }} />
          <View style={styles.actionRow}>
            <Pressable
              onPress={handleCopy}
              style={({ pressed }) => [styles.actionBtn, { borderColor: colors.borderSubtle, opacity: pressed ? 0.6 : 1 }]}
              accessibilityLabel="Copy message"
            >
              <CopyIcon size={12} color={colors.text3} />
            </Pressable>
            {onRegenerate && (
              <Pressable
                onPress={onRegenerate}
                style={({ pressed }) => [styles.actionBtn, { borderColor: colors.borderSubtle, opacity: pressed ? 0.6 : 1 }]}
                accessibilityLabel="Regenerate response"
              >
                <RefreshIcon size={12} color={colors.text3} />
              </Pressable>
            )}
          </View>
        </View>
      </View>
    </Animated.View>
  );
});

// ── Animated Caret ─────────────────────────────────────────────────────────
const AnimatedCaret = () => {
  const { colors } = useTheme();
  const opacity = useSharedValue(1);

  useEffect(() => {
    opacity.value = withRepeat(
      withSequence(
        withTiming(0, { duration: 400 }),
        withTiming(1, { duration: 400 }),
      ),
      -1,
    );
  // shared value ref is stable — intentionally empty deps
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const style = useAnimatedStyle(() => ({
    opacity: opacity.value,
    backgroundColor: Colors.amber,
    width: 8,
    height: 18,
    marginLeft: 4,
    borderRadius: 1,
  }));

  return <Animated.View style={style} />;
};

// ── StreamingBubble (in-flight response) ──────────────────────────────────
export function StreamingBubble({
  content,
  thinking,
  isThinking,
  isStreamActive,
  hasThinking,
  thinkTime,
}: {
  content: string;
  thinking: string;
  isThinking: boolean;
  isStreamActive: boolean;
  hasThinking: boolean;
  thinkTime: number | null;
}) {
  const { colors } = useTheme();

  return (
    <View style={styles.aiRow}>
      <View style={styles.aiIconCol}>
        <View style={[styles.aiIcon, { backgroundColor: colors.bgSurface, borderColor: colors.borderSubtle, borderWidth: 1 }]}>
          <AnchorIcon size={14} color={Colors.amber} />
        </View>
      </View>
      <View style={styles.aiContentCol}>
        {hasThinking && (
          <ThinkingBlock
            content={thinking}
            thinkTime={thinkTime}
            isStreaming={isStreamActive}
            isThinking={isThinking}
          />
        )}

        {content.length > 0 && (
          <View style={styles.streamRow}>
            <Text style={[styles.bodyText, { color: colors.text1 }]}>{content}</Text>
            {!isThinking && <AnimatedCaret />}
          </View>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  userRow: {
    alignItems: 'flex-end',
    paddingHorizontal: Space.screenPadding,
    marginBottom: Space.messageGap,
  },
  userBubble: {
    maxWidth: '78%',
    paddingVertical: Space.md,
    paddingHorizontal: Space.lg,
    borderRadius: Radius.lg,
    borderBottomRightRadius: Radius.xs,
  },
  userText: {
    fontFamily: Fonts.body,
    fontSize: Type.base.fontSize,
    lineHeight: Type.base.lineHeight,
  },
  aiRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingHorizontal: Space.screenPadding,
    marginBottom: Space.messageGap,
    gap: Space.md,
  },
  aiIconCol: { paddingTop: 2 },
  aiIcon: {
    width: 24,
    height: 24,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  aiContentCol: {
    flex: 1,
    maxWidth: 680,
  },
  markdownContainer: {
    marginTop: 6,
  },
  bodyText: {
    fontFamily: Fonts.body,
    fontSize: Type.base.fontSize,
    lineHeight: Type.base.lineHeight,
    flexShrink: 1,
  },
  streamRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'flex-end',
  },
  tokenBadge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
    borderWidth: 1,
  },
  tokenText: {
    fontFamily: Fonts.mono,
    fontSize: 10,
    letterSpacing: 0.2,
  },
  actions: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: Space.sm,
    gap: Space.md,
  },
  actionRow: {
    flexDirection: 'row',
    gap: Space.xs,
  },
  actionBtn: {
    width: 32,
    height: 32,
    borderRadius: 8,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
