/**
 * HRECOS RiverWatch - App Navigator
 *
 * Root navigation structure for the Hudson River environmental monitoring app.
 * Uses a Stack.Navigator at the root with a Tab.Navigator inside for the main
 * 6-tab layout: Home, Stations, Tides, Quality, Fish, and Alerts.
 * StationDetail and Settings screens are pushed onto the stack.
 */

import React from 'react';
import { TouchableOpacity, Platform } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { MaterialCommunityIcons } from '@expo/vector-icons';

import { useTheme } from '../hooks/useTheme';

import DashboardScreen from '../screens/DashboardScreen';
import StationsScreen from '../screens/StationsScreen';
import StationDetailScreen from '../screens/StationDetailScreen';
import TidesScreen from '../screens/TidesScreen';
import WaterQualityScreen from '../screens/WaterQualityScreen';
import FishingScreen from '../screens/FishingScreen';
import AlertsScreen from '../screens/AlertsScreen';
import SettingsScreen from '../screens/SettingsScreen';

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

// ── Tab Navigator ────────────────────────────────────────────────────────────

function MainTabNavigator() {
  const { colors, isDark } = useTheme();

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, color, size }) => {
          let iconName;

          switch (route.name) {
            case 'Home':
              iconName = focused ? 'home' : 'home-outline';
              break;
            case 'Stations':
              iconName = focused ? 'map-marker' : 'map-marker-outline';
              break;
            case 'Tides':
              iconName = 'waves';
              break;
            case 'Quality':
              iconName = focused ? 'water-check' : 'water-check-outline';
              break;
            case 'Fish':
              iconName = 'fish';
              break;
            case 'Alerts':
              iconName = focused ? 'bell' : 'bell-outline';
              break;
            default:
              iconName = 'help-circle-outline';
          }

          return (
            <MaterialCommunityIcons
              name={iconName}
              size={size}
              color={color}
            />
          );
        },
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textSecondary,
        tabBarStyle: {
          backgroundColor: isDark ? colors.card : colors.background,
          borderTopColor: colors.border,
          borderTopWidth: 1,
          elevation: 8,
          shadowColor: '#000',
          shadowOffset: { width: 0, height: -2 },
          shadowOpacity: 0.05,
          shadowRadius: 4,
          paddingBottom: Platform.OS === 'ios' ? 20 : 8,
          paddingTop: 4,
          height: Platform.OS === 'ios' ? 80 : 64,
        },
        tabBarLabelStyle: {
          fontSize: 11,
          fontWeight: '500',
          marginBottom: 4,
        },
        headerShown: false,
      })}
    >
      <Tab.Screen name="Home" component={DashboardScreen} />
      <Tab.Screen name="Stations" component={StationsScreen} />
      <Tab.Screen name="Tides" component={TidesScreen} />
      <Tab.Screen
        name="Quality"
        component={WaterQualityScreen}
        options={{ tabBarLabel: 'Quality' }}
      />
      <Tab.Screen name="Fish" component={FishingScreen} />
      <Tab.Screen
        name="Alerts"
        component={AlertsScreen}
        options={{ tabBarLabel: 'Alerts' }}
      />
    </Tab.Navigator>
  );
}

// ── Settings Button ──────────────────────────────────────────────────────────

function SettingsButton({ navigation, color }) {
  return (
    <TouchableOpacity
      onPress={() => navigation.navigate('Settings')}
      style={{ marginRight: 8, padding: 8 }}
      accessibilityLabel="Open settings"
      accessibilityRole="button"
    >
      <MaterialCommunityIcons
        name="cog-outline"
        size={24}
        color={color}
      />
    </TouchableOpacity>
  );
}

// ── Stack Navigator ──────────────────────────────────────────────────────────

export default function AppNavigator() {
  const { colors, isDark } = useTheme();

  return (
    <NavigationContainer>
      <Stack.Navigator
        screenOptions={{
          headerStyle: {
            backgroundColor: isDark ? colors.card : colors.background,
          },
          headerTintColor: colors.primary,
          headerTitleStyle: {
            fontWeight: '600',
            color: colors.textPrimary || colors.text,
          },
          headerShadowVisible: true,
          animation: 'slide_from_right',
          animationDuration: 250,
          contentStyle: {
            backgroundColor: colors.background,
          },
        }}
      >
        <Stack.Screen
          name="MainTabs"
          component={MainTabNavigator}
          options={({ navigation }) => ({
            headerShown: true,
            title: 'HRECOS RiverWatch',
            headerRight: () => (
              <SettingsButton
                navigation={navigation}
                color={colors.primary}
              />
            ),
          })}
        />

        <Stack.Screen
          name="StationDetail"
          component={StationDetailScreen}
          options={({ route }) => ({
            title: route.params?.stationName ?? 'Station Details',
            headerBackTitle: 'Back',
          })}
        />

        <Stack.Screen
          name="Settings"
          component={SettingsScreen}
          options={{
            title: 'Settings',
            headerBackTitle: 'Back',
            presentation: 'modal',
          }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
