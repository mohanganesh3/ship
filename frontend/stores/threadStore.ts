/**
 * Thread Store — thread list management
 */
import { create } from 'zustand';

export interface Thread {
  id: string;
  title: string;
  preview: string;
  pinned: boolean;
  createdAt: number;
  updatedAt: number;
}

interface ThreadState {
  threads: Thread[];
  searchQuery: string;
  filteredThreads: Thread[];
  
  // Actions
  setThreads: (threads: Thread[]) => void;
  addThread: (thread: Thread) => void;
  removeThread: (id: string) => void;
  togglePin: (id: string) => void;
  updateThread: (id: string, updates: Partial<Thread>) => void;
  setSearchQuery: (query: string) => void;
}

export const useThreadStore = create<ThreadState>((set, get) => ({
  threads: [],
  searchQuery: '',
  filteredThreads: [],

  setThreads: (threads) => {
    const sorted = sortThreads(threads);
    set({ threads: sorted, filteredThreads: filterThreads(sorted, get().searchQuery) });
  },

  addThread: (thread) => {
    const threads = sortThreads([thread, ...get().threads]);
    set({ threads, filteredThreads: filterThreads(threads, get().searchQuery) });
  },

  removeThread: (id) => {
    const threads = get().threads.filter(t => t.id !== id);
    set({ threads, filteredThreads: filterThreads(threads, get().searchQuery) });
  },

  togglePin: (id) => {
    const threads = get().threads.map(t =>
      t.id === id ? { ...t, pinned: !t.pinned } : t
    );
    const sorted = sortThreads(threads);
    set({ threads: sorted, filteredThreads: filterThreads(sorted, get().searchQuery) });
  },

  updateThread: (id, updates) => {
    const threads = get().threads.map(t =>
      t.id === id ? { ...t, ...updates } : t
    );
    const sorted = sortThreads(threads);
    set({ threads: sorted, filteredThreads: filterThreads(sorted, get().searchQuery) });
  },

  setSearchQuery: (query) => {
    set({
      searchQuery: query,
      filteredThreads: filterThreads(get().threads, query),
    });
  },
}));

function sortThreads(threads: Thread[]): Thread[] {
  return [...threads].sort((a, b) => {
    if (a.pinned && !b.pinned) return -1;
    if (!a.pinned && b.pinned) return 1;
    return b.updatedAt - a.updatedAt;
  });
}

function filterThreads(threads: Thread[], query: string): Thread[] {
  if (!query.trim()) return threads;
  const q = query.toLowerCase();
  return threads.filter(t =>
    t.title.toLowerCase().includes(q) ||
    t.preview.toLowerCase().includes(q)
  );
}
