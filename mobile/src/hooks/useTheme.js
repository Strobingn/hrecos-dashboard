/**
 * useTheme Hook
 *
 * Simple convenience hook that wraps the ThemeContext for easy access
 * to theme colors, dark mode state, and theme toggle functionality
 * throughout the HRECOS RiverWatch app.
 */

import { useContext } from 'react';
import { ThemeContext } from '../context/ThemeContext';

/**
 * Hook for accessing the app's theme context.
 *
 * @returns {Object} {
 *   colors: Theme color palette (primary, background, text, etc.),
 *   isDark: boolean indicating dark mode is active,
 *   toggleTheme: function to toggle between light/dark modes,
 *   setTheme: function to explicitly set the theme mode,
 * }
 *
 * @throws {Error} If used outside of a ThemeContext.Provider.
 */
export function useTheme() {
  const context = useContext(ThemeContext);

  if (context === undefined || context === null) {
    throw new Error(
      'useTheme must be used within a ThemeProvider. ' +
        'Wrap your component tree with <ThemeProvider> from ../context/ThemeContext.'
    );
  }

  return context;
}

export default useTheme;
