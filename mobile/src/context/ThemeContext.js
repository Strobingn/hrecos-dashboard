// ============================================================================
// HRECOS RiverWatch - Theme Context
// Provides dark/light mode management with AsyncStorage persistence
// ============================================================================

import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import { useColorScheme } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { lightColors, darkColors, typography, spacing } from '../theme';

const THEME_STORAGE_KEY = '@hrecos_theme_preference';

const ThemeContext = createContext(null);

/**
 * ThemeProvider - Wraps the app and provides theme state to all children.
 *
 * @param {Object} props
 * @param {React.ReactNode} props.children
 */
export function ThemeProvider({ children }) {
  const systemColorScheme = useColorScheme();
  const [isDark, setIsDark] = useState(systemColorScheme === 'dark');
  const [isLoaded, setIsLoaded] = useState(false);

  // Load saved theme preference on mount
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

  // Persist theme preference whenever it changes
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

  const colors = useMemo(() => (isDark ? darkColors : lightColors), [isDark]);

  const value = useMemo(
    () => ({
      colors,
      typography,
      spacing,
      isDark,
      toggleTheme,
      setDarkMode,
    }),
    [colors, isDark, toggleTheme, setDarkMode]
  );

  if (!isLoaded) {
    // Return a placeholder during initial load to prevent flash
    return null;
  }

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

/**
 * useTheme hook - Access the current theme within any component.
 *
 * @returns {{ colors: Object, typography: Object, spacing: Object, isDark: boolean, toggleTheme: Function, setDarkMode: Function }}
 */
export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === null) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}

export default ThemeContext;
