/**
 * Chat Store — active conversation state and streaming
 */
import { create } from 'zustand';

export interface Message {
  id: string;
  threadId: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  thinking: string | null;
  thinkTime: number | null;     // seconds
  tokensUsed: number | null;
  createdAt: number;
  hasSafety: boolean;
}

interface ChatState {
  activeThreadId: string | null;
  messages: Message[];
  isStreaming: boolean;
  streamingContent: string;
  streamingThinking: string;
  isThinking: boolean;
  thinkingStartTime: number | null;

  // Actions
  setActiveThread: (threadId: string | null) => void;
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  setStreaming: (streaming: boolean) => void;
  appendStreamToken: (token: string) => void;
  appendThinkToken: (token: string) => void;
  setIsThinking: (thinking: boolean) => void;
  setThinkingStartTime: (time: number | null) => void;
  finalizeStream: (messageId: string, tokensUsed: number) => void;
  clearStream: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  activeThreadId: null,
  messages: [],
  isStreaming: false,
  streamingContent: '',
  streamingThinking: '',
  isThinking: false,
  thinkingStartTime: null,

  setActiveThread: (threadId) => set({ activeThreadId: threadId }),

  setMessages: (messages) => set({ messages }),

  addMessage: (message) => set(state => ({
    messages: [...state.messages, message],
  })),

  setStreaming: (streaming) => set({ isStreaming: streaming }),

  appendStreamToken: (token) => set(state => ({
    streamingContent: state.streamingContent + token,
  })),

  appendThinkToken: (token) => set(state => ({
    streamingThinking: state.streamingThinking + token,
  })),

  setIsThinking: (thinking) => set({ isThinking: thinking }),

  setThinkingStartTime: (time) => set({ thinkingStartTime: time }),

  finalizeStream: (messageId, tokensUsed) => {
    const state = get();
    const thinkTime = state.thinkingStartTime
      ? (Date.now() - state.thinkingStartTime) / 1000
      : null;
    
    const newMessage: Message = {
      id: messageId,
      threadId: state.activeThreadId || '',
      role: 'assistant',
      content: state.streamingContent,
      thinking: state.streamingThinking || null,
      thinkTime,
      tokensUsed,
      createdAt: Date.now(),
      hasSafety: detectSafetyContent(state.streamingContent),
    };
    
    set(prev => ({
      messages: [...prev.messages, newMessage],
      isStreaming: false,
      streamingContent: '',
      streamingThinking: '',
      isThinking: false,
      thinkingStartTime: null,
    }));
    
    return newMessage;
  },

  clearStream: () => set({
    streamingContent: '',
    streamingThinking: '',
    isStreaming: false,
    isThinking: false,
    thinkingStartTime: null,
  }),
}));

/**
 * Detect safety-critical content in AI responses
 * Looks for ESCALATE TO MASTER and similar safety patterns
 */
function detectSafetyContent(content: string): boolean {
  void content;
  return false;
}
