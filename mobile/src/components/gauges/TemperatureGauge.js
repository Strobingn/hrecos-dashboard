import React, { useEffect } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Svg, { Path, Defs, LinearGradient, Stop } from 'react-native-svg';
import Animated, {
  useSharedValue,
  useAnimatedProps,
  withTiming,
  Easing,
} from 'react-native-reanimated';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useTheme } from '../../hooks/useTheme';

const AnimatedPath = Animated.createAnimatedComponent(Path);

function polarToCartesian(cx, cy, radius, angleInDegrees) {
  const angleInRadians = ((angleInDegrees - 180) * Math.PI) / 180.0;
  return {
    x: cx + radius * Math.cos(angleInRadians),
    y: cy + radius * Math.sin(angleInRadians),
  };
}

function describeSemiArc(cx, cy, radius, startAngle, endAngle) {
  const start = polarToCartesian(cx, cy, radius, endAngle);
  const end = polarToCartesian(cx, cy, radius, startAngle);
  const largeArcFlag = endAngle - startAngle <= 180 ? '0' : '1';

  return [
    'M',
    start.x,
    start.y,
    'A',
    radius,
    radius,
    0,
    largeArcFlag,
    0,
    end.x,
    end.y,
  ].join(' ');
}

function getTempColor(temp, theme) {
  if (temp <= 32) return '#2196F3';
  if (temp <= 50) return '#03A9F4';
  if (temp <= 68) return '#4CAF50';
  if (temp <= 80) return '#8BC34A';
  if (temp <= 90) return '#FF9800';
  return theme.colors.danger;
}

function getTempIcon(temp) {
  if (temp <= 32) return 'snowflake';
  if (temp <= 50) return 'thermometer-low';
  if (temp <= 68) return 'thermometer';
  if (temp <= 80) return 'thermometer-high';
  return 'fire';
}

export default function TemperatureGauge({
  temp,
  size = 120,
  min = -20,
  max = 120,
}) {
  const theme = useTheme();

  const safeTemp = temp != null ? temp : (min + max) / 2;
  const clampedTemp = Math.min(max, Math.max(min, safeTemp));
  const tempPercent = (clampedTemp - min) / (max - min);

  const animatedValue = useSharedValue(0);

  useEffect(() => {
    animatedValue.value = withTiming(tempPercent, {
      duration: 1200,
      easing: Easing.out(Easing.cubic),
    });
  }, [tempPercent]);

  const strokeWidth = size * 0.12;
  const radius = (size - strokeWidth) / 2;
  const cx = size / 2;
  const cy = size * 0.82;
  const maxAngle = 180;

  const animatedProps = useAnimatedProps(() => {
    const progress = animatedValue.value;
    const endAngle = progress * maxAngle;
    return {
      d: describeSemiArc(cx, cy, radius, 0, endAngle),
    };
  });

  const trackPath = describeSemiArc(cx, cy, radius, 0, 180);
  const tempColor = getTempColor(safeTemp, theme);
  const tempIcon = getTempIcon(safeTemp);

  return (
    <View style={styles.wrapper}>
      <View style={[styles.container, { width: size, height: size * 0.92 }]}>
        <Svg
          width={size}
          height={size * 0.92}
          viewBox={`0 0 ${size} ${size * 0.92}`}
        >
          <Defs>
            <LinearGradient id="tempGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <Stop offset="0%" stopColor="#2196F3" />
              <Stop offset="25%" stopColor="#03A9F4" />
              <Stop offset="50%" stopColor="#4CAF50" />
              <Stop offset="75%" stopColor="#FF9800" />
              <Stop offset="100%" stopColor={theme.colors.danger} />
            </LinearGradient>
          </Defs>

          {/* Background track */}
          <Path
            d={trackPath}
            fill="none"
            stroke={theme.colors.divider}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />
          {/* Filled arc with gradient */}
          <AnimatedPath
            animatedProps={animatedProps}
            fill="none"
            stroke="url(#tempGradient)"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />
        </Svg>

        {/* Center content */}
        <View style={[styles.centerOverlay, { bottom: size * 0.1 }]}>
          <MaterialCommunityIcons
            name={tempIcon}
            size={size * 0.18}
            color={tempColor}
          />
          <Text
            style={[
              styles.tempValue,
              { color: theme.colors.text, fontSize: size * 0.22 },
            ]}
          >
            {safeTemp != null ? `${Math.round(safeTemp)}°` : '--'}
          </Text>
          <Text
            style={[
              styles.unitLabel,
              { color: theme.colors.textSecondary, fontSize: size * 0.08 },
            ]}
          >
            Fahrenheit
          </Text>
        </View>
      </View>

      {/* Min/Max labels */}
      <View style={[styles.labelsRow, { width: size }]}>
        <Text style={[styles.rangeLabel, { color: theme.colors.textTertiary }]}>
          {min}°
        </Text>
        <Text style={[styles.rangeLabel, { color: theme.colors.textTertiary }]}>
          {max}°
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    alignItems: 'center',
    alignSelf: 'center',
  },
  container: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  centerOverlay: {
    position: 'absolute',
    justifyContent: 'center',
    alignItems: 'center',
  },
  tempValue: {
    fontWeight: '800',
    includeFontPadding: false,
  },
  unitLabel: {
    fontWeight: '500',
    marginTop: 2,
  },
  labelsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 4,
    paddingHorizontal: 4,
  },
  rangeLabel: {
    fontSize: 11,
    fontWeight: '600',
  },
});
