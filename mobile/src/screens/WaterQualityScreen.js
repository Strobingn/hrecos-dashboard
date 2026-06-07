/**
 * WaterQualityScreen - Water quality and cleanliness assessment screen
 * Displays overall WQI gauge, swimming safety assessment, per-station
 * quality cards, and detailed parameter breakdowns.
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
import { useStations } from '../hooks/useStations';
import { useStationData } from '../hooks/useStationData';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorView from '../components/common/ErrorView';
import SectionHeader from '../components/common/SectionHeader';
import Card from '../components/common/Card';
import Badge from '../components/common/Badge';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

// ============================================================================
// Water Quality Calculation Helpers
// ============================================================================

function calculateWaterQualityIndex(readings) {
  if (!readings) return null;

  let score = 100;
  let paramCount = 0;

  // Dissolved Oxygen (ideal: 6-15 mg/L)
  if (readings.do) {
    const doVal = parseFloat(readings.do.value);
    if (doVal < 4) score -= 25;
    else if (doVal < 6) score -= 10;
    else if (doVal > 14) score -= 5;
    paramCount++;
  }

  // Turbidity (ideal: 0-10 NTU)
  if (readings.turbidity) {
    const turb = parseFloat(readings.turbidity.value);
    if (turb > 50) score -= 25;
    else if (turb > 25) score -= 15;
    else if (turb > 10) score -= 8;
    paramCount++;
  }

  // pH (ideal: 6.5-8.5)
  if (readings.ph) {
    const ph = parseFloat(readings.ph.value);
    if (ph < 6 || ph > 9) score -= 20;
    else if (ph < 6.5 || ph > 8.5) score -= 10;
    paramCount++;
  }

  // Temperature (ideal: 10-25 C)
  if (readings.temp) {
    const temp = parseFloat(readings.temp.value);
    if (temp > 30) score -= 15;
    else if (temp > 25) score -= 8;
    else if (temp < 5) score -= 10;
    paramCount++;
  }

  // Conductivity (ideal: 50-1500)
  if (readings.conductivity) {
    const cond = parseFloat(readings.conductivity.value);
    if (cond > 3000) score -= 10;
    else if (cond > 1500) score -= 5;
    paramCount++;
  }

  return paramCount > 0 ? Math.max(0, Math.min(100, score)) : null;
}

function getWQILabel(wqi) {
  if (wqi >= 90) return { label: 'Excellent', color: '#00BCD4', description: 'Water quality is excellent.' };
  if (wqi >= 70) return { label: 'Good', color: '#43A047', description: 'Water quality is good for most uses.' };
  if (wqi >= 50) return { label: 'Fair', color: '#FFB300', description: 'Water quality is acceptable but some concerns exist.' };
  if (wqi >= 30) return { label: 'Poor', color: '#FF9800', description: 'Water quality is degraded. Caution advised.' };
  return { label: 'Bad', color: '#E53935', description: 'Water quality is very poor. Avoid contact.' };
}

function getSwimmingSafety(wqi, readings) {
  if (!wqi || !readings) {
    return { level: 'UNKNOWN', label: 'No Data', icon: 'help-circle', color: '#8A96A5', description: 'Insufficient data to assess swimming safety.' };
  }

  // Check turbidity
  const turbidity = readings.turbidity ? parseFloat(readings.turbidity.value) : 0;
  const doVal = readings.do ? parseFloat(readings.do.value) : 10;

  if (wqi >= 80 && turbidity < 10 && doVal >= 6) {
    return {
      level: 'SAFE',
      label: 'Swimming Conditions: SAFE',
      icon: 'check-circle',
      color: '#43A047',
      description: 'Water is clear with good dissolved oxygen levels. Safe for recreational swimming.',
    };
  }
  if (wqi >= 50 && turbidity < 25 && doVal >= 4) {
    return {
      level: 'CAUTION',
      label: 'Swimming Conditions: CAUTION',
      icon: 'alert',
      color: '#FFB300',
      description: 'Water quality is fair. Swimming is generally okay but sensitive individuals should be cautious.',
    };
  }
  return {
    level: 'UNSAFE',
    label: 'Swimming Conditions: UNSAFE',
    icon: 'close-circle',
    color: '#E53935',
    description: turbidity >= 25
      ? 'High turbidity reduces visibility and may indicate contamination.'
      : 'Low dissolved oxygen or other quality concerns make swimming inadvisable.',
  };
}

function getWaterClarity(turbidity) {
  if (turbidity === null || turbidity === undefined) return { label: 'Unknown', color: '#8A96A5' };
  if (turbidity < 5) return { label: 'Crystal Clear', color: '#00BCD4' };
  if (turbidity < 15) return { label: 'Clean', color: '#43A047' };
  if (turbidity < 25) return { label: 'Slightly Murky', color: '#8BC34A' };
  if (turbidity < 50) return { label: 'Murky', color: '#FF9800' };
  return { label: 'Very Dirty', color: '#E53935' };
}

function getTurbidityBarColor(turbidity) {
  if (turbidity < 5) return '#00BCD4';
  if (turbidity < 15) return '#43A047';
  if (turbidity < 50) return '#FF9800';
  return '#E53935';
}

function getParameterStatus(value, param) {
  switch (param) {
    case 'do':
      if (value >= 8) return { label: 'Excellent', color: '#43A047' };
      if (value >= 6) return { label: 'Good', color: '#8BC34A' };
      if (value >= 4) return { label: 'Fair', color: '#FFB300' };
      return { label: 'Poor', color: '#E53935' };
    case 'ph':
      if (value >= 7 && value <= 8) return { label: 'Optimal', color: '#43A047' };
      if (value >= 6.5 && value <= 8.5) return { label: 'Good', color: '#8BC34A' };
      if (value >= 6 && value <= 9) return { label: 'Fair', color: '#FFB300' };
      return { label: 'Poor', color: '#E53935' };
    case 'temp':
      if (value >= 15 && value <= 25) return { label: 'Optimal', color: '#43A047' };
      if (value >= 10 && value <= 30) return { label: 'Good', color: '#8BC34A' };
      if (value >= 5 && value <= 35) return { label: 'Fair', color: '#FFB300' };
      return { label: 'Extreme', color: '#E53935' };
    case 'turbidity':
      if (value < 5) return { label: 'Crystal Clear', color: '#00BCD4' };
      if (value < 15) return { label: 'Clear', color: '#43A047' };
      if (value < 25) return { label: 'Slightly Cloudy', color: '#8BC34A' };
      if (value < 50) return { label: 'Cloudy', color: '#FF9800' };
      return { label: 'Very Cloudy', color: '#E53935' };
    default:
      return { label: 'Unknown', color: '#8A96A5' };
  }
}

// Circular gauge component for WQI
function WQIGauge({ score, size = 160 }) {
  const theme = useTheme();
  const label = getWQILabel(score);
  const strokeWidth = 12;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;

  return (
    <View style={[styles.gaugeContainer, { width: size, height: size }]}>
      <View style={[styles.gaugeBackground, { width: size, height: size }]}>
        {/* Background ring */}
        <View
          style={[
            styles.gaugeRing,
            {
              width: size,
              height: size,
              borderRadius: size / 2,
              borderWidth: strokeWidth,
              borderColor: theme.colors.divider,
            },
          ]}
        />
        {/* Progress arc - using a simple approach with border trick */}
        <View
          style={[
            styles.gaugeProgress,
            {
              width: size,
              height: size,
              borderRadius: size / 2,
              borderWidth: strokeWidth,
              borderColor: label.color,
              borderLeftColor: 'transparent',
              borderBottomColor: 'transparent',
              transform: [
                { rotate: `${-45 + (score / 100) * 360}deg` },
              ],
            },
          ]}
        />
      </View>
      <View style={styles.gaugeContent}>
        <Text style={[styles.gaugeScore, { color: theme.colors.textPrimary || theme.colors.text }]}>
          {score !== null ? Math.round(score) : '--'}
        </Text>
        <Text style={[styles.gaugeLabel, { color: label.color }]}>{label.label}</Text>
      </View>
    </View>
  );
}

// Mini WQI indicator (number badge style)
function MiniWQI({ score }) {
  const label = getWQILabel(score);
  return (
    <View style={[styles.miniWQI, { backgroundColor: label.color + '20', borderColor: label.color }]}>
      <Text style={[styles.miniWQIText, { color: label.color }]}>
        {score !== null ? Math.round(score) : '--'}
      </Text>
    </View>
  );
}

// Horizontal bar indicator
function ParameterBar({ label, value, unit, min, max, optimalMin, optimalMax, color }) {
  const theme = useTheme();
  const clampedValue = Math.max(min, Math.min(max, value));
  const percentage = ((clampedValue - min) / (max - min)) * 100;
  const isOptimal = value >= optimalMin && value <= optimalMax;

  return (
    <View style={styles.paramBarContainer}>
      <View style={styles.paramBarHeader}>
        <Text style={[styles.paramBarLabel, { color: theme.colors.textPrimary || theme.colors.text }]}>
          {label}
        </Text>
        <Text style={[styles.paramBarValue, { color: isOptimal ? (theme.colors.success || '#43A047') : theme.colors.textSecondary }]}>
          {value.toFixed(1)}{unit}
        </Text>
      </View>
      <View style={[styles.paramBarTrack, { backgroundColor: theme.colors.divider }]}>
        <View
          style={[
            styles.paramBarFill,
            {
              width: `${percentage}%`,
              backgroundColor: isOptimal ? (theme.colors.success || '#43A047') : (color || theme.colors.warning || '#FFB300'),
            },
          ]}
        />
      </View>
      <View style={styles.paramBarRange}>
        <Text style={[styles.paramBarRangeText, { color: theme.colors.textSecondary }]}>
          Optimal: {optimalMin}-{optimalMax}{unit}
        </Text>
      </View>
    </View>
  );
}

export default function WaterQualityScreen() {
  const theme = useTheme();
  const { stations, loading: stationsLoading, error: stationsError, refetch: refetchStations } = useStations();
  const { data: schodackData, loading: schodackLoading, error: schodackError, refetch: refetchSchodack } = useStationData('schodack');
  const [refreshing, setRefreshing] = useState(false);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await Promise.all([refetchStations(), refetchSchodack()]);
    setRefreshing(false);
  }, [refetchStations, refetchSchodack]);

  // Calculate average WQI across all live stations
  const overallWQI = useMemo(() => {
    if (!stations || stations.length === 0) return null;
    const liveStations = stations.filter((s) => s.status === 'live');
    let totalWQI = 0;
    let count = 0;
    liveStations.forEach((station) => {
      const wqi = calculateWaterQualityIndex(station.readings);
      if (wqi !== null) {
        totalWQI += wqi;
        count++;
      }
    });
    return count > 0 ? totalWQI / count : null;
  }, [stations]);

  const wqiLabel = useMemo(() => getWQILabel(overallWQI || 0), [overallWQI]);

  // Swimming safety based on schodack data
  const swimmingSafety = useMemo(() => {
    if (schodackData?.readings) {
      const schodackWQI = calculateWaterQualityIndex(schodackData.readings);
      return getSwimmingSafety(schodackWQI, schodackData.readings);
    }
    return getSwimmingSafety(null, null);
  }, [schodackData]);

  // Live stations for per-station cards
  const liveStations = useMemo(() => {
    if (!stations) return [];
    return stations.filter((s) => s.status === 'live');
  }, [stations]);

  const loading = stationsLoading && schodackLoading;
  const hasError = stationsError && schodackError;

  if (loading && !stations?.length) {
    return (
      <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
        <LoadingSpinner message="Loading water quality data..." />
      </View>
    );
  }

  if (hasError && !stations?.length) {
    return (
      <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
        <ErrorView message={stationsError || 'Failed to load data'} onRetry={onRefresh} />
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
          Water Quality
        </Text>
        <Text style={[styles.headerSubtitle, { color: theme.colors.textSecondary }]}>
          River cleanliness &amp; safety assessment
        </Text>
      </View>

      {/* Overall Quality Gauge */}
      <Card variant="elevated" style={styles.gaugeCard}>
        <View style={styles.gaugeWrapper}>
          <WQIGauge score={overallWQI || 0} />
          <Text style={[styles.wqiLabel, { color: wqiLabel.color }]}>
            {wqiLabel.label}
          </Text>
          <Text style={[styles.wqiDescription, { color: theme.colors.textSecondary }]}>
            {wqiLabel.description}
          </Text>
          <Text style={[styles.wqiSubtext, { color: theme.colors.textSecondary }]}>
            Based on turbidity, dissolved oxygen, pH, and temperature readings
          </Text>
        </View>
      </Card>

      {/* Swimming Safety Card */}
      <Card style={styles.safetyCard}>
        <View style={[styles.safetyContent, { borderLeftColor: swimmingSafety.color, borderLeftWidth: 4 }]}>
          <View style={styles.safetyIconRow}>
            <MaterialCommunityIcons
              name={swimmingSafety.icon}
              size={48}
              color={swimmingSafety.color}
            />
            <View style={styles.safetyTextContainer}>
              <Text style={[styles.safetyLabel, { color: swimmingSafety.color }]}>
                {swimmingSafety.label}
              </Text>
              <Text style={[styles.safetyDescription, { color: theme.colors.textSecondary }]}>
                {swimmingSafety.description}
              </Text>
            </View>
          </View>
        </View>
      </Card>

      {/* Per-Station Quality Cards */}
      <SectionHeader
        title="Station Quality Details"
        icon="gauge"
        subtitle={`${liveStations.length} active monitoring stations`}
      />
      {liveStations.map((station) => {
        const wqi = calculateWaterQualityIndex(station.readings);
        const turbidity = station.readings?.turbidity
          ? parseFloat(station.readings.turbidity.value)
          : null;
        const clarity = getWaterClarity(turbidity);

        return (
          <Card key={station.id} style={styles.stationCard}>
            <View style={styles.stationHeader}>
              <View style={styles.stationNameRow}>
                <MaterialCommunityIcons
                  name="broadcast"
                  size={18}
                  color={theme.colors.primary}
                />
                <Text style={[styles.stationName, { color: theme.colors.textPrimary || theme.colors.text }]}>
                  {station.name}
                </Text>
              </View>
              {wqi !== null && <MiniWQI score={wqi} />}
            </View>

            {/* Turbidity meter */}
            {turbidity !== null && (
              <View style={styles.turbiditySection}>
                <View style={styles.turbidityHeader}>
                  <Text style={[styles.turbidityLabel, { color: theme.colors.textSecondary }]}>
                    Water Clarity
                  </Text>
                  <Badge
                    label={clarity.label}
                    color={clarity.color}
                    size="small"
                  />
                </View>
                <View style={[styles.turbidityBarTrack, { backgroundColor: theme.colors.divider }]}>
                  <View
                    style={[
                      styles.turbidityBarFill,
                      {
                        width: `${Math.min(100, (turbidity / 60) * 100)}%`,
                        backgroundColor: getTurbidityBarColor(turbidity),
                      },
                    ]}
                  />
                </View>
                <Text style={[styles.turbidityValue, { color: theme.colors.textSecondary }]}>
                  {turbidity.toFixed(1)} NTU
                </Text>
              </View>
            )}

            {/* Available parameters */}
            {station.readings && Object.keys(station.readings).length > 0 && (
              <View style={styles.paramsGrid}>
                {Object.entries(station.readings).map(([key, reading]) => {
                  const status = getParameterStatus(parseFloat(reading.value), key);
                  return (
                    <View key={key} style={styles.paramItem}>
                      <Text style={[styles.paramKey, { color: theme.colors.textSecondary }]}>
                        {reading.label || key}
                      </Text>
                      <Text style={[styles.paramValue, { color: theme.colors.textPrimary || theme.colors.text }]}>
                        {reading.value} {reading.unit}
                      </Text>
                      <Badge label={status.label} color={status.color} size="small" />
                    </View>
                  );
                })}
              </View>
            )}
          </Card>
        );
      })}

      {/* Parameter Breakdown for Schodack */}
      {schodackData?.readings && (
        <View style={styles.breakdownSection}>
          <SectionHeader
            title="Parameter Details"
            icon="flask"
            subtitle="Schodack Island station"
          />
          <Card>
            <View style={styles.breakdownContent}>
              {schodackData.readings.do && (
                <ParameterBar
                  label="Dissolved Oxygen"
                  value={parseFloat(schodackData.readings.do.value)}
                  unit=" mg/L"
                  min={0}
                  max={15}
                  optimalMin={6}
                  optimalMax={14}
                  color="#3498DB"
                />
              )}
              {schodackData.readings.ph && (
                <ParameterBar
                  label="pH Balance"
                  value={parseFloat(schodackData.readings.ph.value)}
                  unit=""
                  min={4}
                  max={10}
                  optimalMin={6.5}
                  optimalMax={8.5}
                  color="#2ECC71"
                />
              )}
              {schodackData.readings.temp && (
                <ParameterBar
                  label="Water Temperature"
                  value={parseFloat(schodackData.readings.temp.value)}
                  unit="°C"
                  min={0}
                  max={40}
                  optimalMin={10}
                  optimalMax={25}
                  color="#E74C3C"
                />
              )}
              {schodackData.readings.turbidity && (
                <ParameterBar
                  label="Turbidity"
                  value={parseFloat(schodackData.readings.turbidity.value)}
                  unit=" NTU"
                  min={0}
                  max={60}
                  optimalMin={0}
                  optimalMax={10}
                  color="#8E44AD"
                />
              )}
              {schodackData.readings.conductivity && (
                <ParameterBar
                  label="Conductivity"
                  value={parseFloat(schodackData.readings.conductivity.value)}
                  unit=" μS/cm"
                  min={0}
                  max={1000}
                  optimalMin={50}
                  optimalMax={500}
                  color="#F39C12"
                />
              )}
            </View>
          </Card>
        </View>
      )}

      {/* Error message if schodack failed but stations loaded */}
      {schodackError && (
        <ErrorView
          message={schodackError}
          onRetry={refetchSchodack}
          icon="flask-outline"
        />
      )}

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
  gaugeCard: {
    marginHorizontal: 16,
    marginBottom: 8,
  },
  gaugeWrapper: {
    alignItems: 'center',
    padding: 20,
  },
  gaugeContainer: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  gaugeBackground: {
    position: 'absolute',
    justifyContent: 'center',
    alignItems: 'center',
  },
  gaugeRing: {
    position: 'absolute',
  },
  gaugeProgress: {
    position: 'absolute',
  },
  gaugeContent: {
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1,
  },
  gaugeScore: {
    fontSize: 36,
    fontWeight: '800',
  },
  gaugeLabel: {
    fontSize: 13,
    fontWeight: '700',
    marginTop: 2,
  },
  wqiLabel: {
    fontSize: 20,
    fontWeight: '700',
    marginTop: 16,
  },
  wqiDescription: {
    fontSize: 14,
    textAlign: 'center',
    marginTop: 6,
    paddingHorizontal: 20,
    lineHeight: 20,
  },
  wqiSubtext: {
    fontSize: 12,
    textAlign: 'center',
    marginTop: 8,
    fontWeight: '400',
  },
  safetyCard: {
    marginHorizontal: 16,
    marginVertical: 8,
  },
  safetyContent: {
    padding: 16,
    borderRadius: 12,
  },
  safetyIconRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  safetyTextContainer: {
    marginLeft: 16,
    flex: 1,
  },
  safetyLabel: {
    fontSize: 16,
    fontWeight: '700',
  },
  safetyDescription: {
    fontSize: 13,
    marginTop: 4,
    lineHeight: 18,
    fontWeight: '400',
  },
  stationCard: {
    marginHorizontal: 16,
    marginVertical: 6,
  },
  stationHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  stationNameRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  stationName: {
    fontSize: 16,
    fontWeight: '700',
    marginLeft: 8,
  },
  miniWQI: {
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
  },
  miniWQIText: {
    fontSize: 16,
    fontWeight: '800',
  },
  turbiditySection: {
    marginBottom: 12,
  },
  turbidityHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  turbidityLabel: {
    fontSize: 13,
    fontWeight: '600',
  },
  turbidityBarTrack: {
    height: 8,
    borderRadius: 4,
    overflow: 'hidden',
  },
  turbidityBarFill: {
    height: '100%',
    borderRadius: 4,
  },
  turbidityValue: {
    fontSize: 12,
    marginTop: 4,
    fontWeight: '500',
  },
  paramsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: 8,
  },
  paramItem: {
    width: '50%',
    paddingVertical: 8,
    paddingRight: 8,
  },
  paramKey: {
    fontSize: 12,
    fontWeight: '500',
  },
  paramValue: {
    fontSize: 14,
    fontWeight: '700',
    marginTop: 2,
    marginBottom: 4,
  },
  breakdownSection: {
    marginTop: 8,
  },
  breakdownContent: {
    padding: 8,
  },
  paramBarContainer: {
    marginBottom: 18,
  },
  paramBarHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  paramBarLabel: {
    fontSize: 14,
    fontWeight: '600',
  },
  paramBarValue: {
    fontSize: 14,
    fontWeight: '700',
  },
  paramBarTrack: {
    height: 10,
    borderRadius: 5,
    overflow: 'hidden',
  },
  paramBarFill: {
    height: '100%',
    borderRadius: 5,
  },
  paramBarRange: {
    marginTop: 4,
  },
  paramBarRangeText: {
    fontSize: 11,
    fontWeight: '400',
  },
  bottomSpacer: {
    height: 24,
  },
});
