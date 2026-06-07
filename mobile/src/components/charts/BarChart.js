import React from 'react';
import { View, Text, Dimensions, StyleSheet } from 'react-native';
import { BarChart as RNBarChart } from 'react-native-chart-kit';
import { useTheme } from '../../hooks/useTheme';
import ErrorView from '../common/ErrorView';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const CHART_WIDTH = SCREEN_WIDTH - 64;
const DEFAULT_HEIGHT = 220;

export default function BarChart({
  data,
  title,
  color,
  height = DEFAULT_HEIGHT,
  yAxisSuffix = '',
}) {
  const theme = useTheme();

  const barColor = color || theme.colors.primary;

  if (!data || data.length === 0) {
    return (
      <View style={styles.container}>
        {title && (
          <Text style={[styles.title, { color: theme.colors.text }]}>
            {title}
          </Text>
        )}
        <ErrorView message="No chart data available" icon="chart-bar" />
      </View>
    );
  }

  const labels = data.map((d) => d.label || '');
  const values = data.map((d) => d.value ?? d);

  const chartData = {
    labels,
    datasets: [
      {
        data: values,
      },
    ],
  };

  const chartConfig = {
    backgroundColor: theme.colors.transparent,
    backgroundGradientFrom: theme.colors.transparent,
    backgroundGradientTo: theme.colors.transparent,
    decimalPlaces: 1,
    color: () => barColor,
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
      fontSize: 11,
      fontWeight: '500',
    },
    barPercentage: 0.6,
    barRadius: 6,
    fillShadowGradient: barColor,
    fillShadowGradientOpacity: 0.85,
    useShadowColorFromDataset: false,
    yAxisSuffix,
  };

  return (
    <View style={styles.container}>
      {title && (
        <Text style={[styles.title, { color: theme.colors.text }]}>
          {title}
        </Text>
      )}
      <RNBarChart
        data={chartData}
        width={CHART_WIDTH}
        height={height}
        chartConfig={chartConfig}
        withInnerLines
        withOuterLines
        withVerticalLabels
        withHorizontalLabels
        showBarTops={false}
        fromZero
        segments={5}
        style={styles.chart}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginVertical: 4,
  },
  title: {
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 8,
    paddingHorizontal: 4,
  },
  chart: {
    borderRadius: 14,
    marginLeft: -8,
  },
});
