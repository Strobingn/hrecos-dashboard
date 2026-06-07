import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  LayoutAnimation,
  Platform,
  UIManager,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useTheme } from '../../hooks/useTheme';

if (
  Platform.OS === 'android' &&
  UIManager.setLayoutAnimationEnabledExperimental
) {
  UIManager.setLayoutAnimationEnabledExperimental(true);
}

function getSeverityConfig(severity, theme) {
  switch (severity) {
    case 'critical':
      return {
        color: theme.colors.danger,
        bg: theme.colors.dangerLight,
        icon: 'alert-octagon',
        label: 'CRITICAL',
      };
    case 'warning':
      return {
        color: theme.colors.warning,
        bg: theme.colors.warningLight,
        icon: 'alert',
        label: 'WARNING',
      };
    case 'info':
    default:
      return {
        color: theme.colors.info,
        bg: theme.colors.infoLight,
        icon: 'information',
        label: 'INFO',
      };
  }
}

function getAnomalyLabel(type) {
  switch (type) {
    case 'high_temperature':
      return 'High Temperature';
    case 'low_temperature':
      return 'Low Temperature';
    case 'high_turbidity':
      return 'High Turbidity';
    case 'low_do':
      return 'Low Dissolved Oxygen';
    case 'high_conductivity':
      return 'High Conductivity';
    case 'sensor_offline':
      return 'Sensor Offline';
    case 'data_gap':
      return 'Data Gap Detected';
    default:
      return type ? type.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()) : 'Anomaly';
  }
}

export default function AlertCard({ alert }) {
  const theme = useTheme();
  const [expanded, setExpanded] = useState(false);

  if (!alert) return null;

  const safeAlert = {
    station: alert.station || 'Unknown Station',
    type: alert.type || 'unknown',
    severity: alert.severity || 'info',
    timestamp: alert.timestamp || new Date().toISOString(),
    value: alert.value,
    expectedRange: alert.expectedRange,
    message: alert.message,
    ...alert,
  };

  const severityConfig = getSeverityConfig(safeAlert.severity, theme);
  const anomalyLabel = getAnomalyLabel(safeAlert.type);

  const toggleExpand = () => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setExpanded(!expanded);
  };

  const formatTimestamp = (ts) => {
    try {
      const date = new Date(ts);
      return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      });
    } catch {
      return ts;
    }
  };

  return (
    <TouchableOpacity
      onPress={toggleExpand}
      activeOpacity={0.85}
      style={[
        styles.container,
        {
          backgroundColor: theme.colors.card,
          borderColor: theme.colors.border,
          borderLeftColor: severityConfig.color,
          shadowColor: theme.isDark ? '#000' : '#64748B',
        },
      ]}
    >
      {/* Left severity border indicator */}
      <View
        style={[
          styles.severityBar,
          { backgroundColor: severityConfig.color },
        ]}
      />

      <View style={styles.content}>
        {/* Header row */}
        <View style={styles.header}>
          <View style={styles.headerLeft}>
            <View
              style={[
                styles.severityBadge,
                { backgroundColor: severityConfig.bg },
              ]}
            >
              <MaterialCommunityIcons
                name={severityConfig.icon}
                size={14}
                color={severityConfig.color}
              />
              <Text
                style={[
                  styles.severityText,
                  { color: severityConfig.color },
                ]}
              >
                {severityConfig.label}
              </Text>
            </View>
            <Text
              style={[styles.stationName, { color: theme.colors.text }]}
              numberOfLines={1}
            >
              {safeAlert.station}
            </Text>
          </View>
          <MaterialCommunityIcons
            name={expanded ? 'chevron-up' : 'chevron-down'}
            size={20}
            color={theme.colors.textTertiary}
          />
        </View>

        {/* Anomaly type */}
        <Text
          style={[styles.anomalyType, { color: theme.colors.textSecondary }]}
        >
          {anomalyLabel}
        </Text>

        {/* Timestamp */}
        <View style={styles.timestampRow}>
          <MaterialCommunityIcons
            name="clock-outline"
            size={12}
            color={theme.colors.textTertiary}
            style={styles.clockIcon}
          />
          <Text
            style={[styles.timestamp, { color: theme.colors.textTertiary }]}
          >
            {formatTimestamp(safeAlert.timestamp)}
          </Text>
        </View>

        {/* Expanded details */}
        {expanded && (
          <View
            style={[
              styles.details,
              { borderTopColor: theme.colors.divider },
            ]}
          >
            {safeAlert.value != null && (
              <View style={styles.detailRow}>
                <Text
                  style={[
                    styles.detailLabel,
                    { color: theme.colors.textSecondary },
                  ]}
                >
                  Actual Value
                </Text>
                <Text
                  style={[
                    styles.detailValue,
                    { color: severityConfig.color },
                  ]}
                >
                  {typeof safeAlert.value === 'number'
                    ? safeAlert.value.toFixed(2)
                    : safeAlert.value}
                </Text>
              </View>
            )}

            {safeAlert.expectedRange && (
              <View style={styles.detailRow}>
                <Text
                  style={[
                    styles.detailLabel,
                    { color: theme.colors.textSecondary },
                  ]}
                >
                  Expected Range
                </Text>
                <Text
                  style={[
                    styles.detailValue,
                    { color: theme.colors.text },
                  ]}
                >
                  {safeAlert.expectedRange.min != null &&
                    safeAlert.expectedRange.max != null
                    ? `${safeAlert.expectedRange.min} - ${safeAlert.expectedRange.max}`
                    : 'N/A'}
                  {safeAlert.expectedRange.unit
                    ? ` ${safeAlert.expectedRange.unit}`
                    : ''}
                </Text>
              </View>
            )}

            {safeAlert.message && (
              <View style={styles.detailRow}>
                <Text
                  style={[
                    styles.detailLabel,
                    { color: theme.colors.textSecondary },
                  ]}
                >
                  Details
                </Text>
                <Text
                  style={[
                    styles.detailMessage,
                    { color: theme.colors.text },
                  ]}
                >
                  {safeAlert.message}
                </Text>
              </View>
            )}
          </View>
        )}
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    marginHorizontal: 16,
    marginVertical: 5,
    borderRadius: 12,
    borderWidth: 1,
    borderLeftWidth: 4,
    flexDirection: 'row',
    overflow: 'hidden',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 6,
    elevation: 2,
  },
  severityBar: {
    width: 4,
  },
  content: {
    flex: 1,
    padding: 12,
    paddingLeft: 10,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  severityBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 6,
    paddingVertical: 3,
    borderRadius: 6,
    marginRight: 8,
  },
  severityText: {
    fontSize: 10,
    fontWeight: '800',
    marginLeft: 3,
    letterSpacing: 0.3,
  },
  stationName: {
    fontSize: 14,
    fontWeight: '700',
    flex: 1,
  },
  anomalyType: {
    fontSize: 13,
    fontWeight: '500',
    marginTop: 6,
  },
  timestampRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 6,
  },
  clockIcon: {
    marginRight: 4,
  },
  timestamp: {
    fontSize: 11,
    fontWeight: '400',
  },
  details: {
    marginTop: 10,
    paddingTop: 10,
    borderTopWidth: 1,
  },
  detailRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 6,
  },
  detailLabel: {
    fontSize: 12,
    fontWeight: '500',
    width: 100,
    flexShrink: 0,
  },
  detailValue: {
    fontSize: 13,
    fontWeight: '700',
    flex: 1,
  },
  detailMessage: {
    fontSize: 12,
    fontWeight: '400',
    flex: 1,
    lineHeight: 18,
  },
});
