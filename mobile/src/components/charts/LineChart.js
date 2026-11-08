import React, { useMemo, useState } from 'react';
import { View, StyleSheet } from 'react-native';
import Svg, { Polyline, Line } from 'react-native-svg';
import { useTheme } from '../../hooks/useTheme';

const GAP_FLOOR_MS = 3 * 60 * 60 * 1000;

function seriesFrom(data) {
  return (data || [])
    .map((point) => ({
      t: new Date(point.timestamp).getTime(),
      value: Number(point.value),
    }))
    .filter((point) => Number.isFinite(point.t) && Number.isFinite(point.value))
    .sort((a, b) => a.t - b.t);
}

function splitOnGaps(points) {
  if (points.length < 2) return points.length ? [points] : [];
  const gaps = [];
  for (let i = 1; i < points.length; i += 1) {
    gaps.push(points[i].t - points[i - 1].t);
  }
  const sorted = [...gaps].sort((a, b) => a - b);
  const median = sorted[Math.floor(sorted.length / 2)] || 0;
  const breakAt = Math.max(median * 3, GAP_FLOOR_MS);
  const segments = [[points[0]]];
  for (let i = 1; i < points.length; i += 1) {
    if (points[i].t - points[i - 1].t > breakAt) {
      segments.push([points[i]]);
    } else {
      segments[segments.length - 1].push(points[i]);
    }
  }
  return segments;
}

export const LineChart = ({ data, color, height = 180, lineWidth = 2.5 }) => {
  const { theme } = useTheme();
  const [width, setWidth] = useState(0);
  const stroke = color || theme.colors.primary;
  const points = useMemo(() => seriesFrom(data), [data]);
  const segments = useMemo(() => splitOnGaps(points), [points]);

  if (!points.length) {
    return <View style={[styles.empty, { height, backgroundColor: theme.colors.surfaceVariant }]} />;
  }

  const pad = { top: 12, bottom: 12, left: 8, right: 8 };
  const min = Math.min(...points.map((point) => point.value));
  const max = Math.max(...points.map((point) => point.value));
  const range = max - min || 1;
  const t0 = points[0].t;
  const t1 = points[points.length - 1].t;
  const span = t1 - t0 || 1;
  const chartW = Math.max(0, width - pad.left - pad.right);
  const chartH = height - pad.top - pad.bottom;

  const xy = (point) => {
    const x = pad.left + ((point.t - t0) / span) * chartW;
    const y = pad.top + (1 - (point.value - min) / range) * chartH;
    return `${x},${y}`;
  };

  return (
    <View style={{ height, width: '100%' }} onLayout={(event) => setWidth(event.nativeEvent.layout.width)}>
      {width > 0 && (
        <Svg width={width} height={height}>
          {[0.25, 0.5, 0.75].map((frac) => (
            <Line
              key={frac}
              x1={pad.left}
              x2={width - pad.right}
              y1={pad.top + frac * chartH}
              y2={pad.top + frac * chartH}
              stroke={theme.colors.divider}
              strokeWidth={1}
            />
          ))}
          {segments.map((segment, index) => (
            segment.length > 1 ? (
              <Polyline
                key={index}
                points={segment.map(xy).join(' ')}
                fill="none"
                stroke={stroke}
                strokeWidth={lineWidth}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
            ) : null
          ))}
        </Svg>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  empty: {
    borderRadius: 8,
    width: '100%',
  },
});

export default LineChart;
