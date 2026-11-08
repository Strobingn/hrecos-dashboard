import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Svg, { Path } from 'react-native-svg';
import { useTheme } from '../../hooks/useTheme';
import { getWQILevel } from '../../constants';

function arcPoint(cx, cy, radius, t) {
  const angle = Math.PI * (1 - t);
  return {
    x: cx + radius * Math.cos(angle),
    y: cy - radius * Math.sin(angle),
  };
}

function arcPath(cx, cy, radius, from, to) {
  const start = arcPoint(cx, cy, radius, from);
  const end = arcPoint(cx, cy, radius, Math.max(from + 0.001, to));
  const large = to - from > 0.5 ? 1 : 0;
  return `M ${start.x} ${start.y} A ${radius} ${radius} 0 ${large} 1 ${end.x} ${end.y}`;
}

export const WaterQualityGauge = ({ wqi, size = 148 }) => {
  const { theme } = useTheme();
  const level = getWQILevel(wqi);
  const progress = Math.min(100, Math.max(0, Number(wqi) || 0));
  const stroke = 12;
  const width = size;
  const radius = (width - stroke) / 2 - 2;
  const cx = width / 2;
  const cy = radius + stroke / 2 + 2;
  const svgHeight = cy + 18;

  return (
    <View style={[styles.container, { width, height: svgHeight + 4 }]}>
      <Svg width={width} height={svgHeight}>
        <Path
          d={arcPath(cx, cy, radius, 0, 1)}
          stroke={theme.colors.border || theme.colors.divider}
          strokeWidth={stroke}
          fill="none"
          strokeLinecap="round"
        />
        {progress > 0 && (
          <Path
            d={arcPath(cx, cy, radius, 0, progress / 100)}
            stroke={level.color}
            strokeWidth={stroke}
            fill="none"
            strokeLinecap="round"
          />
        )}
      </Svg>
      <View style={[styles.center, { top: cy - radius * 0.78 }]}>
        <Text style={[styles.value, { color: level.color }]}>{Math.round(progress)}</Text>
        <Text style={[styles.level, { color: level.color }]}>{level.label}</Text>
      </View>
      <View style={[styles.scale, { top: cy + 2, width }]}>
        <Text style={[styles.scaleText, { color: theme.colors.textTertiary }]}>0</Text>
        <Text style={[styles.scaleText, { color: theme.colors.textTertiary }]}>50</Text>
        <Text style={[styles.scaleText, { color: theme.colors.textTertiary }]}>100</Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    overflow: 'hidden',
  },
  center: {
    position: 'absolute',
    left: 0,
    right: 0,
    alignItems: 'center',
  },
  value: {
    fontSize: 28,
    fontWeight: '800',
    lineHeight: 32,
  },
  level: {
    fontSize: 12,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.4,
  },
  scale: {
    position: 'absolute',
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 2,
  },
  scaleText: {
    fontSize: 10,
    fontWeight: '600',
  },
});
