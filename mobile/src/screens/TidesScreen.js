/**
 * TidesScreen - Comprehensive tide information screen
 * Displays current tide status, 48-hour forecast chart, tide schedule,
 * moon phase, and educational information about Hudson River tides.
 */

import React, { useState, useCallback, useMemo } from 'react';
import {
  View,
  Text,
  ScrollView,
  RefreshControl,
  StyleSheet,
  Dimensions,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useTheme } from '../hooks/useTheme';
import { useTides } from '../hooks/useTides';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorView from '../components/common/ErrorView';
import SectionHeader from '../components/common/SectionHeader';
import Card from '../components/common/Card';
import TideChart from '../components/charts/TideChart';
import { TIDE_LOCATION } from '../constants';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

// Moon phase calculation based on date
function getMoonPhase(date = new Date()) {
  const year = date.getFullYear();
  const month = date.getMonth() + 1;
  const day = date.getDate();

  let c, e, jd, b;
  if (month < 3) {
    year--;
    month += 12;
  }
  c = 365.25 * year;
  e = 30.6 * month;
  jd = c + e + day - 694039.09;
  jd /= 29.5305882;
  b = parseInt(jd);
  jd -= b;
  b = Math.round(jd * 8);

  const phase = b & 7;
  const illumination = Math.round(jd * 100);

  const phases = [
    { name: 'New Moon', icon: 'moon-new', description: 'Tides are extra high and low (spring tides).' },
    { name: 'Waxing Crescent', icon: 'moon-waxing-crescent', description: 'Tides are becoming more extreme.' },
    { name: 'First Quarter', icon: 'moon-first-quarter', description: 'Moderate tides (neap tides).' },
    { name: 'Waxing Gibbous', icon: 'moon-waxing-gibbous', description: 'Tides are building toward spring extremes.' },
    { name: 'Full Moon', icon: 'moon-full', description: 'Tides are extra high and low (spring tides).' },
    { name: 'Waning Gibbous', icon: 'moon-waning-gibbous', description: 'Tides are decreasing from spring extremes.' },
    { name: 'Last Quarter', icon: 'moon-last-quarter', description: 'Moderate tides (neap tides).' },
    { name: 'Waning Crescent', icon: 'moon-waning-crescent', description: 'Tides are approaching neap moderation.' },
  ];

  return {
    ...phases[phase],
    illumination: Math.abs(illumination > 100 ? 200 - illumination : illumination),
    phase,
  };
}

// Generate upcoming tide events list
function generateTideSchedule(predictions) {
  if (!predictions || predictions.length === 0) return [];

  const events = [];
  for (let i = 1; i < predictions.length - 1; i++) {
    const prev = predictions[i - 1].height;
    const curr = predictions[i].height;
    const next = predictions[i + 1].height;

    if (curr > prev && curr > next) {
      events.push({
        time: predictions[i].timestamp || predictions[i].time,
        type: 'High',
        height: curr,
      });
    } else if (curr < prev && curr < next) {
      events.push({
        time: predictions[i].timestamp || predictions[i].time,
        type: 'Low',
        height: curr,
      });
    }
  }

  // Sort by time and take next 10
  const now = new Date();
  return events
    .filter((e) => new Date(e.time) > now)
    .sort((a, b) => new Date(a.time) - new Date(b.time))
    .slice(0, 10);
}

// Format relative time (e.g., "in 3h 24m")
function getRelativeTime(timeStr) {
  const now = new Date();
  const time = new Date(timeStr);
  const diffMs = time - now;
  if (diffMs < 0) return 'now';

  const hours = Math.floor(diffMs / (1000 * 60 * 60));
  const mins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

  if (hours > 0) {
    return `in ${hours}h ${mins}m`;
  }
  return `in ${mins}m`;
}

// Format time for display
function formatTime(timeStr) {
  const date = new Date(timeStr);
  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

export default function TidesScreen() {
  const theme = useTheme();
  const { data, loading, error, refetch } = useTides();
  const [refreshing, setRefreshing] = useState(false);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await refetch();
    setRefreshing(false);
  }, [refetch]);

  const moonPhase = useMemo(() => getMoonPhase(), []);

  const tideSchedule = useMemo(() => {
    if (!data?.predictions) return [];
    return generateTideSchedule(data.predictions);
  }, [data?.predictions]);

  const nextHigh = useMemo(() => {
    return tideSchedule.find((e) => e.type === 'High');
  }, [tideSchedule]);

  const nextLow = useMemo(() => {
    return tideSchedule.find((e) => e.type === 'Low');
  }, [tideSchedule]);

  const timeUntilNext = useMemo(() => {
    if (tideSchedule.length === 0) return '';
    return getRelativeTime(tideSchedule[0].time);
  }, [tideSchedule]);

  const currentPhaseLabel = useMemo(() => {
    if (!data?.current) return { label: 'Loading...', icon: 'waves', color: theme.colors.textSecondary };
    const phase = data.current.phase;
    switch (phase) {
      case 'rising':
        return { label: 'Rising', icon: 'arrow-up-bold', color: theme.colors.success || '#43A047' };
      case 'falling':
        return { label: 'Falling', icon: 'arrow-down-bold', color: theme.colors.primary || '#0A7EA4' };
      case 'high':
        return { label: 'High Tide', icon: 'arrow-collapse-up', color: theme.colors.warning || '#FFB300' };
      case 'low':
        return { label: 'Low Tide', icon: 'arrow-collapse-down', color: theme.colors.secondary || '#26A69A' };
      default:
        return { label: phase || 'Unknown', icon: 'waves', color: theme.colors.textSecondary };
    }
  }, [data?.current, theme]);

  if (loading && !data) {
    return (
      <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
        <LoadingSpinner message="Loading tide predictions..." />
      </View>
    );
  }

  if (error && !data) {
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
          Tide Predictions
        </Text>
        <Text style={[styles.headerSubtitle, { color: theme.colors.textSecondary }]}>
          {TIDE_LOCATION.place} at {TIDE_LOCATION.landmark}
        </Text>
        <Text style={[styles.headerSource, { color: theme.colors.textSecondary }]}>
          NOAA {TIDE_LOCATION.stationId} {TIDE_LOCATION.stationName} · {TIDE_LOCATION.distance}
          {data?.source === 'api' ? ' · live' : ' · offline demo'}
        </Text>
      </View>

      {/* Tide Chart — shown first */}
      <View style={styles.chartCard}>
        <SectionHeader
          title="48-Hour Tide Forecast"
          icon="chart-line"
          subtitle={`${TIDE_LOCATION.dataProvider} ${TIDE_LOCATION.stationId} via ${TIDE_LOCATION.apiEndpoint}`}
        />
        <Card>
          <TideChart
            predictions={data?.predictions?.map((p) => ({
              time: p.timestamp || p.time,
              height: p.height,
            }))}
            title={`${TIDE_LOCATION.stationName} (${TIDE_LOCATION.stationId})`}
          />
        </Card>
      </View>

      {/* Current Tide Status Card */}
      <Card variant="elevated" style={styles.statusCard}>
        <View style={styles.statusContent}>
          <View style={styles.statusMain}>
            <Text style={[styles.tideHeight, { color: theme.colors.primary }]}>
              {data?.current?.height?.toFixed(1) || '--'} ft
            </Text>
            <View style={styles.phaseRow}>
              <MaterialCommunityIcons
                name={currentPhaseLabel.icon}
                size={24}
                color={currentPhaseLabel.color}
              />
              <Text style={[styles.phaseText, { color: currentPhaseLabel.color }]}>
                {currentPhaseLabel.label}
              </Text>
            </View>
          </View>

          <View style={styles.dividerLine} />

          <View style={styles.nextTidesContainer}>
            {nextHigh && (
              <View style={styles.nextTideRow}>
                <MaterialCommunityIcons name="arrow-collapse-up" size={18} color={theme.colors.success || '#43A047'} />
                <Text style={[styles.nextTideText, { color: theme.colors.textPrimary || theme.colors.text }]}>
                  Next High Tide:{' '}
                  <Text style={styles.nextTideTime}>{formatTime(nextHigh.time)}</Text>
                  {' '}({nextHigh.height.toFixed(1)} ft)
                </Text>
              </View>
            )}
            {nextLow && (
              <View style={styles.nextTideRow}>
                <MaterialCommunityIcons name="arrow-collapse-down" size={18} color={theme.colors.primary || '#0A7EA4'} />
                <Text style={[styles.nextTideText, { color: theme.colors.textPrimary || theme.colors.text }]}>
                  Next Low Tide:{' '}
                  <Text style={styles.nextTideTime}>{formatTime(nextLow.time)}</Text>
                  {' '}({nextLow.height.toFixed(1)} ft)
                </Text>
              </View>
            )}
            {timeUntilNext && (
              <View style={styles.timeUntilRow}>
                <MaterialCommunityIcons name="clock-outline" size={16} color={theme.colors.textSecondary} />
                <Text style={[styles.timeUntilText, { color: theme.colors.textSecondary }]}>
                  {timeUntilNext} until next {tideSchedule[0]?.type?.toLowerCase() || 'tide'}
                </Text>
              </View>
            )}
          </View>
        </View>
      </Card>

      {/* Tide Schedule List */}
      <View style={styles.scheduleSection}>
        <SectionHeader
          title="Upcoming Tides"
          icon="calendar-clock"
          subtitle={`Next ${tideSchedule.length} tide events`}
        />
        <Card>
          {tideSchedule.map((event, index) => (
            <View key={`${event.time}-${index}`}>
              <View style={styles.scheduleItem}>
                <View style={styles.scheduleLeft}>
                  <MaterialCommunityIcons
                    name={event.type === 'High' ? 'arrow-collapse-up' : 'arrow-collapse-down'}
                    size={22}
                    color={
                      event.type === 'High'
                        ? (theme.colors.success || '#43A047')
                        : (theme.colors.primary || '#0A7EA4')
                    }
                  />
                  <View style={styles.scheduleInfo}>
                    <Text style={[styles.scheduleType, { color: theme.colors.textPrimary || theme.colors.text }]}>
                      {event.type} Tide
                    </Text>
                    <Text style={[styles.scheduleTime, { color: theme.colors.textSecondary }]}>
                      {formatTime(event.time)}
                    </Text>
                  </View>
                </View>
                <View style={styles.scheduleRight}>
                  <Text style={[styles.scheduleHeight, { color: theme.colors.textPrimary || theme.colors.text }]}>
                    {event.height.toFixed(1)} ft
                  </Text>
                  <Text style={[styles.scheduleRelative, { color: theme.colors.textSecondary }]}>
                    {getRelativeTime(event.time)}
                  </Text>
                </View>
              </View>
              {index < tideSchedule.length - 1 && (
                <View style={[styles.itemDivider, { backgroundColor: theme.colors.divider }]} />
              )}
            </View>
          ))}
          {tideSchedule.length === 0 && (
            <Text style={[styles.noDataText, { color: theme.colors.textSecondary }]}>
              No upcoming tide events available
            </Text>
          )}
        </Card>
      </View>

      {/* Moon Phase Card */}
      <View style={styles.moonSection}>
        <SectionHeader title="Moon Phase" icon="moon-waning-crescent" />
        <Card>
          <View style={styles.moonContent}>
            <View style={styles.moonIconContainer}>
              <MaterialCommunityIcons
                name={moonPhase.icon}
                size={56}
                color={theme.colors.accent || '#FF8F00'}
              />
            </View>
            <View style={styles.moonInfo}>
              <Text style={[styles.moonName, { color: theme.colors.textPrimary || theme.colors.text }]}>
                {moonPhase.name}
              </Text>
              <Text style={[styles.moonIllumination, { color: theme.colors.textSecondary }]}>
                {moonPhase.illumination}% illuminated
              </Text>
              <Text style={[styles.moonDescription, { color: theme.colors.textSecondary }]}>
                {moonPhase.description}
              </Text>
            </View>
          </View>
        </Card>
      </View>

      {/* Tide Info Card */}
      <View style={styles.infoSection}>
        <SectionHeader title="About These Tides" icon="information-outline" />
        <Card>
          <View style={styles.infoContent}>
            <Text style={[styles.infoText, { color: theme.colors.textPrimary || theme.colors.text }]}>
              The Hudson River experiences semi-diurnal tides, meaning there are typically
              two high tides and two low tides each day. Tides on the Hudson are driven
              primarily by the Atlantic Ocean and can travel as far north as the Federal
              Dam in Troy, NY - about 150 miles upstream.
            </Text>
            <View style={[styles.stationInfoBox, { backgroundColor: theme.colors.surface || theme.colors.card }]}>
              <MaterialCommunityIcons
                name="broadcast"
                size={18}
                color={theme.colors.primary}
                style={styles.stationIcon}
              />
              <Text style={[styles.stationInfoText, { color: theme.colors.textSecondary }]}>
                Data from NOAA Station 8518935 (Newburgh), approximately 3 miles south of Cornwall-on-Hudson at West Point.
                Predictions are calculated using harmonic constituents and updated every 15 minutes.
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
  headerSubtitle: {
    fontSize: 14,
    marginTop: 4,
    fontWeight: '400',
  },
  headerSource: {
    fontSize: 12,
    marginTop: 6,
    fontWeight: '400',
    lineHeight: 18,
  },
  statusCard: {
    marginHorizontal: 16,
    marginBottom: 8,
  },
  statusContent: {
    padding: 20,
  },
  statusMain: {
    alignItems: 'center',
    marginBottom: 16,
  },
  tideHeight: {
    fontSize: 56,
    fontWeight: '800',
    letterSpacing: -1,
  },
  phaseRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 8,
    paddingHorizontal: 16,
    paddingVertical: 6,
    borderRadius: 20,
    backgroundColor: 'rgba(10, 126, 164, 0.08)',
  },
  phaseText: {
    fontSize: 18,
    fontWeight: '700',
    marginLeft: 8,
  },
  dividerLine: {
    height: 1,
    backgroundColor: 'rgba(0,0,0,0.06)',
    marginVertical: 14,
  },
  nextTidesContainer: {
    gap: 10,
  },
  nextTideRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  nextTideText: {
    fontSize: 14,
    marginLeft: 10,
    fontWeight: '500',
    flex: 1,
    flexWrap: 'wrap',
  },
  nextTideTime: {
    fontWeight: '700',
  },
  timeUntilRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 4,
  },
  timeUntilText: {
    fontSize: 13,
    marginLeft: 10,
    fontWeight: '500',
    fontStyle: 'italic',
  },
  chartCard: {
    marginTop: 8,
  },
  scheduleSection: {
    marginTop: 8,
  },
  scheduleItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 12,
    paddingHorizontal: 4,
  },
  scheduleLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  scheduleInfo: {
    marginLeft: 12,
  },
  scheduleType: {
    fontSize: 15,
    fontWeight: '700',
  },
  scheduleTime: {
    fontSize: 13,
    marginTop: 2,
    fontWeight: '500',
  },
  scheduleRight: {
    alignItems: 'flex-end',
  },
  scheduleHeight: {
    fontSize: 15,
    fontWeight: '700',
  },
  scheduleRelative: {
    fontSize: 12,
    marginTop: 2,
    fontWeight: '500',
  },
  itemDivider: {
    height: 1,
    marginHorizontal: 4,
  },
  noDataText: {
    textAlign: 'center',
    paddingVertical: 20,
    fontSize: 14,
    fontWeight: '500',
  },
  moonSection: {
    marginTop: 8,
  },
  moonContent: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 8,
  },
  moonIconContainer: {
    width: 80,
    height: 80,
    borderRadius: 40,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 143, 0, 0.08)',
    marginRight: 16,
  },
  moonInfo: {
    flex: 1,
  },
  moonName: {
    fontSize: 18,
    fontWeight: '700',
  },
  moonIllumination: {
    fontSize: 14,
    marginTop: 4,
    fontWeight: '600',
  },
  moonDescription: {
    fontSize: 13,
    marginTop: 6,
    lineHeight: 18,
    fontWeight: '400',
  },
  infoSection: {
    marginTop: 8,
    marginBottom: 8,
  },
  infoContent: {
    padding: 4,
  },
  infoText: {
    fontSize: 14,
    lineHeight: 22,
    fontWeight: '400',
  },
  stationInfoBox: {
    flexDirection: 'row',
    marginTop: 14,
    padding: 14,
    borderRadius: 10,
  },
  stationIcon: {
    marginRight: 10,
    marginTop: 2,
  },
  stationInfoText: {
    flex: 1,
    fontSize: 13,
    lineHeight: 18,
    fontWeight: '400',
  },
  bottomSpacer: {
    height: 24,
  },
});
