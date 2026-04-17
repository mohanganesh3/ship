/**
 * App Store — global application state
 * Theme, model status, settings
 */
import { create } from 'zustand';

export type ModelStatus = 'unloaded' | 'loading' | 'active' | 'error';
export type ThinkMode = 'think' | 'no_think';

interface AppState {
  // Model
  modelStatus: ModelStatus;
  modelLoadProgress: number;   // 0-1
  modelFileSize: string;
  modelQuantization: string;
  
  // UI
  thinkMode: ThinkMode;
  
  // Actions
  setModelStatus: (status: ModelStatus) => void;
  setModelLoadProgress: (progress: number) => void;
  setThinkMode: (mode: ThinkMode) => void;
}

export const useAppStore = create<AppState>((set) => ({
  modelStatus: 'unloaded',
  modelLoadProgress: 0,
  modelFileSize: '1.03 GB',
  modelQuantization: 'GGUF',
  thinkMode: 'no_think',

  setModelStatus: (status) => set({ modelStatus: status }),
  setModelLoadProgress: (progress) => set({ modelLoadProgress: progress }),
  setThinkMode: (mode) => set({ thinkMode: mode }),
}));
