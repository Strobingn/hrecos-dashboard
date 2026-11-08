import React, { useMemo, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Svg, { Polyline, Line } from 'react-native-svg';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useTheme } from '../../hooks/useTheme';
import ErrorView from '../common/ErrorView';

function formatAxisTime(timeStr) {
  const date = new Date(timeStr);
  if (Number.isNaN(date.getTime())) return '';
  let hour = date.getHours();
  const suffix = hour >= 12 ? 'p' : 'a';
  hour = hour % 12 || 12;
  return `${hour}${suffix}`;
}

function formatClock(timeStr) {
  const date = new Date(timeStr);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

export default function TideChart({ predictions, title }) {
  const theme = useTheme();
  const [width, setWidth] = useState(0);

  const model = useMemo(() => {
    const rows = (predictions || [])
      .map((point) => ({
        time: point.time,
        t: new Date(point.time).getTime(),
        height: Number(point.height),
      }))
      .filter((point) => Number.isFinite(point.t) && Number.isFinite(point.height))
      .sort((a, b) => a.t - b.t);

    const highs = [];
    const lows = [];
    for (let i = 1; i < rows.length - 1; i += 1) {
      const prev = rows[i - 1].height;
      const curr = rows[i].height;
      const next = rows[i + 1].height;
      if (curr >= prev && curr >= next && curr > prev) highs.push(rows[i]);
      else if (curr <= prev && curr <= next && curr < prev) lows.push(rows[i]);
    }

    const labelCount = 5;
    const labels = [];
    if (rows.length) {
      for (let i = 0; i < labelCount; i += 1) {
        const index = Math.round((i * (rows.length - 1)) / (labelCount - 1));
        const row = rows[index];
        const text = formatAxisTime(row.time);
        if (!labels.some((label) => label.text === text)) {
          labels.push({ t: row.t, text });
        }
      }
    }

    return { rows, highs: highs.slice(0, 2), lows: lows.slice(0, 2), labels };
  }, [predictions]);

  if (!model.rows.length) {
    return (
      <View style={styles.container}>
        {title ? <Text style={[styles.title, { color: theme.colors.text }]}>{title}</Text> : null}
        <ErrorView message="No tide predictions available" icon="waves" />
      </View>
    );
  }

  const pad = { top: 16, right: 12, bottom: 8, left: 36 };
  const chartH = 180;
  const chartW = Math.max(0, width - pad.left - pad.right);
  const heights = model.rows.map((row) => row.height);
  const min = Math.min(...heights);
  const max = Math.max(...heights);
  const padY = Math.max(0.2, (max - min) * 0.12);
  const y0 = min - padY;
  const y1 = max + padY;
  const ySpan = y1 - y0 || 1;
  const t0 = model.rows[0].t;
  const t1 = model.rows[model.rows.length - 1].t;
  const tSpan = t1 - t0 || 1;

  const xOf = (t) => pad.left + ((t - t0) / tSpan) * chartW;
  const yOf = (h) => pad.top + (1 - (h - y0) / ySpan) * chartH;
  const points = model.rows.map((row) => `${xOf(row.t)},${yOf(row.height)}`).join(' ');
  const yTicks = [y1, (y0 + y1) / 2, y0];

  return (
    <View style={styles.container}>
      {title ? (
        <View style={styles.headerRow}>
          <MaterialCommunityIcons name="waves" size={20} color={theme.colors.secondary} style={styles.headerIcon} />
          <Text style={[styles.title, { color: theme.colors.text }]}>{title}</Text>
        </View>
      ) : null}

      <View onLayout={(event) => setWidth(event.nativeEvent.layout.width)}>
        {width > 0 && (
          <Svg width={width} height={chartH + pad.top + pad.bottom}>
            {yTicks.map((tick) => (
              <Line
                key={tick}
                x1={pad.left}
                x2={width - pad.right}
                y1={yOf(tick)}
                y2={yOf(tick)}
                stroke={theme.colors.chartGrid || theme.colors.divider}
                strokeWidth={1}
                strokeDasharray="4 4"
              />
            ))}
            <Polyline
              points={points}
              fill="none"
              stroke={theme.colors.secondary}
              strokeWidth={2.5}
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          </Svg>
        )}
        {width > 0 && (
          <View style={[styles.yLabels, { height: chartH + pad.top + pad.bottom }]} pointerEvents="none">
            {yTicks.map((tick) => (
              <Text
                key={tick}
                style={[styles.yText, { color: theme.colors.textSecondary, top: yOf(tick) - 7 }]}
              >
                {tick.toFixed(1)}
              </Text>
            ))}
          </View>
        )}
        <View style={styles.xLabels}>
          {model.labels.map((label) => (
            <Text
              key={`${label.t}-${label.text}`}
              style={[
                styles.xText,
                {
                  color: theme.colors.textSecondary,
                  left: width ? xOf(label.t) - 16 : 0,
                },
              ]}
            >
              {label.text}
            </Text>
          ))}
        </View>
      </View>

      <View style={styles.markersRow}>
        {model.highs.map((row) => (
          <View key={`high-${row.t}`} style={styles.markerItem}>
            <MaterialCommunityIcons name="triangle" size={12} color={theme.colors.success} />
            <Text style={[styles.markerLabel, { color: theme.colors.textSecondary }]}>
              High <Text style={{ color: theme.colors.success, fontWeight: '700' }}>{row.height.toFixed(1)} ft</Text> {formatClock(row.time)}
            </Text>
          </View>
        ))}
        {model.lows.map((row) => (
          <View key={`low-${row.t}`} style={styles.markerItem}>
            <MaterialCommunityIcons name="triangle-down" size={12} color={theme.colors.warning} />
            <Text style={[styles.markerLabel, { color: theme.colors.textSecondary }]}>
              Low <Text style={{ color: theme.colors.warning, fontWeight: '700' }}>{row.height.toFixed(1)} ft</Text> {formatClock(row.time)}
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
  yLabels: {
    position: 'absolute',
    left: 0,
    top: 0,
    width: 34,
  },
  yText: {
    position: 'absolute',
    left: 0,
    width: 32,
    fontSize: 10,
    textAlign: 'right',
  },
  xLabels: {
    height: 18,
    position: 'relative',
  },
  xText: {
    position: 'absolute',
    width: 32,
    fontSize: 11,
    fontWeight: '600',
    textAlign: 'center',
  },
  markersRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-around',
    marginTop: 8,
  },
  markerItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: 6,
    marginVertical: 2,
    gap: 4,
  },
  markerLabel: {
    fontSize: 12,
    fontWeight: '500',
  },
});
