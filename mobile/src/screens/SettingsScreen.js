/**
 * SettingsScreen - App settings screen
 * Manages appearance, data preferences, notifications, and about info.
 * All settings are persisted via AsyncStorage.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  Switch,
  TextInput,
  TouchableOpacity,
  Alert,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useTheme } from '../hooks/useTheme';
import SectionHeader from '../components/common/SectionHeader';
import Card from '../components/common/Card';
import { API_BASE_URL } from '../config/api';

// Storage keys
const STORAGE_KEYS = {
  apiBaseUrl: '@hrecos_api_base_url',
  refreshInterval: '@hrecos_refresh_interval',
  units: '@hrecos_units',
  pushNotifications: '@hrecos_push_notifications',
  alertOnAnomalies: '@hrecos_alert_anomalies',
  dailySummary: '@hrecos_daily_summary',
};

const DEFAULT_API_URL = API_BASE_URL;
const REFRESH_OPTIONS = [
  { label: '1 minute', value: 60000 },
  { label: '5 minutes', value: 300000 },
  { label: '10 minutes', value: 600000 },
  { label: '30 minutes', value: 1800000 },
];

// Simple picker dropdown component
function SettingPicker({ options, selectedValue, onValueChange }) {
  const theme = useTheme();
  const [open, setOpen] = useState(false);

  const selectedLabel = options.find((o) => o.value === selectedValue)?.label || 'Select...';

  return (
    <View>
      <TouchableOpacity
        onPress={() => setOpen(!open)}
        activeOpacity={0.7}
        style={[styles.pickerTrigger, { backgroundColor: theme.colors.surface || theme.colors.card, borderColor: theme.colors.border }]}
      >
        <Text style={[styles.pickerTriggerText, { color: theme.colors.textPrimary || theme.colors.text }]}>
          {selectedLabel}
        </Text>
        <MaterialCommunityIcons
          name={open ? 'chevron-up' : 'chevron-down'}
          size={20}
          color={theme.colors.textSecondary}
        />
      </TouchableOpacity>
      {open && (
        <View style={[styles.pickerDropdown, { backgroundColor: theme.colors.surface || theme.colors.card, borderColor: theme.colors.border }]}>
          {options.map((option) => {
            const isSelected = option.value === selectedValue;
            return (
              <TouchableOpacity
                key={option.value}
                onPress={() => {
                  onValueChange(option.value);
                  setOpen(false);
                }}
                activeOpacity={0.7}
                style={[
                  styles.pickerOption,
                  isSelected && { backgroundColor: (theme.colors.primary || '#0A7EA4') + '12' },
                ]}
              >
                <Text
                  style={[
                    styles.pickerOptionText,
                    { color: isSelected ? (theme.colors.primary || '#0A7EA4') : (theme.colors.textPrimary || theme.colors.text) },
                    isSelected && styles.pickerOptionTextSelected,
                  ]}
                >
                  {option.label}
                </Text>
                {isSelected && (
                  <MaterialCommunityIcons
                    name="check"
                    size={18}
                    color={theme.colors.primary || '#0A7EA4'}
                  />
                )}
              </TouchableOpacity>
            );
          })}
        </View>
      )}
    </View>
  );
}

// Toggle row component
function ToggleRow({ icon, label, description, value, onValueChange, color }) {
  const theme = useTheme();
  return (
    <View style={styles.toggleRow}>
      <View style={styles.toggleLeft}>
        {icon && (
          <View style={[styles.toggleIconBox, { backgroundColor: (color || theme.colors.primary) + '12' }]}>
            <MaterialCommunityIcons name={icon} size={20} color={color || theme.colors.primary} />
          </View>
        )}
        <View style={styles.toggleText}>
          <Text style={[styles.toggleLabel, { color: theme.colors.textPrimary || theme.colors.text }]}>
            {label}
          </Text>
          {description && (
            <Text style={[styles.toggleDescription, { color: theme.colors.textSecondary }]}>
              {description}
            </Text>
          )}
        </View>
      </View>
      <Switch
        value={value}
        onValueChange={onValueChange}
        trackColor={{
          false: theme.colors.divider,
          true: (color || theme.colors.primary) + '60',
        }}
        thumbColor={value ? (color || theme.colors.primary) : '#999'}
      />
    </View>
  );
}

// Divider component
function Divider() {
  const theme = useTheme();
  return (
    <View style={[styles.divider, { backgroundColor: theme.colors.divider }]} />
  );
}

export default function SettingsScreen() {
  const theme = useTheme();
  const { isDark, toggleTheme } = useTheme();

  // Settings state
  const [apiUrl, setApiUrl] = useState(DEFAULT_API_URL);
  const [refreshInterval, setRefreshInterval] = useState(300000);
  const [units, setUnits] = useState('imperial');
  const [pushNotifications, setPushNotifications] = useState(true);
  const [alertOnAnomalies, setAlertOnAnomalies] = useState(true);
  const [dailySummary, setDailySummary] = useState(false);
  const [urlEdited, setUrlEdited] = useState(false);

  // Load saved settings on mount
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const [
          savedUrl,
          savedInterval,
          savedUnits,
          savedPush,
          savedAlerts,
          savedDaily,
        ] = await Promise.all([
          AsyncStorage.getItem(STORAGE_KEYS.apiBaseUrl),
          AsyncStorage.getItem(STORAGE_KEYS.refreshInterval),
          AsyncStorage.getItem(STORAGE_KEYS.units),
          AsyncStorage.getItem(STORAGE_KEYS.pushNotifications),
          AsyncStorage.getItem(STORAGE_KEYS.alertOnAnomalies),
          AsyncStorage.getItem(STORAGE_KEYS.dailySummary),
        ]);

        if (savedUrl) setApiUrl(savedUrl);
        if (savedInterval) setRefreshInterval(parseInt(savedInterval, 10));
        if (savedUnits) setUnits(savedUnits);
        if (savedPush !== null) setPushNotifications(savedPush === 'true');
        if (savedAlerts !== null) setAlertOnAnomalies(savedAlerts === 'true');
        if (savedDaily !== null) setDailySummary(savedDaily === 'true');
      } catch (error) {
        console.warn('Failed to load settings:', error);
      }
    };

    loadSettings();
  }, []);

  // Persist a setting value
  const persistSetting = useCallback(async (key, value) => {
    try {
      await AsyncStorage.setItem(key, String(value));
    } catch (error) {
      console.warn(`Failed to save setting ${key}:`, error);
    }
  }, []);

  const handleUrlSave = useCallback(async () => {
    await persistSetting(STORAGE_KEYS.apiBaseUrl, apiUrl);
    setUrlEdited(false);
    Alert.alert('Saved', 'API Base URL has been updated.');
  }, [apiUrl, persistSetting]);

  const handleRefreshIntervalChange = useCallback(async (value) => {
    setRefreshInterval(value);
    await persistSetting(STORAGE_KEYS.refreshInterval, value);
  }, [persistSetting]);

  const handleUnitsChange = useCallback(async (value) => {
    setUnits(value);
    await persistSetting(STORAGE_KEYS.units, value);
  }, [persistSetting]);

  const UNIT_OPTIONS = [
    { label: 'Imperial (°F, ft³/s)', value: 'imperial' },
    { label: 'Metric (°C, m³/s)', value: 'metric' },
  ];

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: theme.colors.background }]}
      contentContainerStyle={styles.contentContainer}
    >
      {/* Header */}
      <View style={styles.header}>
        <Text style={[styles.headerTitle, { color: theme.colors.textPrimary || theme.colors.text }]}>
          Settings
        </Text>
      </View>

      {/* Appearance Section */}
      <View style={styles.section}>
        <SectionHeader title="Appearance" icon="palette-outline" />
        <Card>
          <ToggleRow
            icon={isDark ? 'weather-night' : 'white-balance-sunny'}
            label="Dark Mode"
            description={isDark ? 'Dark theme is active' : 'Light theme is active'}
            value={isDark}
            onValueChange={() => {
              toggleTheme();
            }}
            color="#9B59B6"
          />
        </Card>
      </View>

      {/* Data Section */}
      <View style={styles.section}>
        <SectionHeader title="Data" icon="database-outline" />
        <Card>
          {/* API Base URL */}
          <View style={styles.inputGroup}>
            <View style={styles.inputLabelRow}>
              <MaterialCommunityIcons name="link" size={16} color={theme.colors.textSecondary} />
              <Text style={[styles.inputLabel, { color: theme.colors.textSecondary }]}>
                API Base URL
              </Text>
            </View>
            <TextInput
              value={apiUrl}
              onChangeText={(text) => {
                setApiUrl(text);
                setUrlEdited(true);
              }}
              placeholder="https://..."
              placeholderTextColor={theme.colors.textSecondary}
              style={[
                styles.textInput,
                {
                  backgroundColor: theme.colors.surface || theme.colors.card,
                  color: theme.colors.textPrimary || theme.colors.text,
                  borderColor: theme.colors.border,
                },
              ]}
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="url"
            />
            {urlEdited && (
              <TouchableOpacity
                onPress={handleUrlSave}
                activeOpacity={0.8}
                style={[styles.saveButton, { backgroundColor: theme.colors.primary || '#0A7EA4' }]}
              >
                <MaterialCommunityIcons name="content-save" size={16} color="#FFFFFF" />
                <Text style={styles.saveButtonText}>Save URL</Text>
              </TouchableOpacity>
            )}
          </View>

          <Divider />

          {/* Refresh Interval */}
          <View style={styles.inputGroup}>
            <View style={styles.inputLabelRow}>
              <MaterialCommunityIcons name="sync" size={16} color={theme.colors.textSecondary} />
              <Text style={[styles.inputLabel, { color: theme.colors.textSecondary }]}>
                Refresh Interval
              </Text>
            </View>
            <SettingPicker
              options={REFRESH_OPTIONS}
              selectedValue={refreshInterval}
              onValueChange={handleRefreshIntervalChange}
            />
          </View>

          <Divider />

          {/* Units */}
          <View style={styles.inputGroup}>
            <View style={styles.inputLabelRow}>
              <MaterialCommunityIcons name="ruler" size={16} color={theme.colors.textSecondary} />
              <Text style={[styles.inputLabel, { color: theme.colors.textSecondary }]}>
                Units
              </Text>
            </View>
            <SettingPicker
              options={UNIT_OPTIONS}
              selectedValue={units}
              onValueChange={handleUnitsChange}
            />
          </View>
        </Card>
      </View>

      {/* Notifications Section */}
      <View style={styles.section}>
        <SectionHeader title="Notifications" icon="bell-outline" />
        <Card>
          <ToggleRow
            icon="bell-ring"
            label="Enable Push Notifications"
            description="Receive push notifications from the app"
            value={pushNotifications}
            onValueChange={async (val) => {
              setPushNotifications(val);
              await persistSetting(STORAGE_KEYS.pushNotifications, val);
            }}
          />
          <Divider />
          <ToggleRow
            icon="alert"
            label="Alert on Anomalies"
            description="Get notified when AI detects unusual patterns"
            value={alertOnAnomalies}
            onValueChange={async (val) => {
              setAlertOnAnomalies(val);
              await persistSetting(STORAGE_KEYS.alertOnAnomalies, val);
            }}
            color="#E53935"
          />
          <Divider />
          <ToggleRow
            icon="calendar-check"
            label="Daily Summary"
            description="Receive a daily summary of river conditions"
            value={dailySummary}
            onValueChange={async (val) => {
              setDailySummary(val);
              await persistSetting(STORAGE_KEYS.dailySummary, val);
            }}
            color="#43A047"
          />
        </Card>
      </View>

      {/* About Section */}
      <View style={styles.section}>
        <SectionHeader title="About" icon="information-outline" />
        <Card>
          <View style={styles.aboutContent}>
            {/* App name and version */}
            <View style={styles.aboutHeader}>
              <View style={[styles.appIconBox, { backgroundColor: (theme.colors.primary || '#0A7EA4') + '15' }]}>
                <MaterialCommunityIcons
                  name="waves"
                  size={32}
                  color={theme.colors.primary || '#0A7EA4'}
                />
              </View>
              <View style={styles.appTitleBox}>
                <Text style={[styles.appName, { color: theme.colors.textPrimary || theme.colors.text }]}>
                  HRECOS RiverWatch
                </Text>
                <Text style={[styles.appVersion, { color: theme.colors.textSecondary }]}>
                  v1.0.0
                </Text>
              </View>
            </View>

            <View style={[styles.aboutDivider, { backgroundColor: theme.colors.divider }]} />

            {/* Description */}
            <Text style={[styles.aboutDescription, { color: theme.colors.textPrimary || theme.colors.text }]}>
              HRECOS RiverWatch provides real-time environmental monitoring data
              from the Hudson River Environmental Conditions Observing System.
              Track water quality, tides, weather, and fishing conditions along
              the Hudson River in New York State.
            </Text>

            <View style={[styles.aboutDivider, { backgroundColor: theme.colors.divider }]} />

            {/* Data Sources */}
            <Text style={[styles.dataSourcesTitle, { color: theme.colors.textPrimary || theme.colors.text }]}>
              Data Sources
            </Text>
            <View style={styles.sourceItem}>
              <MaterialCommunityIcons name="database" size={16} color="#1A6BAA" />
              <Text style={[styles.sourceText, { color: theme.colors.textSecondary }]}>
                <Text style={[styles.sourceName, { color: theme.colors.textPrimary || theme.colors.text }]}>USGS</Text>
                {' '}– United States Geological Survey water quality data
              </Text>
            </View>
            <View style={styles.sourceItem}>
              <MaterialCommunityIcons name="database" size={16} color="#28A745" />
              <Text style={[styles.sourceText, { color: theme.colors.textSecondary }]}>
                <Text style={[styles.sourceName, { color: theme.colors.textPrimary || theme.colors.text }]}>NOAA</Text>
                {' '}– National Oceanic and Atmospheric Administration tides
              </Text>
            </View>
            <View style={styles.sourceItem}>
              <MaterialCommunityIcons name="database" size={16} color="#E67E22" />
              <Text style={[styles.sourceText, { color: theme.colors.textSecondary }]}>
                <Text style={[styles.sourceName, { color: theme.colors.textPrimary || theme.colors.text }]}>NDBC</Text>
                {' '}– National Data Buoy Center meteorological data
              </Text>
            </View>

            <View style={[styles.aboutDivider, { backgroundColor: theme.colors.divider }]} />

            {/* Refresh info */}
            <View style={styles.refreshInfo}>
              <MaterialCommunityIcons
                name="sync-circle"
                size={16}
                color={theme.colors.textSecondary}
              />
              <Text style={[styles.refreshInfoText, { color: theme.colors.textSecondary }]}>
                Data refreshes automatically every 5 minutes from HRECOS monitoring stations.
              </Text>
            </View>
          </View>
        </Card>
      </View>

      <View style={styles.bottomSpacer} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  contentContainer: {
    paddingTop: 16,
    paddingBottom: 32,
  },
  header: {
    paddingHorizontal: 20,
    marginBottom: 16,
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: '800',
    letterSpacing: -0.5,
  },
  section: {
    marginBottom: 4,
  },
  toggleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 12,
    paddingHorizontal: 4,
  },
  toggleLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
    marginRight: 12,
  },
  toggleIconBox: {
    width: 38,
    height: 38,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 14,
  },
  toggleText: {
    flex: 1,
  },
  toggleLabel: {
    fontSize: 15,
    fontWeight: '600',
  },
  toggleDescription: {
    fontSize: 12,
    marginTop: 2,
    fontWeight: '400',
  },
  divider: {
    height: 1,
    marginHorizontal: 4,
  },
  inputGroup: {
    paddingVertical: 10,
    paddingHorizontal: 4,
  },
  inputLabelRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  inputLabel: {
    fontSize: 13,
    fontWeight: '600',
    marginLeft: 8,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  textInput: {
    height: 44,
    borderRadius: 10,
    borderWidth: 1,
    paddingHorizontal: 14,
    fontSize: 15,
    fontWeight: '500',
  },
  saveButton: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    marginTop: 10,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
  },
  saveButtonText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '700',
    marginLeft: 8,
  },
  pickerTrigger: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    height: 44,
    borderRadius: 10,
    borderWidth: 1,
    paddingHorizontal: 14,
  },
  pickerTriggerText: {
    fontSize: 15,
    fontWeight: '500',
  },
  pickerDropdown: {
    marginTop: 4,
    borderRadius: 10,
    borderWidth: 1,
    overflow: 'hidden',
  },
  pickerOption: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  pickerOptionText: {
    fontSize: 15,
    fontWeight: '500',
  },
  pickerOptionTextSelected: {
    fontWeight: '700',
  },
  aboutContent: {
    padding: 8,
  },
  aboutHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  appIconBox: {
    width: 56,
    height: 56,
    borderRadius: 14,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 16,
  },
  appTitleBox: {
    flex: 1,
  },
  appName: {
    fontSize: 18,
    fontWeight: '700',
  },
  appVersion: {
    fontSize: 14,
    marginTop: 2,
    fontWeight: '500',
  },
  aboutDivider: {
    height: 1,
    marginVertical: 14,
  },
  aboutDescription: {
    fontSize: 14,
    lineHeight: 22,
    fontWeight: '400',
  },
  dataSourcesTitle: {
    fontSize: 15,
    fontWeight: '700',
    marginBottom: 10,
  },
  sourceItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 10,
  },
  sourceText: {
    fontSize: 13,
    lineHeight: 18,
    marginLeft: 10,
    flex: 1,
    fontWeight: '400',
  },
  sourceName: {
    fontWeight: '700',
  },
  refreshInfo: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  refreshInfoText: {
    fontSize: 13,
    lineHeight: 18,
    marginLeft: 10,
    flex: 1,
    fontWeight: '400',
  },
  bottomSpacer: {
    height: 24,
  },
});
