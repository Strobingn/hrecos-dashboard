import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '../../hooks/useTheme';
import { getWQILevel } from '../../constants';

export const WaterQualityGauge = ({ wqi, size = 160 }) => {
  const { theme } = useTheme();
  const level = getWQILevel(wqi);

  // SVG gauge calculations
  const strokeWidth = 14;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const halfCircumference = circumference / 2;
  const progress = Math.min(Math.max(wqi, 0), 100);
  const dashOffset = halfCircumference - (progress / 100) * halfCircumference;

  const center = size / 2;

  return (
    <View style={[styles.container, { width: size, height: size * 0.7 }]}>
      <View style={{ position: 'relative' }}>
        {/* Background arc */}
        <View style={{ width: size, height: size }}>
          <Text> </Text>
        </View>

        {/* We use a simpler approach with styled View arcs */}
        <View style={[styles.gaugeContainer, { width: size, height: size * 0.65 }]}>
          {/* Background track */}
          <View style={[
            styles.track,
            {
              width: size,
              height: size,
              borderWidth: strokeWidth,
              borderColor: theme.colors.border,
            },
          ]} />
          {/* Colored progress - using a clip approach */}
          <View style={[
            styles.progressOverlay,
            {
              width: size,
              height: size,
              borderWidth: strokeWidth,
              borderColor: level.color,
            },
          ]} />

          {/* Center content */}
          <View style={[styles.center, { width: size - strokeWidth * 4, height: (size - strokeWidth * 4) * 0.7 }]}>
            <Text style={[styles.wqiValue, { color: level.color, fontSize: size * 0.2 }]}>
              {wqi}
            </Text>
            <Text style={[styles.wqiLabel, { color: theme.colors.textSecondary, fontSize: size * 0.075 }]}>
              WQI
            </Text>
            <View style={[styles.levelBadge, { backgroundColor: level.color + '25' }]}>
              <Text style={[styles.levelText, { color: level.color, fontSize: size * 0.065 }]}>
                {level.label}
              </Text>
            </View>
          </View>
        </View>
      </View>

      {/* Scale labels */}
      <View style={[styles.scaleLabels, { width: size }]}>
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
    justifyContent: 'center',
  },
  gaugeContainer: {
    position: 'relative',
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
  track: {
    position: 'absolute',
    borderRadius: 999,
    borderBottomColor: 'transparent',
    borderLeftColor: 'transparent',
    transform: [{ rotate: '-90deg' }],
  },
  progressOverlay: {
    position: 'absolute',
    borderRadius: 999,
    borderBottomColor: 'transparent',
    borderLeftColor: 'transparent',
    transform: [{ rotate: '-90deg' }],
  },
  center: {
    position: 'absolute',
    bottom: 0,
    alignItems: 'center',
    justifyContent: 'center',
  },
  wqiValue: {
    fontWeight: '800',
    lineHeight: undefined,
  },
  wqiLabel: {
    fontWeight: '500',
    marginTop: 2,
  },
  levelBadge: {
    marginTop: 4,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
  },
  levelText: {
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  scaleLabels: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 8,
    marginTop: 4,
  },
  scaleText: {
    fontSize: 10,
  },
});
