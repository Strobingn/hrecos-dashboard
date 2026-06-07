import React from 'react';
import { View, StyleSheet } from 'react-native';
import { useTheme } from '../../hooks/useTheme';

export const LineChart = ({ data, color, height = 160, lineWidth = 2, showDots = false }) => {
  const { theme } = useTheme();

  if (!data || data.length === 0) {
    return (
      <View style={[styles.emptyContainer, { height, backgroundColor: theme.colors.surfaceVariant }]}>
        <View style={styles.emptyLine} />
      </View>
    );
  }

  const values = data.map(d => d.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const padding = { top: 10, bottom: 10, left: 0, right: 0 };
  const chartW = 100; // percentage-based width
  const chartH = height - padding.top - padding.bottom;

  // Build SVG polyline points
  const points = data.map((d, i) => {
    const x = (i / (data.length - 1)) * chartW;
    const y = padding.top + (1 - (d.value - min) / range) * chartH;
    return `${x},${y}`;
  }).join(' ');

  // Build area path
  const areaPath = data.map((d, i) => {
    const x = (i / (data.length - 1)) * chartW;
    const y = padding.top + (1 - (d.value - min) / range) * chartH;
    return `${x},${y}`;
  }).join(' ');

  const svgColor = color || theme.colors.primary;
  const svgHeight = height;

  return (
    <View style={[styles.container, { height: svgHeight }]}>
      {/* Use a View-based approach for simplicity */}
      <View style={styles.svgWrapper}>
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((frac, i) => (
          <View
            key={`grid-${i}`}
            style={[
              styles.gridLine,
              {
                top: `${frac * 100}%`,
                backgroundColor: theme.colors.divider,
              },
            ]}
          />
        ))}

        {/* Area fill */}
        <View style={[styles.areaFill, { backgroundColor: svgColor + '12' }]} />

        {/* Line using a series of small line segments */}
        <View style={StyleSheet.absoluteFill}>
          {data.map((d, i) => {
            if (i === 0) return null;
            const x1 = ((i - 1) / (data.length - 1)) * 100;
            const x2 = (i / (data.length - 1)) * 100;
            const y1 = padding.top + (1 - (data[i - 1].value - min) / range) * chartH;
            const y2 = padding.top + (1 - (d.value - min) / range) * chartH;
            const dx = x2 - x1;
            const dy = ((y2 - y1) / svgHeight) * 100;
            const dist = Math.sqrt(dx * dx + dy * dy);
            const angle = Math.atan2(dy, dx) * (180 / Math.PI);
            return (
              <View
                key={`line-${i}`}
                style={{
                  position: 'absolute',
                  left: `${x1}%`,
                  top: `${(y1 / svgHeight) * 100}%`,
                  width: `${dist}%`,
                  height: lineWidth,
                  backgroundColor: svgColor,
                  transform: [{ rotate: `${angle}deg` }],
                  transformOrigin: 'left center',
                  borderRadius: lineWidth / 2,
                }}
              />
            );
          })}
        </View>

        {/* Dots */}
        {showDots && data.map((d, i) => {
          if (i % Math.ceil(data.length / 12) !== 0) return null;
          const x = (i / (data.length - 1)) * 100;
          const y = padding.top + (1 - (d.value - min) / range) * chartH;
          return (
            <View
              key={`dot-${i}`}
              style={{
                position: 'absolute',
                left: `${x}%`,
                top: `${(y / svgHeight) * 100}%`,
                width: 6,
                height: 6,
                borderRadius: 3,
                backgroundColor: theme.colors.card,
                borderWidth: 2,
                borderColor: svgColor,
                marginLeft: -3,
                marginTop: -3,
              }}
            />
          );
        })}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: '100%',
  },
  svgWrapper: {
    flex: 1,
    position: 'relative',
    overflow: 'hidden',
  },
  emptyContainer: {
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emptyLine: {
    width: '60%',
    height: 1,
    backgroundColor: '#ccc',
  },
  gridLine: {
    position: 'absolute',
    left: 0,
    right: 0,
    height: 1,
  },
  areaFill: {
    ...StyleSheet.absoluteFillObject,
    opacity: 0.3,
  },
});
