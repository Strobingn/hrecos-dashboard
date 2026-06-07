import React, { useState, useCallback, useMemo } from 'react';
import {
  View,
  Text,
  ScrollView,
  RefreshControl,
  StyleSheet,
  TouchableOpacity,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useNavigation, useRoute } from '@react-navigation/native';
import { useTheme } from '../hooks/useTheme';
import { useStationData } from '../hooks/useStationData';
import { useHistorical } from '../hooks/useHistorical';
import { useStats } from '../hooks/useStats';
import { PARAM_INFO, STATUS_CONFIG, TIME_RANGES, SOURCE_COLORS } from '../constants';

import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorView } from '../components/common/ErrorView';
import { SectionHeader } from '../components/common/SectionHeader';
import { ParameterCard } from '../components/cards/ParameterCard';
import { LineChart } from '../components/charts/LineChart';

export default function StationDetailScreen() {
  const navigation = useNavigation();
  const route = useRoute();
  const { stationId } = route.params || {};
  const { theme } = useTheme();

  const [isFavorite, setIsFavorite] = useState(false);
  const [selectedParam, setSelectedParam] = useState(null);
  const [timeRange, setTimeRange] = useState('24H');
  const [refreshing, setRefreshing] = useState(false);

  const hours = useMemo(() => {
    const found = TIME_RANGES.find(t => t.label === timeRange);
    return found ? found.hours : 24;
  }, [timeRange]);

  const {
    data: stationData,
    loading: stationLoading,
    error: stationError,
    refetch: refetchStation,
  } = useStationData(stationId);

  const {
    data: historicalData,
    loading: histLoading,
    error: histError,
    refetch: refetchHistorical,
  } = useHistorical(stationId, hours);

  const {
    data: statsData,
    loading: statsLoading,
    error: statsError,
    refetch: refetchStats,
  } = useStats(stationId, stationData?.parameters || []);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await Promise.all([
      refetchStation(),
      refetchHistorical(),
      refetchStats(),
    ]);
    setRefreshing(false);
  }, [refetchStation, refetchHistorical, refetchStats]);

  // Default selected parameter to temp or first available
  const availableParams = useMemo(() => {
    if (!stationData?.parameters) return [];
    return stationData.parameters.filter(p => PARAM_INFO[p]);
  }, [stationData]);

  const currentParamKey = selectedParam || (availableParams.includes('temp') ? 'temp' : availableParams[0]);
  const currentParamInfo = PARAM_INFO[currentParamKey] || {};

  // Chart data for selected parameter
  const chartData = useMemo(() => {
    if (!historicalData || !historicalData[currentParamKey]) return [];
    return historicalData[currentParamKey];
  }, [historicalData, currentParamKey]);

  const toggleFavorite = () => {
    setIsFavorite(prev => !prev);
  };

  const getValueColor = (param, value) => {
    const info = PARAM_INFO[param];
    if (!info || !info.thresholds) return theme.colors.textSecondary;
    const v = parseFloat(value);
    if (isNaN(v)) return theme.colors.textSecondary;
    const { good, caution, concern } = info.thresholds;
    if (concern !== undefined && v >= concern) return theme.colors.danger;
    if (caution && v >= caution[0] && v <= caution[1]) return theme.colors.warning;
    if (good && v >= good[0] && v <= good[1]) return theme.colors.success;
    return theme.colors.textSecondary;
  };

  // Loading state
  if (stationLoading && !stationData) {
    return (
      <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
        <LoadingSpinner fullScreen message="Loading station data..." />
      </View>
    );
  }

  // Error state
  if (stationError && !stationData) {
    return (
      <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
        <View style={styles.headerSpacer} />
        <ErrorView message={stationError} onRetry={onRefresh} />
      </View>
    );
  }

  if (!stationData) {
    return (
      <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
        <ErrorView message="Station not found" onRetry={() => navigation.goBack()} />
      </View>
    );
  }

  const status = STATUS_CONFIG[stationData.status] || STATUS_CONFIG.offline;
  const sourceColor = SOURCE_COLORS[stationData.source] || theme.colors.primary;

  return (
    <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={theme.colors.primary}
            colors={[theme.colors.primary]}
          />
        }
      >
        {/* ===== HEADER CARD ===== */}
        <View style={[styles.headerCard, { backgroundColor: theme.colors.card }, theme.shadows.medium]}>
          {/* Top row: back + favorite */}
          <View style={styles.headerTopRow}>
            <TouchableOpacity
              style={[styles.iconButton, { backgroundColor: theme.colors.surfaceVariant }]}
              onPress={() => navigation.goBack()}
              activeOpacity={0.7}
            >
              <MaterialCommunityIcons name="arrow-left" size={22} color={theme.colors.textSecondary} />
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.iconButton, { backgroundColor: isFavorite ? theme.colors.warning + '20' : theme.colors.surfaceVariant }]}
              onPress={toggleFavorite}
              activeOpacity={0.7}
            >
              <MaterialCommunityIcons
                name={isFavorite ? 'star' : 'star-outline'}
                size={22}
                color={isFavorite ? theme.colors.warning : theme.colors.textSecondary}
              />
            </TouchableOpacity>
          </View>

          {/* Station name */}
          <Text style={[styles.stationName, { color: theme.colors.text }]}>
            {stationData.name}
          </Text>

          {/* Status + Source badges */}
          <View style={styles.badgeRow}>
            <View style={[styles.statusBadge, { backgroundColor: status.bgColor }]}>
              <View style={[styles.statusDot, { backgroundColor: status.color }]} />
              <Text style={[styles.statusText, { color: status.color }]}>
                {status.label}
              </Text>
            </View>
            <View style={[styles.sourceBadge, { backgroundColor: sourceColor + '20' }]}>
              <Text style={[styles.sourceText, { color: sourceColor }]}>
                {stationData.sourceLabel}
              </Text>
            </View>
          </View>

          {/* Location */}
          <View style={styles.locationRow}>
            <MaterialCommunityIcons name="map-marker" size={14} color={theme.colors.textTertiary} />
            <Text style={[styles.locationText, { color: theme.colors.textSecondary }]}>
              River Mile {stationData.mile} | Lat {stationData.lat}, Lon {stationData.lon}
            </Text>
          </View>

          {/* Description note */}
          {stationData.description && (
            <Text style={[styles.description, { color: theme.colors.textTertiary }]}>
              {stationData.description}
            </Text>
          )}
        </View>

        {/* ===== PARAMETER CARDS GRID ===== */}
        <SectionHeader title="Current Readings" icon="gauge" />
        <View style={styles.paramsGrid}>
          {availableParams.map((param, index) => {
            const reading = stationData.readings?.[param];
            const stat = statsData?.[param];
            return (
              <View key={param} style={styles.paramGridItem}>
                <ParameterCard
                  paramKey={param}
                  value={reading?.value}
                  unit={reading?.unit}
                  trend={reading?.trend}
                  min={stat?.min}
                  max={stat?.max}
                  onPress={() => setSelectedParam(param)}
                  isSelected={currentParamKey === param}
                />
              </View>
            );
          })}
        </View>

        {/* ===== HISTORICAL CHART CARD ===== */}
        <View style={[styles.chartCard, { backgroundColor: theme.colors.card }, theme.shadows.small]}>
          <SectionHeader
            title={`${currentParamInfo.label || currentParamKey} Trend`}
            icon="chart-line"
          />

          {/* Time range filter chips */}
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.timeRangeScroll}
          >
            {TIME_RANGES.map(range => (
              <TouchableOpacity
                key={range.label}
                style={[
                  styles.timeChip,
                  {
                    backgroundColor: timeRange === range.label
                      ? currentParamInfo.chartColor || theme.colors.primary
                      : theme.colors.surfaceVariant,
                  },
                ]}
                onPress={() => setTimeRange(range.label)}
                activeOpacity={0.8}
              >
                <Text
                  style={[
                    styles.timeChipText,
                    {
                      color: timeRange === range.label
                        ? theme.colors.textInverse
                        : theme.colors.textSecondary,
                    },
                  ]}
                >
                  {range.label}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>

          {/* Chart */}
          <View style={styles.chartContainer}>
            {(histLoading && !chartData.length) ? (
              <LoadingSpinner message="Loading chart..." />
            ) : histError ? (
              <ErrorView message="Failed to load chart data" onRetry={refetchHistorical} />
            ) : (
              <LineChart
                data={chartData}
                color={currentParamInfo.chartColor || theme.colors.primary}
                height={180}
              />
            )}
          </View>

          {/* Parameter selector for chart */}
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.paramSelectorScroll}
          >
            {availableParams.map(param => {
              const info = PARAM_INFO[param];
              const isSelected = currentParamKey === param;
              return (
                <TouchableOpacity
                  key={param}
                  style={[
                    styles.paramChip,
                    {
                      backgroundColor: isSelected
                        ? info.chartColor + '25'
                        : theme.colors.surfaceVariant,
                      borderColor: isSelected ? info.chartColor : theme.colors.border,
                    },
                  ]}
                  onPress={() => setSelectedParam(param)}
                  activeOpacity={0.8}
                >
                  <MaterialCommunityIcons
                    name={info.icon || 'circle'}
                    size={14}
                    color={isSelected ? info.chartColor : theme.colors.textTertiary}
                  />
                  <Text
                    style={[
                      styles.paramChipText,
                      {
                        color: isSelected
                          ? info.chartColor
                          : theme.colors.textSecondary,
                      },
                    ]}
                  >
                    {info.label}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </ScrollView>
        </View>

        {/* ===== STATISTICS CARD ===== */}
        <View style={[styles.statsCard, { backgroundColor: theme.colors.card }, theme.shadows.small]}>
          <SectionHeader title="Statistics (24h)" icon="calculator" />
          {statsLoading && !Object.keys(statsData).length ? (
            <LoadingSpinner message="Loading statistics..." />
          ) : (
            <View style={styles.statsGrid}>
              {availableParams.map(param => {
                const info = PARAM_INFO[param];
                const stat = statsData?.[param];
                return (
                  <View
                    key={param}
                    style={[styles.statRow, { borderBottomColor: theme.colors.divider }]}
                  >
                    <View style={styles.statLabelCol}>
                      <MaterialCommunityIcons name={info.icon || 'circle'} size={14} color={info.chartColor} />
                      <Text style={[styles.statLabel, { color: theme.colors.text }]}>
                        {info.label}
                      </Text>
                    </View>
                    <View style={styles.statValues}>
                      <View style={styles.statItem}>
                        <Text style={[styles.statItemLabel, { color: theme.colors.textTertiary }]}>Avg</Text>
                        <Text style={[styles.statItemValue, { color: theme.colors.textSecondary }]}>
                          {stat?.avg ?? '--'}
                        </Text>
                      </View>
                      <View style={styles.statItem}>
                        <Text style={[styles.statItemLabel, { color: theme.colors.textTertiary }]}>Min</Text>
                        <Text style={[styles.statItemValue, { color: theme.colors.primary }]}>
                          {stat?.min ?? '--'}
                        </Text>
                      </View>
                      <View style={styles.statItem}>
                        <Text style={[styles.statItemLabel, { color: theme.colors.textTertiary }]}>Max</Text>
                        <Text style={[styles.statItemValue, { color: theme.colors.danger }]}>
                          {stat?.max ?? '--'}
                        </Text>
                      </View>
                    </View>
                  </View>
                );
              })}
              {/* Readings count */}
              <View style={[styles.statRow, { borderBottomWidth: 0 }]}>
                <View style={styles.statLabelCol}>
                  <MaterialCommunityIcons name="database" size={14} color={theme.colors.textTertiary} />
                  <Text style={[styles.statLabel, { color: theme.colors.text }]}>
                    Readings Count
                  </Text>
                </View>
                <Text style={[styles.readingsCount, { color: theme.colors.textSecondary }]}>
                  {Object.values(statsData)[0]?.count || '--'} samples
                </Text>
              </View>
            </View>
          )}
        </View>

        {/* ===== INFO CARD ===== */}
        <View style={[styles.infoCard, { backgroundColor: theme.colors.card }, theme.shadows.small]}>
          <SectionHeader title="Station Information" icon="information-outline" />
          <View style={styles.infoGrid}>
            <InfoRow label="Station ID" value={stationData.id} theme={theme} />
            <InfoRow label="Data Source" value={stationData.sourceLabel} theme={theme} />
            <InfoRow
              label="Parameters"
              value={availableParams.map(p => PARAM_INFO[p]?.label || p).join(', ')}
              theme={theme}
            />
            <InfoRow
              label="Last Data"
              value={stationData.readings && Object.values(stationData.readings)[0]
                ? new Date(Object.values(stationData.readings)[0].timestamp).toLocaleString()
                : 'N/A'}
              theme={theme}
              isLast
            />
          </View>
        </View>

        {/* Footer spacing */}
        <View style={styles.footer} />
      </ScrollView>
    </View>
  );
}

function InfoRow({ label, value, theme, isLast = false }) {
  return (
    <View style={[styles.infoRow, { borderBottomColor: theme.colors.divider }, isLast && styles.lastRow]}>
      <Text style={[styles.infoLabel, { color: theme.colors.textTertiary }]}>{label}</Text>
      <Text style={[styles.infoValue, { color: theme.colors.textSecondary }]}>{value}</Text>
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
  headerSpacer: {
    height: 100,
  },
  headerCard: {
    marginHorizontal: 16,
    marginBottom: 12,
    borderRadius: 16,
    padding: 16,
  },
  headerTopRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  iconButton: {
    width: 40,
    height: 40,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stationName: {
    fontSize: 24,
    fontWeight: '800',
    letterSpacing: -0.5,
  },
  badgeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 10,
    flexWrap: 'wrap',
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 8,
    marginRight: 8,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 6,
  },
  statusText: {
    fontSize: 12,
    fontWeight: '700',
  },
  sourceBadge: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 8,
  },
  sourceText: {
    fontSize: 12,
    fontWeight: '700',
  },
  locationRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 10,
  },
  locationText: {
    fontSize: 12,
    marginLeft: 4,
  },
  description: {
    fontSize: 12,
    lineHeight: 18,
    marginTop: 8,
    fontStyle: 'italic',
  },
  paramsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: 12,
    marginBottom: 8,
  },
  paramGridItem: {
    width: '50%',
    padding: 4,
  },
  chartCard: {
    marginHorizontal: 16,
    marginBottom: 12,
    borderRadius: 14,
    paddingBottom: 12,
  },
  timeRangeScroll: {
    paddingHorizontal: 16,
    paddingVertical: 4,
  },
  timeChip: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 16,
    marginRight: 8,
  },
  timeChipText: {
    fontSize: 12,
    fontWeight: '700',
  },
  chartContainer: {
    paddingHorizontal: 16,
    marginTop: 8,
  },
  paramSelectorScroll: {
    paddingHorizontal: 16,
    paddingTop: 10,
  },
  paramChip: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 16,
    marginRight: 6,
    borderWidth: 1,
  },
  paramChipText: {
    fontSize: 11,
    fontWeight: '600',
    marginLeft: 4,
  },
  statsCard: {
    marginHorizontal: 16,
    marginBottom: 12,
    borderRadius: 14,
  },
  statsGrid: {
    paddingHorizontal: 16,
    paddingBottom: 12,
  },
  statRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 10,
    borderBottomWidth: 1,
  },
  statLabelCol: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 0.4,
  },
  statLabel: {
    fontSize: 13,
    fontWeight: '600',
    marginLeft: 6,
  },
  statValues: {
    flexDirection: 'row',
    flex: 0.6,
    justifyContent: 'flex-end',
  },
  statItem: {
    alignItems: 'center',
    marginLeft: 16,
  },
  statItemLabel: {
    fontSize: 10,
  },
  statItemValue: {
    fontSize: 13,
    fontWeight: '700',
    marginTop: 2,
  },
  readingsCount: {
    fontSize: 13,
    fontWeight: '600',
  },
  infoCard: {
    marginHorizontal: 16,
    marginBottom: 12,
    borderRadius: 14,
  },
  infoGrid: {
    paddingHorizontal: 16,
    paddingBottom: 12,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
  },
  lastRow: {
    borderBottomWidth: 0,
  },
  infoLabel: {
    fontSize: 13,
    fontWeight: '500',
  },
  infoValue: {
    fontSize: 12,
    flex: 1,
    textAlign: 'right',
    marginLeft: 16,
  },
  footer: {
    height: 30,
  },
});
