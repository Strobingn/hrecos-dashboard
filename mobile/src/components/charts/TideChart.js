import React, { useMemo } from 'react';
import { View, Text, Dimensions, StyleSheet } from 'react-native';
import { LineChart as RNLineChart } from 'react-native-chart-kit';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useTheme } from '../../hooks/useTheme';
import ErrorView from '../common/ErrorView';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const CHART_WIDTH = SCREEN_WIDTH - 48;
const CHART_HEIGHT = 240;

export default function TideChart({ predictions, title }) {
  const theme = useTheme();

  const {
    chartData,
    chartLabels,
    highTideIndices,
    lowTideIndices,
    currentTimeIndex,
    minHeight,
    maxHeight,
  } = useMemo(() => {
    if (!predictions || predictions.length === 0) {
      return {
        chartData: [],
        chartLabels: [],
        highTideIndices: [],
        lowTideIndices: [],
        currentTimeIndex: -1,
        minHeight: 0,
        maxHeight: 10,
      };
    }

    const heights = predictions.map((p) => p.height);
    const min = Math.min(...heights);
    const max = Math.max(...heights);
    const padding = (max - min) * 0.15;

    const labels = predictions.map((p, i) => {
      const date = new Date(p.time);
      const hour = date.getHours();
      if (i === 0 || hour % 6 === 0) {
        return `${hour.toString().padStart(2, '0')}:00`;
      }
      return '';
    });

    const highIndices = [];
    const lowIndices = [];

    for (let i = 1; i < predictions.length - 1; i++) {
      const prev = predictions[i - 1].height;
      const curr = predictions[i].height;
      const next = predictions[i + 1].height;

      if (curr > prev && curr > next) {
        highIndices.push(i);
      } else if (curr < prev && curr < next) {
        lowIndices.push(i);
      }
    }

    const now = new Date();
    let closestIdx = 0;
    let closestDiff = Infinity;
    predictions.forEach((p, i) => {
      const diff = Math.abs(new Date(p.time).getTime() - now.getTime());
      if (diff < closestDiff) {
        closestDiff = diff;
        closestIdx = i;
      }
    });

    return {
      chartData: predictions.map((p) => p.height),
      chartLabels: labels,
      highTideIndices: highIndices,
      lowTideIndices: lowIndices,
      currentTimeIndex: closestIdx,
      minHeight: Math.max(0, min - padding),
      maxHeight: max + padding,
    };
  }, [predictions]);

  if (!predictions || predictions.length === 0) {
    return (
      <View style={styles.container}>
        {title && (
          <Text style={[styles.title, { color: theme.colors.text }]}>
            {title}
          </Text>
        )}
        <ErrorView message="No tide predictions available" icon="waves" />
      </View>
    );
  }

  const data = {
    labels: chartLabels,
    datasets: [
      {
        data: chartData,
        color: () => theme.colors.secondary,
        strokeWidth: 2.5,
      },
    ],
  };

  const chartConfig = {
    backgroundColor: theme.colors.transparent,
    backgroundGradientFrom: theme.colors.transparent,
    backgroundGradientTo: theme.colors.transparent,
    decimalPlaces: 1,
    color: () => theme.colors.textSecondary,
    labelColor: () => theme.colors.textSecondary,
    style: {
      borderRadius: 14,
    },
    propsForBackgroundLines: {
      stroke: theme.colors.chartGrid,
      strokeWidth: 1,
      strokeDasharray: '4, 4',
    },
    propsForLabels: {
      fontSize: 10,
      fontWeight: '500',
    },
    propsForDots: {
      r: '0',
      strokeWidth: '0',
    },
    fillShadowGradient: theme.colors.secondary,
    fillShadowGradientOpacity: 0.2,
    useShadowColorFromDataset: false,
  };

  const formatTime = (timeStr) => {
    const date = new Date(timeStr);
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  };

  return (
    <View style={styles.container}>
      {title && (
        <View style={styles.headerRow}>
          <MaterialCommunityIcons
            name="waves"
            size={20}
            color={theme.colors.secondary}
            style={styles.headerIcon}
          />
          <Text style={[styles.title, { color: theme.colors.text }]}>
            {title}
          </Text>
        </View>
      )}

      <RNLineChart
        data={data}
        width={CHART_WIDTH}
        height={CHART_HEIGHT}
        chartConfig={chartConfig}
        bezier
        withDots={false}
        withShadow
        withInnerLines
        withOuterLines
        withVerticalLines={false}
        withHorizontalLines
        withHorizontalLabels
        withVerticalLabels
        fromZero={false}
        segments={5}
        style={styles.chart}
      />

      {/* High/Low tide markers overlay */}
      <View style={styles.markersRow}>
        {highTideIndices.slice(0, 2).map((idx) => (
          <View key={`high-${idx}`} style={styles.markerItem}>
            <MaterialCommunityIcons
              name="triangle"
              size={12}
              color={theme.colors.success}
              style={styles.highTideIcon}
            />
            <Text
              style={[styles.markerLabel, { color: theme.colors.textSecondary }]}
            >
              High{' '}
              <Text style={[styles.markerValue, { color: theme.colors.success }]}>
                {chartData[idx]?.toFixed(1)} ft
              </Text>{' '}
              {formatTime(predictions[idx]?.time)}
            </Text>
          </View>
        ))}
        {lowTideIndices.slice(0, 2).map((idx) => (
          <View key={`low-${idx}`} style={styles.markerItem}>
            <MaterialCommunityIcons
              name="triangle-down"
              size={12}
              color={theme.colors.warning}
              style={styles.lowTideIcon}
            />
            <Text
              style={[styles.markerLabel, { color: theme.colors.textSecondary }]}
            >
              Low{' '}
              <Text style={[styles.markerValue, { color: theme.colors.warning }]}>
                {chartData[idx]?.toFixed(1)} ft
              </Text>{' '}
              {formatTime(predictions[idx]?.time)}
            </Text>
          </View>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginVertical: 4,
    paddingHorizontal: 8,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
    paddingHorizontal: 4,
  },
  headerIcon: {
    marginRight: 8,
  },
  title: {
    fontSize: 16,
    fontWeight: '700',
  },
  chart: {
    borderRadius: 14,
  },
  markersRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-around',
    marginTop: 10,
    paddingHorizontal: 4,
  },
  markerItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: 6,
    marginVertical: 2,
  },
  highTideIcon: {
    marginRight: 4,
  },
  lowTideIcon: {
    marginRight: 4,
  },
  markerLabel: {
    fontSize: 12,
    fontWeight: '500',
  },
  markerValue: {
    fontWeight: '700',
  },
});
