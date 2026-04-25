/**
 * Chat Screen — thread-safe local chat with buffered streaming.
 *
 * Critical fixes applied:
 * 1. runAssistantTurnRef pattern: mode toggle no longer aborts an active
 *    generation by re-running the hydration effect.
 * 2. onComplete shows the message in the UI before DB writes; DB failure
 *    is non-fatal so the streaming state always resets correctly.
 * 3. Scroll-to-bottom after initial thread hydration.
 */
import { useLocalSearchParams, useRouter } from 'expo-router';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
    FlatList,
    KeyboardAvoidingView, Platform, Pressable,
    StyleSheet,
    Text,
    View,
} from 'react-native';
import { InputTray } from '../../components/InputTray';
import { MessageBubble, StreamingBubble } from '../../components/MessageBubble';
import { QuickActionChips } from '../../components/QuickActionChips';
import { ScreenHeader } from '../../components/ScreenHeader';
import { TypingIndicator } from '../../components/TypingIndicator';
import { MODEL_DISPLAY_NAME, THINK_MODE_COPY } from '../../constants/model';
import { Fonts, Space, Type } from '../../constants/theme';
import {
    addMessage as dbAddMessage,
    generateId,
    generateThreadTitle,
    getMessages,
    updateThreadPreview,
    updateThreadTitle,
} from '../../database/operations';
import { useTheme } from '../../providers/ThemeProvider';
import { logger } from '../../services/Logger';
import { abortGeneration, generateResponse, loadModel } from '../../services/modelBridge';
import { useAppStore } from '../../stores/appStore';
import { useChatStore, type Message } from '../../stores/chatStore';
import { useThreadStore } from '../../stores/threadStore';

const TAG = 'CHAT-SCREEN';

export default function ChatScreen() {
  const { threadId, autostart } = useLocalSearchParams<{ threadId: string; autostart?: string }>();
  const router = useRouter();
  const { colors } = useTheme();
  const flatListRef = useRef<FlatList>(null);
  const mountedRef = useRef(true);
  const activeRunIdRef = useRef(0);
  const autostartHandledRef = useRef<string | null>(null);
  const flushInterval = useRef<ReturnType<typeof setInterval> | null>(null);
  const scrollFrameRef = useRef<number | null>(null);
  const messagesRef = useRef<Message[]>([]);
  const contentBuf = useRef('');
  const thinkBuf = useRef('');
  const thinkTimeRef = useRef<number | null>(null);
  const writingStartedRef = useRef(false);
  const flushTickRef = useRef(0);
  const lastFlushedContentRef = useRef('');
  const lastFlushedThinkingRef = useRef('');
  const shouldAutoScrollRef = useRef(true);
  const pendingThinkModeOverrideRef = useRef<'think' | 'no_think' | null>(null);

  const {
    messages, setMessages, clearStream, setActiveThread,
  } = useChatStore();
  const { thinkMode, setThinkMode } = useAppStore();
  const updateThread = useThreadStore((state) => state.updateThread);
  const threadTitle = useThreadStore(
    (state) => state.threads.find((t) => t.id === threadId)?.title || MODEL_DISPLAY_NAME,
  );

  const [streamStatus, setStreamStatus] = useState<'planning' | 'thinking' | 'writing' | 'idle'>('idle');
  const [displayContent, setDisplayContent] = useState('');
  const [displayThinking, setDisplayThinking] = useState('');
  const [isStreamActive, setIsStreamActive] = useState(false);
  const [isThinkingActive, setIsThinkingActive] = useState(false);
  const [hasThinkingStarted, setHasThinkingStarted] = useState(false);
  const [thinkTimeSecs, setThinkTimeSecs] = useState<number | null>(null);
  const [inlineError, setInlineError] = useState<string | null>(null);
  const [isThreadHydrated, setIsThreadHydrated] = useState(false);

  const replaceMessages = useCallback((nextMessages: Message[]) => {
    messagesRef.current = nextMessages;
    setMessages(nextMessages);
  }, [setMessages]);

  const appendMessage = useCallback((message: Message) => {
    const nextMessages = [...messagesRef.current, message];
    messagesRef.current = nextMessages;
    setMessages(nextMessages);
  }, [setMessages]);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  const stopFlush = useCallback(() => {
    if (flushInterval.current) {
      clearInterval(flushInterval.current);
      flushInterval.current = null;
    }
    lastFlushedContentRef.current = contentBuf.current;
    lastFlushedThinkingRef.current = thinkBuf.current;
    setDisplayContent(contentBuf.current);
    setDisplayThinking(thinkBuf.current);
  }, []);

  const startFlush = useCallback(() => {
    if (flushInterval.current) clearInterval(flushInterval.current);
    flushTickRef.current = 0;
    flushInterval.current = setInterval(() => {
      const nextContent = contentBuf.current;
      const nextThinking = thinkBuf.current;

      if (nextContent !== lastFlushedContentRef.current) {
        lastFlushedContentRef.current = nextContent;
        setDisplayContent(nextContent);
      }
      if (nextThinking !== lastFlushedThinkingRef.current) {
        lastFlushedThinkingRef.current = nextThinking;
        setDisplayThinking(nextThinking);
      }

      flushTickRef.current += 1;
      if ((nextContent || nextThinking) && shouldAutoScrollRef.current && flushTickRef.current % 5 === 0) {
        requestAnimationFrame(() => {
          flatListRef.current?.scrollToEnd({ animated: false });
        });
      }
    }, 100);
  }, []);

  const clearBuffers = useCallback(() => {
    contentBuf.current = '';
    thinkBuf.current = '';
    thinkTimeRef.current = null;
    writingStartedRef.current = false;
    flushTickRef.current = 0;
    lastFlushedContentRef.current = '';
    lastFlushedThinkingRef.current = '';
    setDisplayContent('');
    setDisplayThinking('');
    setThinkTimeSecs(null);
    setHasThinkingStarted(false);
  }, []);

  const resetStreamingUi = useCallback(() => {
    stopFlush();
    clearBuffers();
    setIsStreamActive(false);
    setIsThinkingActive(false);
    setStreamStatus('idle');
  }, [clearBuffers, stopFlush]);

  const scrollToBottom = useCallback((animated = true) => {
    if (scrollFrameRef.current !== null) return;
    scrollFrameRef.current = requestAnimationFrame(() => {
      scrollFrameRef.current = null;
      flatListRef.current?.scrollToEnd({ animated });
    });
  }, []);

  const getCurrentThreadHistory = useCallback((source: Message[]): Message[] => (
    source.filter((m) => m.threadId === threadId)
  ), [threadId]);

  const runAssistantTurn = useCallback(async (historyMessages: Message[]) => {
    if (!threadId) return;

    const runId = ++activeRunIdRef.current;
    const effectiveThinkMode = pendingThinkModeOverrideRef.current ?? thinkMode;
    pendingThinkModeOverrideRef.current = null;
    let didComplete = false;
    let errorMessage: string | null = null;

    setInlineError(null);
    clearBuffers();
    shouldAutoScrollRef.current = true;
    setIsThinkingActive(false);
    setIsStreamActive(true);
    setStreamStatus('planning');
    writingStartedRef.current = false;
    scrollToBottom(false);

    const shouldShowThinking = effectiveThinkMode === 'think';

    try {
      await loadModel();

      const scopedHistory = getCurrentThreadHistory(historyMessages);

      await generateResponse({
        messages: scopedHistory.map((m) => ({ role: m.role, content: m.content })),
        thinkMode: effectiveThinkMode,
        onToken: (token) => {
          if (!mountedRef.current || activeRunIdRef.current !== runId) return;
          contentBuf.current += token;
          if (!writingStartedRef.current) {
            writingStartedRef.current = true;
            setStreamStatus('writing');
          }
        },
        onThinkToken: shouldShowThinking
          ? (token) => {
            if (!mountedRef.current || activeRunIdRef.current !== runId) return;
            thinkBuf.current += token;
          }
          : undefined,
        onThinkStart: shouldShowThinking
          ? () => {
            if (!mountedRef.current || activeRunIdRef.current !== runId) return;
            setHasThinkingStarted(true);
            setIsThinkingActive(true);
            setStreamStatus('thinking');
          }
          : undefined,
        onThinkEnd: (duration) => {
          if (!mountedRef.current || activeRunIdRef.current !== runId) return;
          if (shouldShowThinking) {
            thinkTimeRef.current = duration;
            setIsThinkingActive(false);
            setThinkTimeSecs(duration);
          }
          if (!writingStartedRef.current) {
            writingStartedRef.current = true;
          }
          setStreamStatus('writing');
        },
        onComplete: (tokenCount) => {
          if (!mountedRef.current || activeRunIdRef.current !== runId) return;

          const finalContent = sanitizeAssistantOutput(contentBuf.current.trim());
          const finalThinking = shouldShowThinking ? thinkBuf.current.trim() : '';

          if (!finalContent) {
            if (finalThinking && effectiveThinkMode === 'think') {
              // Model burned all tokens on reasoning — silently retry in Direct mode.
              // setTimeout ensures modelBridge's finally block has released isGenerating
              // before the new generation starts.
              pendingThinkModeOverrideRef.current = 'no_think';
              resetStreamingUi();
              const capturedRunId = runId;
              setTimeout(() => {
                if (!mountedRef.current || activeRunIdRef.current !== capturedRunId) return;
                runAssistantTurnRef.current(getCurrentThreadHistory(messagesRef.current));
              }, 80);
              return;
            }
            errorMessage = 'No response received. Tap Retry or check model status.';
            return;
          }

          didComplete = true;

          const aiMsg: Message = {
            id: generateId(),
            threadId,
            role: 'assistant',
            content: finalContent,
            thinking: finalThinking || null,
            thinkTime: thinkTimeRef.current,
            tokensUsed: tokenCount,
            createdAt: Date.now(),
            hasSafety: detectSafety(finalContent),
          };

          // Show message in UI immediately — DB persistence is non-fatal.
          appendMessage(aiMsg);
          resetStreamingUi();
          scrollToBottom();

          // Persist asynchronously so a DB error never leaves the UI stuck.
          (async () => {
            try {
              await dbAddMessage(aiMsg);
              await updateThreadPreview(threadId, finalContent.substring(0, 80));
              updateThread(threadId, { preview: finalContent.substring(0, 80) });
            } catch (dbErr) {
              logger.error(TAG, 'Failed to persist assistant message', dbErr);
            }
          })();
        },
        onError: (errMsg) => {
          errorMessage = errMsg;
        },
      });
    } catch (error: any) {
      errorMessage = errorMessage || error?.message || 'Inference failed';
      logger.error(TAG, 'Assistant turn failed', error);
    } finally {
      if (!mountedRef.current || activeRunIdRef.current !== runId) return;
      if (!didComplete) {
        resetStreamingUi();
        if (errorMessage) setInlineError(errorMessage);
      }
    }
  }, [appendMessage, clearBuffers, getCurrentThreadHistory, resetStreamingUi, scrollToBottom, thinkMode, threadId, updateThread]);

  // Keep a stable ref to the latest runAssistantTurn so the hydration effect
  // never needs runAssistantTurn itself as a dependency. Without this, toggling
  // Think/Direct mode would re-run the hydration effect and abort an active
  // generation mid-response.
  const runAssistantTurnRef = useRef(runAssistantTurn);
  runAssistantTurnRef.current = runAssistantTurn;

  const retryLastTurn = useCallback(async () => {
    const lastMsg = messagesRef.current[messagesRef.current.length - 1];
    if (lastMsg?.role !== 'user') return;
    setInlineError(null);
    await runAssistantTurnRef.current([...messagesRef.current]);
  }, []);

  const handleAbort = useCallback(async () => {
    activeRunIdRef.current += 1;
    await abortGeneration().catch(() => {});
    resetStreamingUi();
    setInlineError('Response stopped. Tap Retry or send a new message.');
  }, [resetStreamingUi]);

  // Mount / unmount
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (scrollFrameRef.current !== null) {
        cancelAnimationFrame(scrollFrameRef.current);
        scrollFrameRef.current = null;
      }
    };
  }, []);

  // Manage flush interval when streaming state changes
  useEffect(() => {
    if (isStreamActive) {
      startFlush();
    } else {
      stopFlush();
    }
    // startFlush/stopFlush are stable (no deps), so this only fires on isStreamActive.
  }, [isStreamActive, startFlush, stopFlush]);

  // Thread hydration — depends only on threadId/autostart, NOT on runAssistantTurn.
  // Using the ref means mode changes don't abort ongoing generations.
  useEffect(() => {
    if (!threadId) return;

    let cancelled = false;
    setIsThreadHydrated(false);
    replaceMessages([]);
    setInlineError(null);
    setActiveThread(threadId);
    loadModel().catch((err) => logger.error(TAG, 'Background model load failed', err));

    const hydrateThread = async () => {
      const loadedMessages = await getMessages(threadId, 80);
      if (cancelled || !mountedRef.current) return;

      replaceMessages(loadedMessages);
      setIsThreadHydrated(true);

      // Scroll to the bottom of the loaded history
      requestAnimationFrame(() => {
        flatListRef.current?.scrollToEnd({ animated: false });
      });

      const lastMsg = loadedMessages[loadedMessages.length - 1];
      const shouldAutostart =
        autostartHandledRef.current !== threadId &&
        lastMsg?.role === 'user' &&
        (autostart === '1' || loadedMessages.length === 1);

      if (shouldAutostart) {
        autostartHandledRef.current = threadId;
        await runAssistantTurnRef.current(loadedMessages);
      }
    };

    hydrateThread().catch((err) => logger.error(TAG, 'Thread hydration failed', err));

    return () => {
      cancelled = true;
      activeRunIdRef.current += 1;
      setIsThreadHydrated(false);
      abortGeneration().catch(() => {});
      clearStream();
      resetStreamingUi();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [threadId, autostart]);

  const handleSend = useCallback(async (text: string) => {
    if (!threadId || isStreamActive || !isThreadHydrated) return;

    logger.info(TAG, `Sending: ${text.substring(0, 48)}…`);

    const isFirstTurn = messagesRef.current.length === 0;
    const userMsg: Message = {
      id: generateId(),
      threadId,
      role: 'user',
      content: text,
      thinking: null,
      thinkTime: null,
      tokensUsed: null,
      createdAt: Date.now(),
      hasSafety: false,
    };

    appendMessage(userMsg);

    (async () => {
      try {
        await dbAddMessage(userMsg);
        await updateThreadPreview(threadId, text);
        updateThread(threadId, { preview: text.substring(0, 80) });
        if (isFirstTurn) {
          const title = generateThreadTitle(text);
          await updateThreadTitle(threadId, title);
          updateThread(threadId, { title });
        }
      } catch (dbErr) {
        logger.error(TAG, 'Failed to persist user message', dbErr);
      }
    })();

    await runAssistantTurnRef.current(getCurrentThreadHistory(messagesRef.current));
  }, [appendMessage, getCurrentThreadHistory, isStreamActive, isThreadHydrated, threadId, updateThread]);

  const renderMessage = useCallback(
    ({ item }: { item: Message }) => <MessageBubble message={item} />,
    [],
  );

  const showStreaming = isStreamActive && (
    displayContent.length > 0 ||
    displayThinking.length > 0 ||
    hasThinkingStarted
  );
  const showTypingDots = isStreamActive && !showStreaming;
  const canRetryLastTurn = !isStreamActive && messages[messages.length - 1]?.role === 'user';
  const modeCopy = THINK_MODE_COPY[thinkMode];

  const footerComponent = useMemo(() => (
    <>
      {showTypingDots && <TypingIndicator status={streamStatus} />}
      {showStreaming && (
        <StreamingBubble
          content={displayContent}
          thinking={displayThinking}
          isThinking={isThinkingActive}
          isStreamActive={isStreamActive}
          hasThinking={hasThinkingStarted || displayThinking.length > 0}
          thinkTime={thinkTimeSecs}
        />
      )}
    </>
  ), [
    displayContent,
    displayThinking,
    hasThinkingStarted,
    isStreamActive,
    isThinkingActive,
    showStreaming,
    showTypingDots,
    streamStatus,
    thinkTimeSecs,
  ]);

  return (
    <KeyboardAvoidingView
      style={[styles.container, { backgroundColor: colors.bgPage }]}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={0}
    >
      <ScreenHeader title={threadTitle} onBack={() => router.back()} showStatus />

      <FlatList
        ref={flatListRef}
        data={messages}
        renderItem={renderMessage}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.list}
        ListFooterComponent={footerComponent}
        keyboardShouldPersistTaps="handled"
        maxToRenderPerBatch={8}
        windowSize={5}
        onScroll={(e) => {
          const { contentOffset, contentSize, layoutMeasurement } = e.nativeEvent;
          const nearBottom = contentOffset.y + layoutMeasurement.height >= contentSize.height - 120;
          shouldAutoScrollRef.current = nearBottom;
        }}
        scrollEventThrottle={16}
      />

      {!isStreamActive && messages.length > 0 && (
        <QuickActionChips onPress={handleSend} disabled={!isThreadHydrated} />
      )}

      <View style={[styles.toolbar, { borderTopColor: colors.borderSubtle }]}>
        <Pressable
          onPress={() => setThinkMode(thinkMode === 'think' ? 'no_think' : 'think')}
          style={({ pressed }) => [
            styles.toolbarPill,
            {
              backgroundColor: colors.bgSurface,
              borderColor: thinkMode === 'think' ? colors.borderMedium : colors.borderSubtle,
              opacity: pressed ? 0.75 : 1,
            },
          ]}
        >
          <Text style={[styles.toolbarLabel, { color: colors.text2 }]}>Mode</Text>
          <Text style={[styles.toolbarValue, { color: colors.text1 }]}>{modeCopy.label}</Text>
        </Pressable>

        <Text style={[styles.toolbarHint, { color: colors.text4 }]} numberOfLines={1}>
          {modeCopy.hint}
        </Text>

        {isStreamActive ? (
          <Pressable
            onPress={() => void handleAbort()}
            style={({ pressed }) => [
              styles.toolbarAction,
              { backgroundColor: colors.bgSurface, borderColor: colors.borderSubtle, opacity: pressed ? 0.75 : 1 },
            ]}
          >
            <Text style={[styles.toolbarActionText, { color: colors.text1 }]}>Stop</Text>
          </Pressable>
        ) : canRetryLastTurn ? (
          <Pressable
            onPress={() => void retryLastTurn()}
            style={({ pressed }) => [
              styles.toolbarAction,
              { backgroundColor: colors.bgSurface, borderColor: colors.borderSubtle, opacity: pressed ? 0.75 : 1 },
            ]}
          >
            <Text style={[styles.toolbarActionText, { color: colors.text1 }]}>Retry</Text>
          </Pressable>
        ) : null}
      </View>

      {inlineError && (
        <View style={[styles.errorWrap, { borderColor: colors.borderSubtle, backgroundColor: colors.bgSurface }]}>
          <Text style={[styles.errorText, { color: colors.text2 }]}>{inlineError}</Text>
          {canRetryLastTurn && (
            <Pressable onPress={() => void retryLastTurn()} style={styles.errorAction}>
              <Text style={[styles.errorActionText, { color: colors.text1 }]}>Retry last turn</Text>
            </Pressable>
          )}
        </View>
      )}

      <InputTray
        onSend={handleSend}
        disabled={isStreamActive || !isThreadHydrated}
        placeholder="Ask Maritime AI…"
      />
    </KeyboardAvoidingView>
  );
}

function detectSafety(content: string): boolean {
  void content;
  return false;
}

function sanitizeAssistantOutput(content: string): string {
  return String(content || '').trim();
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  list: {
    paddingTop: Space.lg,
    paddingBottom: Space.xl,
  },
  toolbar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.sm,
    paddingHorizontal: Space.screenPadding,
    paddingTop: Space.sm,
    borderTopWidth: StyleSheet.hairlineWidth,
  },
  toolbarPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 7,
  },
  toolbarLabel: {
    fontFamily: Fonts.body,
    fontSize: Type.xs.fontSize,
  },
  toolbarValue: {
    fontFamily: Fonts.bodySemibold,
    fontSize: Type.sm.fontSize,
  },
  toolbarHint: {
    flex: 1,
    fontFamily: Fonts.body,
    fontSize: Type.xs.fontSize,
  },
  toolbarAction: {
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 7,
  },
  toolbarActionText: {
    fontFamily: Fonts.bodySemibold,
    fontSize: Type.xs.fontSize,
  },
  errorWrap: {
    marginHorizontal: Space.screenPadding,
    marginBottom: Space.sm,
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: 12,
    paddingHorizontal: Space.md,
    paddingVertical: Space.sm,
  },
  errorText: {
    fontFamily: Fonts.body,
    fontSize: Type.sm.fontSize,
    lineHeight: Type.sm.lineHeight,
  },
  errorAction: {
    marginTop: Space.xs,
    alignSelf: 'flex-start',
    paddingVertical: 4,
  },
  errorActionText: {
    fontFamily: Fonts.bodySemibold,
    fontSize: Type.xs.fontSize,
  },
});
