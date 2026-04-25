/**
 * New Chat v2 — Simpler greeting, 2-column tiles with descriptions
 *
 * Removed: wave icon, heavy maritime theming
 * Kept: anchor icon (smaller, gentler sway), greeting, quick-start tiles
 */
import React, { useState, useCallback } from 'react';
import { View, Text, ScrollView, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import Animated, {
  FadeIn,
} from 'react-native-reanimated';
import { Colors, Fonts, Type, Space, QuickStartCategories } from '../../constants/theme';
import { useTheme } from '../../providers/ThemeProvider';
import { QuickStartTile } from '../../components/QuickStartTile';
import { InputTray } from '../../components/InputTray';
import { AnchorIcon } from '../../components/icons';
import { createThread, generateThreadTitle, addMessage, updateThreadPreview } from '../../database/operations';
import { useThreadStore } from '../../stores/threadStore';
import { type Message } from '../../stores/chatStore';
import { generateId } from '../../database/operations';

export default function NewChatScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const { addThread } = useThreadStore();
  const [inputValue, setInputValue] = useState('');

  const handleSend = useCallback(async (text: string) => {
    const thread = await createThread(generateThreadTitle(text));
    addThread(thread);
    const userMsg: Message = {
      id: generateId(),
      threadId: thread.id,
      role: 'user',
      content: text,
      thinking: null,
      thinkTime: null,
      tokensUsed: null,
      createdAt: Date.now(),
      hasSafety: false,
    };
    await addMessage(userMsg);
    await updateThreadPreview(thread.id, text);
    router.push({
      pathname: '/chat/[threadId]',
      params: { threadId: thread.id, autostart: '1' },
    });
  }, []);

  return (
    <View style={[styles.container, { backgroundColor: colors.bgPage }]}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        {/* Anchor */}
        <Animated.View entering={FadeIn.delay(100).duration(500)} style={styles.anchorWrap}>
          <AnchorIcon size={40} color={Colors.amber} />
        </Animated.View>

        {/* Greeting */}
        <Animated.View entering={FadeIn.delay(250).duration(400)}>
          <Text style={[styles.greeting, { color: colors.text1 }]}>
            What can I help with?
          </Text>
          <Text style={[styles.subtitle, { color: colors.text3 }]}>
            Ask about engines, regulations, or safety procedures
          </Text>
        </Animated.View>

        {/* Quick-start tiles — 2 column */}
        <Animated.View entering={FadeIn.delay(400).duration(400)} style={styles.tiles}>
          {QuickStartCategories.map(cat => (
            <QuickStartTile
              key={cat.id}
              title={cat.title}
              description={cat.description}
              icon={cat.icon}
              onPress={() => setInputValue(cat.prompt)}
            />
          ))}
        </Animated.View>
      </ScrollView>

      <InputTray onSend={handleSend} initialValue={inputValue} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: Space.screenPadding,
    paddingTop: 80,
    paddingBottom: Space.lg,
  },
  anchorWrap: {
    marginBottom: Space['2xl'],
  },
  greeting: {
    fontFamily: Fonts.display,
    fontSize: Type['2xl'].fontSize,
    lineHeight: Type['2xl'].lineHeight,
    textAlign: 'center',
    letterSpacing: -0.3,
  },
  subtitle: {
    fontFamily: Fonts.body,
    fontSize: Type.sm.fontSize,
    lineHeight: Type.sm.lineHeight,
    textAlign: 'center',
    marginTop: Space.sm,
    marginBottom: Space['2xl'],
  },
  tiles: {
    width: '100%',
    maxWidth: 440,
    gap: Space.md,
  },
});
