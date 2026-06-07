// ============================================================================
// HRECOS RiverWatch - Root Application Component
// Hudson River environmental monitoring mobile application
// ============================================================================

import React, { useEffect, useState } from 'react';
import { StatusBar, View, ActivityIndicator, StyleSheet, LogBox, Platform } from 'react-native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import * as Notifications from 'expo-notifications';

import { ThemeProvider, useTheme } from './src/context/ThemeContext';
import AppNavigator from './src/navigation/AppNavigator';
import { ensureApiConfigured } from './src/utils/initApi';

// =============================================================================
// SUPPRESS WARNINGS
// =============================================================================

LogBox.ignoreLogs([
  'Non-serializable values were found in the navigation state',
]);

// =============================================================================
// NOTIFICATION SETUP
// =============================================================================

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

// =============================================================================
// TANSTACK QUERY CLIENT
// =============================================================================

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 2,
      gcTime: 1000 * 60 * 10,
      retry: 2,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      refetchOnWindowFocus: false,
    },
  },
});

// =============================================================================
// LOADING SCREEN
// =============================================================================

function LoadingScreen() {
  return (
    <View style={styles.loadingContainer}>
      <ActivityIndicator size="large" color="#0A7EA4" />
    </View>
  );
}

// =============================================================================
// NOTIFICATION MANAGER
// =============================================================================

function NotificationManager() {
  useEffect(() => {
    let isMounted = true;

    async function setupNotifications() {
      try {
        const { status: existingStatus } = await Notifications.getPermissionsAsync();
        let finalStatus = existingStatus;

        if (existingStatus !== 'granted') {
          const { status } = await Notifications.requestPermissionsAsync();
          finalStatus = status;
        }

        if (finalStatus !== 'granted') {
          console.log('Notification permissions not granted');
          return;
        }

        if (Platform.OS === 'android') {
          await Notifications.setNotificationChannelAsync('water-quality-alerts', {
            name: 'Water Quality Alerts',
            importance: Notifications.AndroidImportance.HIGH,
            vibrationPattern: [0, 250, 250, 250],
            lightColor: '#0A7EA4',
          });

          await Notifications.setNotificationChannelAsync('fishing-updates', {
            name: 'Fishing Updates',
            importance: Notifications.AndroidImportance.DEFAULT,
          });

          await Notifications.setNotificationChannelAsync('general', {
            name: 'General',
            importance: Notifications.AndroidImportance.DEFAULT,
          });
        }
      } catch (error) {
        console.warn('Notification setup failed:', error);
      }
    }

    if (isMounted) {
      setupNotifications();
    }

    const subscription = Notifications.addNotificationReceivedListener((notification) => {
      console.log('Notification received:', notification.request.content);
    });

    const responseSubscription = Notifications.addNotificationResponseReceivedListener(
      (response) => {
        console.log('Notification response:', response.notification.request.content);
      }
    );

    return () => {
      isMounted = false;
      subscription.remove();
      responseSubscription.remove();
    };
  }, []);

  return null;
}

// =============================================================================
// MAIN APP CONTENT
// =============================================================================

function AppContent() {
  const [isReady, setIsReady] = useState(false);
  const { colors, isDark } = useTheme();

  useEffect(() => {
    let cancelled = false;

    async function prepare() {
      try {
        await ensureApiConfigured();
        await new Promise((resolve) => setTimeout(resolve, 300));
        if (!cancelled) setIsReady(true);
      } catch (error) {
        console.warn('App preparation failed:', error);
        if (!cancelled) setIsReady(true);
      }
    }

    prepare();
    return () => { cancelled = true; };
  }, []);

  if (!isReady) {
    return <LoadingScreen />;
  }

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <StatusBar
        barStyle={isDark ? 'light-content' : 'dark-content'}
        backgroundColor={colors.surface}
        translucent={false}
      />
      <NotificationManager />
      <AppNavigator />
    </View>
  );
}

// =============================================================================
// ROOT WRAPPER
// =============================================================================

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AppContent />
      </ThemeProvider>
    </QueryClientProvider>
  );
}

// =============================================================================
// STYLES
// =============================================================================

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#0A7EA4',
  },
});
