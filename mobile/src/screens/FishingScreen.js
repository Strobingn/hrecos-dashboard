/**
 * FishingScreen - Fishing conditions predictor screen
 * Displays an overall fishing score, score breakdown by factors,
 * best fishing times, current conditions summary, and dynamic tips.
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
import { useTides } from '../hooks/useTides';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorView from '../components/common/ErrorView';
import SectionHeader from '../components/common/SectionHeader';
import Card from '../components/common/Card';
import Badge from '../components/common/Badge';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

// ============================================================================
// Fishing Score Calculation Helpers
// ============================================================================

function calculateFishingScore(stationData, tidesData) {
  let totalScore = 0;
  let factorCount = 0;

  const breakdown = {
    temperature: { score: 0, label: '', max: 100 },
    clarity: { score: 0, label: '', max: 100 },
    flow: { score: 0, label: '', max: 100 },
    tide: { score: 0, label: '', max: 100 },
    timeOfDay: { score: 0, label: '', max: 100 },
  };

  if (!stationData?.readings) {
    return { totalScore: null, breakdown, rating: 'No Data' };
  }

  const readings = stationData.readings;

  // Water Temperature Score (ideal: 55-75 F / 13-24 C)
  if (readings.temp) {
    const tempC = parseFloat(readings.temp.value);
    const tempF = (tempC * 9) / 5 + 32;
    if (tempF >= 60 && tempF <= 75) {
      breakdown.temperature.score = 95;
      breakdown.temperature.label = `${Math.round(tempF)}°F - Ideal`;
    } else if (tempF >= 55 && tempF <= 80) {
      breakdown.temperature.score = 80;
      breakdown.temperature.label = `${Math.round(tempF)}°F - Good`;
    } else if (tempF >= 50 && tempF <= 85) {
      breakdown.temperature.score = 60;
      breakdown.temperature.label = `${Math.round(tempF)}°F - Fair`;
    } else {
      breakdown.temperature.score = 30;
      breakdown.temperature.label = `${Math.round(tempF)}°F - Poor`;
    }
    totalScore += breakdown.temperature.score;
    factorCount++;
  } else {
    breakdown.temperature.label = 'No data';
  }

  // Water Clarity Score (based on turbidity - lower is better)
  if (readings.turbidity) {
    const turb = parseFloat(readings.turbidity.value);
    if (turb < 5) {
      breakdown.clarity.score = 90;
      breakdown.clarity.label = `${turb.toFixed(1)} NTU - Excellent Visibility`;
    } else if (turb < 15) {
      breakdown.clarity.score = 80;
      breakdown.clarity.label = `${turb.toFixed(1)} NTU - Good Visibility`;
    } else if (turb < 25) {
      breakdown.clarity.score = 60;
      breakdown.clarity.label = `${turb.toFixed(1)} NTU - Moderate Visibility`;
    } else if (turb < 50) {
      breakdown.clarity.score = 40;
      breakdown.clarity.label = `${turb.toFixed(1)} NTU - Low Visibility`;
    } else {
      breakdown.clarity.score = 20;
      breakdown.clarity.label = `${turb.toFixed(1)} NTU - Very Poor Visibility`;
    }
    totalScore += breakdown.clarity.score;
    factorCount++;
  } else {
    breakdown.clarity.label = 'No data';
  }

  // Flow/Speed Score (ideal: 0.5-1.5 m/s)
  if (readings.speed) {
    const speed = parseFloat(readings.speed.value);
    if (speed >= 0.5 && speed <= 1.5) {
      breakdown.flow.score = 95;
      breakdown.flow.label = `${speed.toFixed(1)} m/s - Optimal`;
    } else if (speed >= 0.3 && speed <= 2.0) {
      breakdown.flow.score = 75;
      breakdown.flow.label = `${speed.toFixed(1)} m/s - Good`;
    } else if (speed < 0.3) {
      breakdown.flow.score = 55;
      breakdown.flow.label = `${speed.toFixed(1)} m/s - Slow`;
    } else {
      breakdown.flow.score = 40;
      breakdown.flow.label = `${speed.toFixed(1)} m/s - Fast`;
    }
    totalScore += breakdown.flow.score;
    factorCount++;
  } else {
    // Estimate from depth changes if no speed
    breakdown.flow.score = 70;
    breakdown.flow.label = 'Moderate - Estimated';
    totalScore += 70;
    factorCount++;
  }

  // Tide Phase Score
  if (tidesData?.current?.phase) {
    const phase = tidesData.current.phase;
    if (phase === 'rising') {
      breakdown.tide.score = 95;
      breakdown.tide.label = 'Incoming Tide - Excellent';
    } else if (phase === 'falling') {
      breakdown.tide.score = 75;
      breakdown.tide.label = 'Outgoing Tide - Good';
    } else if (phase === 'high') {
      breakdown.tide.score = 60;
      breakdown.tide.label = 'High Tide - Fair';
    } else {
      breakdown.tide.score = 50;
      breakdown.tide.label = 'Low Tide - Fair';
    }
    totalScore += breakdown.tide.score;
    factorCount++;
  } else {
    breakdown.tide.label = 'No tide data';
  }

  // Time of Day Score
  const hour = new Date().getHours();
  if ((hour >= 5 && hour <= 9) || (hour >= 17 && hour <= 20)) {
    breakdown.timeOfDay.score = 90;
    breakdown.timeOfDay.label = `${getTimeOfDayName(hour)} - Prime Time`;
  } else if (hour >= 10 && hour <= 16) {
    breakdown.timeOfDay.score = 60;
    breakdown.timeOfDay.label = `${getTimeOfDayName(hour)} - Moderate`;
  } else {
    breakdown.timeOfDay.score = 40;
    breakdown.timeOfDay.label = `${getTimeOfDayName(hour)} - Off Peak`;
  }
  totalScore += breakdown.timeOfDay.score;
  factorCount++;

  const avgScore = factorCount > 0 ? Math.round(totalScore / factorCount) : null;

  return {
    totalScore: avgScore,
    breakdown,
    rating: getFishingRating(avgScore),
  };
}

function getTimeOfDayName(hour) {
  if (hour >= 5 && hour < 12) return 'Morning';
  if (hour >= 12 && hour < 17) return 'Afternoon';
  if (hour >= 17 && hour < 21) return 'Evening';
  return 'Night';
}

function getFishingRating(score) {
  if (score === null) return 'No Data';
  if (score >= 90) return 'Excellent';
  if (score >= 75) return 'Great';
  if (score >= 60) return 'Good';
  if (score >= 40) return 'Fair';
  return 'Poor';
}

function getScoreColor(score) {
  if (score >= 80) return '#43A047';
  if (score >= 60) return '#8BC34A';
  if (score >= 40) return '#FFB300';
  return '#E53935';
}

// ============================================================================
// Sub-components
// ============================================================================

function FishingScoreGauge({ score }) {
  const theme = useTheme();
  const rating = getFishingRating(score);
  const color = getScoreColor(score || 0);

  return (
    <View style={styles.scoreGaugeContainer}>
      <View style={[styles.scoreCircleOuter, { borderColor: color + '30' }]}>
        <View style={[styles.scoreCircle, { borderColor: color }]}>
          <Text style={[styles.scoreNumber, { color: theme.colors.textPrimary || theme.colors.text }]}>
            {score !== null ? score : '--'}
          </Text>
        </View>
      </View>
      <Text style={[styles.scoreRating, { color }]}>{rating}</Text>
      <Text style={[styles.scoreSubtitle, { color: theme.colors.textSecondary }]}>
        Overall Fishing Score
      </Text>
    </View>
  );
}

function ScoreBreakdownBar({ label, score, description, icon }) {
  const theme = useTheme();
  const color = getScoreColor(score || 0);

  return (
    <View style={styles.breakdownItem}>
      <View style={styles.breakdownHeader}>
        <View style={styles.breakdownLabelRow}>
          <MaterialCommunityIcons name={icon} size={18} color={color} style={styles.breakdownIcon} />
          <Text style={[styles.breakdownLabel, { color: theme.colors.textPrimary || theme.colors.text }]}>
            {label}
          </Text>
        </View>
        <Text style={[styles.breakdownPercentage, { color }]}>
          {score !== null ? `${score}%` : '--'}
        </Text>
      </View>
      <View style={[styles.breakdownTrack, { backgroundColor: theme.colors.divider }]}>
        <View
          style={[
            styles.breakdownFill,
            { width: `${score || 0}%`, backgroundColor: color },
          ]}
        />
      </View>
      <Text style={[styles.breakdownDesc, { color: theme.colors.textSecondary }]}>
        {description}
      </Text>
    </View>
  );
}

function BestTimeItem({ icon, timeRange, label, rating }) {
  const theme = useTheme();
  const ratingColor = getScoreColor(rating === 'Excellent' ? 95 : rating === 'Great' ? 80 : 70);

  return (
    <View style={styles.bestTimeItem}>
      <View style={[styles.bestTimeIconBox, { backgroundColor: ratingColor + '15' }]}>
        <MaterialCommunityIcons name={icon} size={24} color={ratingColor} />
      </View>
      <View style={styles.bestTimeInfo}>
        <Text style={[styles.bestTimeRange, { color: theme.colors.textPrimary || theme.colors.text }]}>
          {timeRange}
        </Text>
        <Text style={[styles.bestTimeLabel, { color: theme.colors.textSecondary }]}>
          {label}
        </Text>
      </View>
      <Badge label={rating} color={ratingColor} size="small" />
    </View>
  );
}

function MetricGridItem({ icon, label, value, color }) {
  const theme = useTheme();
  return (
    <View style={styles.metricItem}>
      <MaterialCommunityIcons name={icon} size={22} color={color || theme.colors.primary} />
      <Text style={[styles.metricValue, { color: theme.colors.textPrimary || theme.colors.text }]}>
        {value}
      </Text>
      <Text style={[styles.metricLabel, { color: theme.colors.textSecondary }]}>
        {label}
      </Text>
    </View>
  );
}

export default function FishingScreen() {
  const theme = useTheme();
  const FISHING_STATION = 'turkey_point';
  const { data: stationData, loading: stationLoading, error: stationError, refetch: refetchStation } = useStationData(FISHING_STATION);
  const { data: tidesData, loading: tidesLoading, error: tidesError, refetch: refetchTides } = useTides();
  const { stations } = useStations();
  const [refreshing, setRefreshing] = useState(false);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await Promise.all([refetchStation(), refetchTides()]);
    setRefreshing(false);
  }, [refetchStation, refetchTides]);

  // Calculate fishing score
  const fishingResult = useMemo(() => {
    return calculateFishingScore(stationData, tidesData);
  }, [stationData, tidesData]);

  // Best fishing windows (mock data - in real app would calculate from conditions)
  const bestTimes = useMemo(() => {
    const now = new Date();
    const hour = now.getHours();
    const times = [];

    if (hour < 12) {
      times.push({ icon: 'weather-sunset-up', timeRange: '6:00 AM - 9:00 AM', label: 'Dawn bite', rating: 'Excellent', score: 95 });
    }
    if (hour < 18) {
      times.push({ icon: 'weather-sunny', timeRange: '12:00 PM - 2:00 PM', label: 'Midday bite', rating: 'Fair', score: 60 });
    }
    times.push({ icon: 'weather-sunset-down', timeRange: '5:30 PM - 8:30 PM', label: 'Dusk bite', rating: 'Great', score: 85 });

    return times;
  }, []);

  // Current conditions
  const currentConditions = useMemo(() => {
    const conditions = [];
    if (stationData?.readings?.temp) {
      const tempC = parseFloat(stationData.readings.temp.value);
      const tempF = (tempC * 9) / 5 + 32;
      conditions.push({
        icon: 'thermometer',
        label: 'Water Temp',
        value: `${Math.round(tempF)}°F`,
        color: '#E74C3C',
      });
    }
    if (stationData?.readings?.turbidity) {
      const turb = parseFloat(stationData.readings.turbidity.value);
      let clarityLabel = 'Clear';
      if (turb < 5) clarityLabel = 'Crystal Clear';
      else if (turb < 15) clarityLabel = 'Clear';
      else if (turb < 25) clarityLabel = 'Cloudy';
      else clarityLabel = 'Murky';
      conditions.push({
        icon: 'water-opacity',
        label: 'Clarity',
        value: `${clarityLabel} (${turb.toFixed(0)} NTU)`,
        color: '#3498DB',
      });
    }
    if (stationData?.readings?.speed) {
      const speed = parseFloat(stationData.readings.speed.value);
      conditions.push({
        icon: 'waves',
        label: 'Flow',
        value: `${speed.toFixed(1)} m/s`,
        color: '#2ECC71',
      });
    }
    if (tidesData?.current) {
      const phaseLabel = tidesData.current.phase === 'rising'
        ? 'Incoming'
        : tidesData.current.phase === 'falling'
        ? 'Outgoing'
        : tidesData.current.phase === 'high'
        ? 'High'
        : 'Low';
      conditions.push({
        icon: 'waves-arrow-up',
        label: 'Tide',
        value: `${phaseLabel} (${tidesData.current.height.toFixed(1)} ft)`,
        color: '#9B59B6',
      });
    }
    return conditions;
  }, [stationData, tidesData]);

  // Dynamic fishing tips
  const tips = useMemo(() => {
    const tipsList = [];

    if (stationData?.readings?.temp) {
      const tempC = parseFloat(stationData.readings.temp.value);
      const tempF = (tempC * 9) / 5 + 32;
      if (tempF >= 60 && tempF <= 75) {
        tipsList.push({
          icon: 'thermometer',
          text: 'Water temperature is in the ideal range for bass fishing. Target areas with structure.',
          color: '#43A047',
        });
      } else if (tempF > 80) {
        tipsList.push({
          icon: 'thermometer',
          text: 'Water is warm - fish deeper areas where oxygen levels are better.',
          color: '#FFB300',
        });
      }
    }

    if (stationData?.readings?.speed) {
      const speed = parseFloat(stationData.readings.speed.value);
      if (speed > 1.5) {
        tipsList.push({
          icon: 'waves',
          text: 'High water flow - try fishing near eddies and calmer areas behind structures.',
          color: '#E53935',
        });
      } else if (speed < 0.3) {
        tipsList.push({
          icon: 'waves',
          text: 'Low flow - fish may be lethargic. Use slow presentations.',
          color: '#FFB300',
        });
      }
    }

    if (stationData?.readings?.turbidity) {
      const turb = parseFloat(stationData.readings.turbidity.value);
      if (turb > 25) {
        tipsList.push({
          icon: 'water-opacity',
          text: 'Murky water - use lures that create vibration or noise. Fish closer than usual.',
          color: '#E53935',
        });
      } else if (turb < 5) {
        tipsList.push({
          icon: 'water-opacity',
          text: 'Crystal clear water - use natural-colored lures and lighter line.',
          color: '#43A047',
        });
      }
    }

    if (tidesData?.current?.phase === 'rising') {
      tipsList.push({
        icon: 'waves-arrow-up',
        text: 'Incoming tide brings in baitfish - fish near structures and channel edges.',
        color: '#43A047',
      });
    }

    if (tipsList.length === 0) {
      tipsList.push({
        icon: 'fish',
        text: 'Conditions are variable. Try a mix of techniques and adjust based on what you observe.',
        color: theme.colors.primary,
      });
    }

    return tipsList;
  }, [stationData, tidesData, theme.colors.primary]);

  const loading = stationLoading && tidesLoading;
  const hasDataError = stationError && !stationData;

  if (loading && !stationData) {
    return (
      <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
        <LoadingSpinner message="Loading fishing conditions..." />
      </View>
    );
  }

  if (hasDataError) {
    return (
      <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
        <ErrorView
          message={stationError || 'Turkey Point station data is unavailable. Fishing scores use the nearest live water sensor upstream of West Point.'}
          onRetry={onRefresh}
        />
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
          Fishing Conditions
        </Text>
        <Text style={[styles.headerSubtitle, { color: theme.colors.textSecondary }]}>
          Real-time fishing score for the Hudson River
        </Text>
      </View>

      {/* Fishing Score Gauge */}
      <Card variant="elevated" style={styles.scoreCard}>
        <FishingScoreGauge score={fishingResult.totalScore} />
      </Card>

      {/* Score Breakdown Bars */}
      <View style={styles.breakdownSection}>
        <SectionHeader title="Score Breakdown" icon="chart-bar" />
        <Card>
          <ScoreBreakdownBar
            label="Water Temperature"
            score={fishingResult.breakdown.temperature.score}
            description={fishingResult.breakdown.temperature.label}
            icon="thermometer"
          />
          <ScoreBreakdownBar
            label="Water Clarity"
            score={fishingResult.breakdown.clarity.score}
            description={fishingResult.breakdown.clarity.label}
            icon="water-opacity"
          />
          <ScoreBreakdownBar
            label="Water Flow"
            score={fishingResult.breakdown.flow.score}
            description={fishingResult.breakdown.flow.label}
            icon="waves"
          />
          <ScoreBreakdownBar
            label="Tide Phase"
            score={fishingResult.breakdown.tide.score}
            description={fishingResult.breakdown.tide.label}
            icon="waves-arrow-up"
          />
          <ScoreBreakdownBar
            label="Time of Day"
            score={fishingResult.breakdown.timeOfDay.score}
            description={fishingResult.breakdown.timeOfDay.label}
            icon="clock-outline"
          />
        </Card>
      </View>

      {/* Best Fishing Times */}
      <View style={styles.bestTimesSection}>
        <SectionHeader title="Best Times Today" icon="clock-star-outline" />
        <Card>
          {bestTimes.map((time, index) => (
            <BestTimeItem
              key={index}
              icon={time.icon}
              timeRange={time.timeRange}
              label={time.label}
              rating={time.rating}
            />
          ))}
        </Card>
      </View>

      {/* Current Conditions Summary */}
      <View style={styles.conditionsSection}>
        <SectionHeader title="Current Conditions" icon="gauge" />
        <Card>
          {currentConditions.length > 0 ? (
            <View style={styles.conditionsGrid}>
              {currentConditions.map((cond, index) => (
                <MetricGridItem
                  key={index}
                  icon={cond.icon}
                  label={cond.label}
                  value={cond.value}
                  color={cond.color}
                />
              ))}
            </View>
          ) : (
            <Text style={[styles.noDataText, { color: theme.colors.textSecondary }]}>
              No condition data available
            </Text>
          )}
        </Card>
      </View>

      {/* Fishing Tips */}
      <View style={styles.tipsSection}>
        <SectionHeader title="Fishing Tips" icon="lightbulb-on-outline" />
        <Card>
          {tips.map((tip, index) => (
            <View
              key={index}
              style={[
                styles.tipItem,
                index < tips.length - 1 && styles.tipItemBorder,
                { borderBottomColor: theme.colors.divider },
              ]}
            >
              <View style={[styles.tipIconBox, { backgroundColor: tip.color + '12' }]}>
                <MaterialCommunityIcons name={tip.icon} size={22} color={tip.color} />
              </View>
              <Text style={[styles.tipText, { color: theme.colors.textPrimary || theme.colors.text }]}>
                {tip.text}
              </Text>
            </View>
          ))}
        </Card>
      </View>

      {/* Data source note */}
      <View style={styles.sourceNote}>
        <MaterialCommunityIcons name="information-outline" size={14} color={theme.colors.textSecondary} />
        <Text style={[styles.sourceNoteText, { color: theme.colors.textSecondary }]}>
          Fishing scores use Turkey Point water data (nearest live sensor) and Newburgh tide predictions for Cornwall-on-Hudson.
        </Text>
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
  scoreCard: {
    marginHorizontal: 16,
    marginBottom: 8,
  },
  scoreGaugeContainer: {
    alignItems: 'center',
    padding: 20,
  },
  scoreCircleOuter: {
    width: 160,
    height: 160,
    borderRadius: 80,
    borderWidth: 4,
    justifyContent: 'center',
    alignItems: 'center',
  },
  scoreCircle: {
    width: 130,
    height: 130,
    borderRadius: 65,
    borderWidth: 4,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'transparent',
  },
  scoreNumber: {
    fontSize: 44,
    fontWeight: '800',
  },
  scoreRating: {
    fontSize: 22,
    fontWeight: '700',
    marginTop: 14,
  },
  scoreSubtitle: {
    fontSize: 13,
    marginTop: 4,
    fontWeight: '400',
  },
  breakdownSection: {
    marginTop: 8,
  },
  breakdownItem: {
    marginBottom: 16,
    paddingHorizontal: 4,
  },
  breakdownHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  breakdownLabelRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  breakdownIcon: {
    marginRight: 8,
  },
  breakdownLabel: {
    fontSize: 14,
    fontWeight: '600',
  },
  breakdownPercentage: {
    fontSize: 14,
    fontWeight: '700',
  },
  breakdownTrack: {
    height: 10,
    borderRadius: 5,
    overflow: 'hidden',
  },
  breakdownFill: {
    height: '100%',
    borderRadius: 5,
  },
  breakdownDesc: {
    fontSize: 12,
    marginTop: 4,
    fontWeight: '400',
  },
  bestTimesSection: {
    marginTop: 8,
  },
  bestTimeItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
  },
  bestTimeIconBox: {
    width: 44,
    height: 44,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 14,
  },
  bestTimeInfo: {
    flex: 1,
  },
  bestTimeRange: {
    fontSize: 15,
    fontWeight: '700',
  },
  bestTimeLabel: {
    fontSize: 13,
    marginTop: 2,
    fontWeight: '400',
  },
  conditionsSection: {
    marginTop: 8,
  },
  conditionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    padding: 8,
  },
  metricItem: {
    width: '50%',
    paddingVertical: 14,
    paddingHorizontal: 8,
    alignItems: 'center',
  },
  metricValue: {
    fontSize: 15,
    fontWeight: '700',
    marginTop: 6,
  },
  metricLabel: {
    fontSize: 12,
    marginTop: 2,
    fontWeight: '400',
  },
  noDataText: {
    textAlign: 'center',
    paddingVertical: 20,
    fontSize: 14,
    fontWeight: '500',
  },
  tipsSection: {
    marginTop: 8,
  },
  tipItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingVertical: 12,
    paddingHorizontal: 4,
  },
  tipItemBorder: {
    borderBottomWidth: 1,
  },
  tipIconBox: {
    width: 40,
    height: 40,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
    marginTop: 2,
  },
  tipText: {
    flex: 1,
    fontSize: 14,
    lineHeight: 20,
    fontWeight: '400',
  },
  sourceNote: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginHorizontal: 24,
    marginTop: 16,
    paddingHorizontal: 4,
  },
  sourceNoteText: {
    fontSize: 12,
    marginLeft: 8,
    lineHeight: 16,
    flex: 1,
  },
  bottomSpacer: {
    height: 24,
  },
});
