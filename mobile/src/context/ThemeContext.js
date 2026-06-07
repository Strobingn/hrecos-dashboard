// ============================================================================
// HRECOS RiverWatch - Theme Context
// Provides dark/light mode management with AsyncStorage persistence
// ============================================================================

import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import { useColorScheme } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { getTheme } from '../theme';

const THEME_STORAGE_KEY = '@hrecos_theme_preference';

export const ThemeContext = createContext(null);

/**
 * ThemeProvider - Wraps the app and provides theme state to all children.
 */
export function ThemeProvider({ children }) {
  const systemColorScheme = useColorScheme();
  const [isDark, setIsDark] = useState(systemColorScheme === 'dark');
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadThemePreference() {
      try {
        const saved = await AsyncStorage.getItem(THEME_STORAGE_KEY);
        if (!cancelled) {
          if (saved !== null) {
            setIsDark(saved === 'dark');
          } else {
            setIsDark(systemColorScheme === 'dark');
          }
          setIsLoaded(true);
        }
      } catch (error) {
        console.warn('Failed to load theme preference:', error);
        if (!cancelled) {
          setIsDark(systemColorScheme === 'dark');
          setIsLoaded(true);
        }
      }
    }

    loadThemePreference();

    return () => {
      cancelled = true;
    };
  }, [systemColorScheme]);

  useEffect(() => {
    if (isLoaded) {
      AsyncStorage.setItem(THEME_STORAGE_KEY, isDark ? 'dark' : 'light').catch((error) => {
        console.warn('Failed to save theme preference:', error);
      });
    }
  }, [isDark, isLoaded]);

  const toggleTheme = useCallback(() => {
    setIsDark((prev) => !prev);
  }, []);

  const setDarkMode = useCallback((value) => {
    setIsDark(!!value);
  }, []);

  const theme = useMemo(() => getTheme(isDark), [isDark]);

  const value = useMemo(
    () => ({
      theme,
      colors: theme.colors,
      spacing: theme.spacing,
      shadows: theme.shadows,
      fonts: theme.fonts,
      radius: theme.radius,
      isDark: theme.isDark,
      toggleTheme,
      setDarkMode,
    }),
    [theme, toggleTheme, setDarkMode]
  );

  if (!isLoaded) {
    return null;
  }

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

/**
 * useTheme hook - Access the current theme within any component.
 */
export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === null) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}

export default ThemeContext;