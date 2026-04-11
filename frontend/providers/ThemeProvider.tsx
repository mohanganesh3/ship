import React, { createContext, useContext, useState, useCallback, useMemo } from 'react';
import { DarkTheme, LightTheme, type ThemeColors, Colors } from '../constants/theme';

type ThemeMode = 'dark' | 'light';

interface ThemeContextValue {
  mode: ThemeMode;
  colors: ThemeColors;
  accent: typeof Colors;
  toggleMode: () => void;
  isDark: boolean;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setMode] = useState<ThemeMode>('dark');

  const toggleMode = useCallback(() => {
    setMode(prev => (prev === 'dark' ? 'light' : 'dark'));
  }, []);

  const colors = useMemo<ThemeColors>(() => {
    return mode === 'dark' ? DarkTheme : LightTheme;
  }, [mode]);

  const value = useMemo(
    () => ({ mode, colors, accent: Colors, toggleMode, isDark: mode === 'dark' }),
    [mode, colors, toggleMode],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider');
  return ctx;
}
