/**
 * AlertsScreen - Anomaly detection alerts screen
 * Displays AI-detected anomalies with severity filtering,
 * expandable alert cards, and an empty state when all is clear.
 */

import React, { useState, useCallback, useMemo } from 'react';
import {
  View,
  Text,
  ScrollView,
  RefreshControl,
  StyleSheet,
  TouchableOpacity,
  LayoutAnimation,
  Platform,
  UIManager,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useTheme } from '../hooks/useTheme';
import { useAnomalies } from '../hooks/useAnomalies';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorView from '../components/common/ErrorView';
import SectionHeader from '../components/common/SectionHeader';
import Card from '../components/common/Card';
import Badge from '../components/common/Badge';

// Enable LayoutAnimation on Android
if (Platform.OS === 'android' && UIManager.setLayoutAnimationEnabledExperimental) {
  UIManager.setLayoutAnimationEnabledExperimental(true);
}

const SEVERITY_FILTERS = [
  { key: 'all', label: 'All', color: '#0A7EA4' },
  { key: 'critical', label: 'High', color: '#E53935' },
  { key: 'warning', label: 'Medium', color: '#FF8F00' },
  { key: 'info', label: 'Low', color: '#3498DB' },
];

const SEVERITY_CONFIG = {
  critical: { label: 'High', color: '#E53935', borderColor: '#E53935', icon: 'alert-circle' },
  warning: { label: 'Medium', color: '#FF8F00', borderColor: '#FF8F00', icon: 'alert' },
  info: { label: 'Low', color: '#3498DB', borderColor: '#3498DB', icon: 'information' },
};

function formatTimestamp(isoString) {
  if (!isoString) return 'Unknown time';
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  let relative;
  if (diffMins < 1) relative = 'just now';
  else if (diffMins < 60) relative = `${diffMins}m ago`;
  else if (diffHours < 24) relative = `${diffHours}h ago`;
  else relative = `${diffDays}d ago`;

  const formatted = date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });

  return `${formatted} (${relative})`;
}

// Individual alert card with expand/collapse
function AlertCard({ anomaly }) {
  const theme = useTheme();
  const [expanded, setExpanded] = useState(false);
  const config = SEVERITY_CONFIG[anomaly.severity] || SEVERITY_CONFIG.info;

  const toggleExpand = useCallback(() => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setExpanded((prev) => !prev);
  }, []);

  return (
    <Card style={styles.alertCard}>
      <TouchableOpacity
        onPress={toggleExpand}
        activeOpacity={0.8}
        style={[styles.alertTouchable, { borderLeftColor: config.borderColor, borderLeftWidth: 4 }]}
      >
        <View style={styles.alertHeader}>
          <View style={styles.alertLeft}>
            <MaterialCommunityIcons
              name={config.icon}
              size={24}
              color={config.color}
              style={styles.alertIcon}
            />
            <View style={styles.alertInfo}>
              <Text style={[styles.alertStation, { color: theme.colors.textPrimary || theme.colors.text }]}>
                {anomaly.station}
              </Text>
              <Text style={[styles.alertType, { color: theme.colors.textSecondary }]}>
                {anomaly.message}
              </Text>
              <Text style={[styles.alertTime, { color: theme.colors.textSecondary }]}>
                {formatTimestamp(anomaly.timestamp)}
              </Text>
            </View>
          </View>
          <View style={styles.alertRight}>
            <Badge
              label={config.label}
              color={config.color}
              size="small"
            />
            <MaterialCommunityIcons
              name={expanded ? 'chevron-up' : 'chevron-down'}
              size={20}
              color={theme.colors.textSecondary}
              style={styles.expandIcon}
            />
          </View>
        </View>

        {expanded && (
          <View style={styles.alertDetails}>
            <View style={[styles.detailsBox, { backgroundColor: theme.colors.surface || theme.colors.card }]}>
              <Text style={[styles.detailsTitle, { color: theme.colors.textPrimary || theme.colors.text }]}>
                Alert Details
              </Text>
              <View style={styles.detailRow}>
                <Text style={[styles.detailLabel, { color: theme.colors.textSecondary }]}>
                  Anomaly Type:
                </Text>
                <Text style={[styles.detailValue, { color: theme.colors.textPrimary || theme.colors.text }]}>
                  {anomaly.type}
                </Text>
              </View>
              <View style={styles.detailRow}>
                <Text style={[styles.detailLabel, { color: theme.colors.textSecondary }]}>
                  Station:
                </Text>
                <Text style={[styles.detailValue, { color: theme.colors.textPrimary || theme.colors.text }]}>
                  {anomaly.station}
                </Text>
              </View>
              <View style={styles.detailRow}>
                <Text style={[styles.detailLabel, { color: theme.colors.textSecondary }]}>
                  Detected:
                </Text>
                <Text style={[styles.detailValue, { color: theme.colors.textPrimary || theme.colors.text }]}>
                  {formatTimestamp(anomaly.timestamp)}
                </Text>
              </View>
              <View style={styles.detailRow}>
                <Text style={[styles.detailLabel, { color: theme.colors.textSecondary }]}>
                  Severity:
                </Text>
                <Badge label={config.label} color={config.color} size="small" />
              </View>
              <Text style={[styles.detailsNote, { color: theme.colors.textSecondary }]}>
                This anomaly was detected by our AI monitoring system using the Isolation Forest algorithm.
                The reading falls outside the expected range based on historical data patterns.
              </Text>
            </View>
          </View>
        )}
      </TouchableOpacity>
    </Card>
  );
}

// Empty state when no alerts
function EmptyAlertsState() {
  const theme = useTheme();
  return (
    <View style={styles.emptyContainer}>
      <View style={[styles.emptyIconBox, { backgroundColor: (theme.colors.success || '#43A047') + '12' }]}>
        <MaterialCommunityIcons
          name="shield-check"
          size={64}
          color={theme.colors.success || '#43A047'}
        />
      </View>
      <Text style={[styles.emptyTitle, { color: theme.colors.textPrimary || theme.colors.text }]}>
        No Anomalies Detected
      </Text>
      <Text style={[styles.emptyDescription, { color: theme.colors.textSecondary }]}>
        All monitoring stations are reporting normal values. Our AI system continuously
        watches for unusual patterns in river data and will alert you immediately
        when anything abnormal is detected.
      </Text>
    </View>
  );
}

export default function AlertsScreen() {
  const theme = useTheme();
  const { anomalies, loading, error, refetch } = useAnomalies();
  const [refreshing, setRefreshing] = useState(false);
  const [activeFilter, setActiveFilter] = useState('all');

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await refetch();
    setRefreshing(false);
  }, [refetch]);

  const filteredAlerts = useMemo(() => {
    if (!anomalies) return [];
    if (activeFilter === 'all') return anomalies;
    return anomalies.filter((a) => a.severity === activeFilter);
  }, [anomalies, activeFilter]);

  if (loading && !anomalies) {
    return (
      <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
        <LoadingSpinner message="Loading alerts..." />
      </View>
    );
  }

  if (error && !anomalies) {
    return (
      <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
        <ErrorView message={error} onRetry={refetch} />
      </View>
    );
  }

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: theme.colors.background }]}
      contentContainerStyle={styles.contentContainer}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          tintColor={theme.colors.primary}
          colors={[theme.colors.primary]}
        />
      }
    >
      {/* Header */}
      <View style={styles.header}>
        <Text style={[styles.headerTitle, { color: theme.colors.textPrimary || theme.colors.text }]}>
          Alerts
        </Text>
        <Text style={[styles.headerSubtitle, { color: theme.colors.textSecondary }]}>
          AI-detected anomalies
        </Text>
      </View>

      {/* Filter Tabs */}
      <View style={styles.filterRow}>
        {SEVERITY_FILTERS.map((filter) => {
          const isActive = activeFilter === filter.key;
          const alertCount = filter.key === 'all'
            ? (anomalies?.length || 0)
            : (anomalies?.filter((a) => a.severity === filter.key).length || 0);

          return (
            <TouchableOpacity
              key={filter.key}
              onPress={() => setActiveFilter(filter.key)}
              activeOpacity={0.7}
              style={[
                styles.filterChip,
                {
                  backgroundColor: isActive ? filter.color + '18' : (theme.colors.surface || theme.colors.card),
                  borderColor: isActive ? filter.color : (theme.colors.border || theme.colors.divider),
                },
              ]}
            >
              <View style={styles.filterChipInner}>
                <View
                  style={[
                    styles.filterDot,
                    { backgroundColor: filter.color, opacity: isActive ? 1 : 0.5 },
                  ]}
                />
                <Text
                  style={[
                    styles.filterLabel,
                    { color: isActive ? filter.color : theme.colors.textSecondary },
                  ]}
                >
                  {filter.label}
                </Text>
                <View
                  style={[
                    styles.filterCount,
                    { backgroundColor: isActive ? filter.color + '20' : theme.colors.divider },
                  ]}
                >
                  <Text
                    style={[
                      styles.filterCountText,
                      { color: isActive ? filter.color : theme.colors.textSecondary },
                    ]}
                  >
                    {alertCount}
                  </Text>
                </View>
              </View>
            </TouchableOpacity>
          );
        })}
      </View>

      {/* Alerts List */}
      {filteredAlerts.length > 0 ? (
        <View style={styles.alertsList}>
          {filteredAlerts.map((anomaly) => (
            <AlertCard key={anomaly.id} anomaly={anomaly} />
          ))}
        </View>
      ) : (
        <EmptyAlertsState />
      )}

      {/* Info Card */}
      <View style={styles.infoSection}>
        <SectionHeader title="About AI Monitoring" icon="brain" />
        <Card>
          <View style={styles.infoContent}>
            <MaterialCommunityIcons
              name="shield-search"
              size={28}
              color={theme.colors.primary}
              style={styles.infoIcon}
            />
            <Text style={[styles.infoText, { color: theme.colors.textPrimary || theme.colors.text }]}>
              Our AI system uses the Isolation Forest algorithm to detect unusual patterns
              in river data. Alerts are generated when readings fall outside expected ranges
              based on historical patterns for each station and parameter.
            </Text>
            <Text style={[styles.infoSubtext, { color: theme.colors.textSecondary }]}>
              The system monitors all active stations every 5 minutes and evaluates
              temperature, dissolved oxygen, turbidity, pH, conductivity, and other
              parameters for anomalies.
            </Text>
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
  headerSubtitle: {
    fontSize: 14,
    marginTop: 4,
    fontWeight: '400',
  },
  filterRow: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    marginBottom: 12,
  },
  filterChip: {
    flex: 1,
    marginHorizontal: 4,
    borderRadius: 10,
    borderWidth: 1,
    paddingVertical: 8,
    paddingHorizontal: 4,
  },
  filterChipInner: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  filterDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 6,
  },
  filterLabel: {
    fontSize: 13,
    fontWeight: '600',
  },
  filterCount: {
    borderRadius: 10,
    paddingHorizontal: 6,
    paddingVertical: 1,
    marginLeft: 6,
    minWidth: 20,
    alignItems: 'center',
  },
  filterCountText: {
    fontSize: 11,
    fontWeight: '700',
  },
  alertsList: {
    marginTop: 4,
  },
  alertCard: {
    marginHorizontal: 16,
    marginVertical: 5,
  },
  alertTouchable: {
    padding: 14,
    borderRadius: 10,
  },
  alertHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  alertLeft: {
    flexDirection: 'row',
    flex: 1,
  },
  alertIcon: {
    marginRight: 12,
    marginTop: 2,
  },
  alertInfo: {
    flex: 1,
  },
  alertStation: {
    fontSize: 15,
    fontWeight: '700',
  },
  alertType: {
    fontSize: 13,
    marginTop: 2,
    lineHeight: 18,
    fontWeight: '400',
  },
  alertTime: {
    fontSize: 12,
    marginTop: 4,
    fontWeight: '400',
  },
  alertRight: {
    alignItems: 'center',
    marginLeft: 8,
  },
  expandIcon: {
    marginTop: 8,
  },
  alertDetails: {
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: 'rgba(0,0,0,0.06)',
  },
  detailsBox: {
    borderRadius: 10,
    padding: 14,
  },
  detailsTitle: {
    fontSize: 14,
    fontWeight: '700',
    marginBottom: 10,
  },
  detailRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  detailLabel: {
    fontSize: 13,
    fontWeight: '500',
    width: 100,
  },
  detailValue: {
    fontSize: 13,
    fontWeight: '600',
    flex: 1,
  },
  detailsNote: {
    fontSize: 12,
    lineHeight: 18,
    marginTop: 10,
    fontWeight: '400',
  },
  emptyContainer: {
    alignItems: 'center',
    paddingHorizontal: 32,
    paddingVertical: 40,
  },
  emptyIconBox: {
    width: 100,
    height: 100,
    borderRadius: 50,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: '700',
    marginBottom: 8,
  },
  emptyDescription: {
    fontSize: 14,
    textAlign: 'center',
    lineHeight: 22,
    fontWeight: '400',
  },
  infoSection: {
    marginTop: 8,
  },
  infoContent: {
    padding: 8,
    alignItems: 'center',
  },
  infoIcon: {
    marginBottom: 12,
  },
  infoText: {
    fontSize: 14,
    lineHeight: 22,
    textAlign: 'center',
    fontWeight: '400',
  },
  infoSubtext: {
    fontSize: 13,
    lineHeight: 20,
    textAlign: 'center',
    marginTop: 10,
    fontWeight: '400',
  },
  bottomSpacer: {
    height: 24,
  },
});
