import React, { useCallback, useEffect, useRef } from 'react';
import {
  View,
  Text,
  ScrollView,
  RefreshControl,
  StyleSheet,
  TouchableOpacity,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import { useTheme } from '../hooks/useTheme';
import { useDashboard } from '../hooks/useDashboard';
import { useStations } from '../hooks/useStations';
import { useTides } from '../hooks/useTides';
import { useAnomalies } from '../hooks/useAnomalies';
import { TIDE_PHASES } from '../constants';

import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorView } from '../components/common/ErrorView';
import { SectionHeader } from '../components/common/SectionHeader';
import { MetricCard } from '../components/cards/MetricCard';
import { WaterQualityGauge } from '../components/gauges/WaterQualityGauge';
import { StationCard } from '../components/cards/StationCard';
import { AlertCard } from '../components/cards/AlertCard';
import { TideCard } from '../components/cards/TideCard';

const REFRESH_INTERVAL = 5 * 60 * 1000; // 5 minutes

export default function DashboardScreen() {
  const navigation = useNavigation();
  const { theme } = useTheme();

  const {
    data: dashboardData,
    loading: dashboardLoading,
    error: dashboardError,
    refetch: refetchDashboard,
  } = useDashboard();

  const {
    stations,
    loading: stationsLoading,
    error: stationsError,
    refetch: refetchStations,
  } = useStations();

  const {
    data: tideData,
    loading: tideLoading,
    error: tideError,
    refetch: refetchTides,
  } = useTides();

  const {
    anomalies,
    loading: alertsLoading,
    refetch: refetchAlerts,
  } = useAnomalies(3);

  const intervalRef = useRef(null);

  const isLoading = dashboardLoading || stationsLoading || tideLoading || alertsLoading;
  const hasError = dashboardError || stationsError || tideError;

  const onRefresh = useCallback(async () => {
    await Promise.all([
      refetchDashboard(),
      refetchStations(),
      refetchTides(),
      refetchAlerts(),
    ]);
  }, [refetchDashboard, refetchStations, refetchTides, refetchAlerts]);

  // Auto-refresh every 5 minutes
  useEffect(() => {
    intervalRef.current = setInterval(() => {
      onRefresh();
    }, REFRESH_INTERVAL);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [onRefresh]);

  const getCurrentDate = () => {
    return new Date().toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const getTideSubtitle = () => {
    if (!tideData?.current) return '--';
    const phase = TIDE_PHASES[tideData.current.phase];
    return `${tideData.current.height.toFixed(2)}m ${phase ? phase.label : ''}`;
  };

  const getLiveStations = () => {
    return stations.filter(s => s.status === 'live');
  };

  const handleStationPress = (stationId) => {
    navigation.navigate('StationDetail', { stationId });
  };

  const handleViewAllAlerts = () => {
    navigation.navigate('Alerts');
  };

  const handleSettings = () => {
    navigation.navigate('Settings');
  };

  // Loading state
  if (isLoading && !dashboardData) {
    return (
      <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
        <LoadingSpinner fullScreen message="Loading river data..." />
      </View>
    );
  }

  // Error state
  if (hasError && !dashboardData) {
    return (
      <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
        <View style={styles.headerSpacer} />
        <ErrorView
          message={dashboardError || stationsError || 'Failed to load dashboard'}
          onRetry={onRefresh}
        />
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={isLoading}
            onRefresh={onRefresh}
            tintColor={theme.colors.primary}
            colors={[theme.colors.primary]}
          />
        }
      >
        {/* ===== HEADER ===== */}
        <View style={styles.header}>
          <View style={styles.headerLeft}>
            <Text style={[styles.appTitle, { color: theme.colors.text }]}>
              HRECOS RiverWatch
            </Text>
            <Text style={[styles.subtitle, { color: theme.colors.textSecondary }]}>
              Hudson River Environmental Monitor
            </Text>
            <View style={styles.dateRow}>
              <MaterialCommunityIcons name="calendar-today" size={13} color={theme.colors.textTertiary} />
              <Text style={[styles.dateText, { color: theme.colors.textTertiary }]}>
                {getCurrentDate()}
              </Text>
            </View>
          </View>
          <TouchableOpacity
            style={[styles.settingsButton, { backgroundColor: theme.colors.surfaceVariant }]}
            onPress={handleSettings}
            activeOpacity={0.7}
          >
            <MaterialCommunityIcons name="cog" size={22} color={theme.colors.textSecondary} />
          </TouchableOpacity>
        </View>

        {/* ===== QUICK STATS ROW ===== */}
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.statsScroll}
        >
          <MetricCard
            icon="broadcast"
            label="Stations Online"
            value={`${dashboardData?.stationsOnline ?? '--'}`}
            subtitle={`/ ${dashboardData?.totalStations ?? '--'} total`}
            color={theme.colors.success}
            bgColor={theme.colors.successLight}
          />
          <MetricCard
            icon="thermometer-water"
            label="Avg Water Temp"
            value={`${dashboardData?.avgWaterTemp ?? '--'}°C`}
            subtitle="Live stations"
            color={theme.colors.chartTemp}
            bgColor={theme.colors.chartTemp + '20'}
          />
          <MetricCard
            icon="waves-arrow-up"
            label="Current Tide"
            value={tideData?.current?.height?.toFixed(2) ?? '--'}
            subtitle={getTideSubtitle()}
            color={theme.colors.primary}
            bgColor={theme.colors.primaryFaded}
          />
          <MetricCard
            icon="water-check"
            label="Water Quality"
            value={dashboardData?.waterQualityLevel?.label ?? '--'}
            subtitle={`WQI: ${dashboardData?.waterQualityIndex ?? '--'}`}
            color={theme.colors.secondary}
            bgColor={theme.colors.secondaryFaded}
          />
        </ScrollView>

        {/* ===== WATER QUALITY SUMMARY CARD ===== */}
        <View style={[styles.wqCard, { backgroundColor: theme.colors.card }, theme.shadows.medium]}>
          <View style={styles.wqHeader}>
            <MaterialCommunityIcons name="water-check" size={20} color={theme.colors.primary} />
            <Text style={[styles.wqTitle, { color: theme.colors.text }]}>
              River Health
            </Text>
          </View>
          <View style={styles.wqBody}>
            <WaterQualityGauge wqi={dashboardData?.waterQualityIndex || 0} size={150} />
            <View style={styles.wqDescription}>
              <Text style={[styles.wqLabel, { color: theme.colors.textSecondary }]}>
                Water Quality Index
              </Text>
              <Text style={[styles.wqText, { color: theme.colors.textSecondary }]}>
                The Hudson River water quality is currently{' '}
                <Text style={{ fontWeight: '700', color: dashboardData?.waterQualityLevel?.color || theme.colors.text }}>
                  {dashboardData?.waterQualityLevel?.label?.toUpperCase() || 'GOOD'}
                </Text>
                {' '}based on turbidity, dissolved oxygen, and pH readings from active monitoring stations.
              </Text>
            </View>
          </View>
        </View>

        {/* ===== LIVE STATIONS SECTION ===== */}
        <SectionHeader
          title="Live Monitoring Stations"
          icon="radar"
        />
        <View style={styles.stationsList}>
          {getLiveStations().map(station => (
            <StationCard
              key={station.id}
              station={station}
              onPress={() => handleStationPress(station.id)}
              compact
            />
          ))}
          {getLiveStations().length === 0 && (
            <View style={[styles.emptyState, { backgroundColor: theme.colors.card }]}>
              <MaterialCommunityIcons name="broadcast-off" size={32} color={theme.colors.textTertiary} />
              <Text style={[styles.emptyText, { color: theme.colors.textTertiary }]}>
                No live stations currently
              </Text>
            </View>
          )}
        </View>

        {/* ===== RECENT ALERTS PREVIEW ===== */}
        <SectionHeader
          title="Recent Alerts"
          icon="alert-outline"
          actionLabel="View All"
          onAction={handleViewAllAlerts}
        />
        <View style={styles.alertsList}>
          {anomalies.length > 0 ? (
            anomalies.slice(0, 3).map(alert => (
              <AlertCard key={alert.id} alert={alert} />
            ))
          ) : (
            <View style={[styles.emptyState, { backgroundColor: theme.colors.card }]}>
              <MaterialCommunityIcons name="check-circle-outline" size={32} color={theme.colors.success} />
              <Text style={[styles.emptyText, { color: theme.colors.textSecondary }]}>
                No recent alerts. All systems nominal.
              </Text>
            </View>
          )}
        </View>

        {/* ===== NEXT TIDE CARD ===== */}
        <SectionHeader
          title="Tides"
          icon="waves"
        />
        <TideCard tideData={tideData} />

        {/* Footer spacing */}
        <View style={styles.footer} />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scrollContent: {
    paddingTop: 12,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 12,
  },
  headerLeft: {
    flex: 1,
  },
  appTitle: {
    fontSize: 22,
    fontWeight: '800',
    letterSpacing: -0.5,
  },
  subtitle: {
    fontSize: 13,
    marginTop: 2,
  },
  dateRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 6,
  },
  dateText: {
    fontSize: 12,
    marginLeft: 4,
  },
  settingsButton: {
    width: 40,
    height: 40,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: 12,
    marginTop: 2,
  },
  headerSpacer: {
    height: 100,
  },
  statsScroll: {
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  wqCard: {
    marginHorizontal: 16,
    marginVertical: 12,
    borderRadius: 16,
    padding: 16,
  },
  wqHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  wqTitle: {
    fontSize: 16,
    fontWeight: '700',
    marginLeft: 8,
  },
  wqBody: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  wqDescription: {
    flex: 1,
    marginLeft: 12,
  },
  wqLabel: {
    fontSize: 12,
    fontWeight: '600',
    marginBottom: 6,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  wqText: {
    fontSize: 12,
    lineHeight: 18,
  },
  stationsList: {
    marginBottom: 4,
  },
  alertsList: {
    marginBottom: 4,
  },
  emptyState: {
    marginHorizontal: 16,
    marginBottom: 10,
    borderRadius: 12,
    padding: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emptyText: {
    marginTop: 8,
    fontSize: 13,
    textAlign: 'center',
  },
  footer: {
    height: 30,
  },
});
