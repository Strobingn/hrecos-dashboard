import React, { useEffect } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Svg, { Circle, Path } from 'react-native-svg';
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
  const angleInRadians = ((angleInDegrees - 90) * Math.PI) / 180.0;
  return {
    x: cx + radius * Math.cos(angleInRadians),
    y: cy + radius * Math.sin(angleInRadians),
  };
}

function describeArc(cx, cy, radius, startAngle, endAngle) {
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

function getFishingColor(score, theme) {
  if (score <= 30) return theme.colors.danger;
  if (score <= 50) return theme.colors.warning;
  if (score <= 70) return '#9BBB2A';
  if (score <= 90) return theme.colors.success;
  return theme.colors.accent;
}

function getFishingLabel(score) {
  if (score <= 30) return 'Poor';
  if (score <= 50) return 'Fair';
  if (score <= 70) return 'Good';
  if (score <= 90) return 'Great';
  return 'Excellent';
}

export default function FishingScoreGauge({
  score = 0,
  size = 160,
}) {
  const theme = useTheme();

  const safeScore = Math.min(100, Math.max(0, score));
  const animatedValue = useSharedValue(0);

  useEffect(() => {
    animatedValue.value = withTiming(safeScore, {
      duration: 1500,
      easing: Easing.out(Easing.cubic),
    });
  }, [safeScore]);

  const strokeWidth = size * 0.09;
  const radius = (size - strokeWidth) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const maxAngle = 270;

  const animatedProps = useAnimatedProps(() => {
    const progress = animatedValue.value / 100;
    const endAngle = -135 + progress * maxAngle;
    return {
      d: describeArc(cx, cy, radius, -135, endAngle),
    };
  });

  const scoreColor = getFishingColor(safeScore, theme);
  const scoreLabel = getFishingLabel(safeScore);
  const trackPath = describeArc(cx, cy, radius, -135, 135);

  return (
    <View style={[styles.container, { width: size, height: size }]}>
      <Svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {/* Background track */}
        <Path
          d={trackPath}
          fill="none"
          stroke={theme.colors.divider}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        {/* Filled arc */}
        <AnimatedPath
          animatedProps={animatedProps}
          fill="none"
          stroke={scoreColor}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
      </Svg>

      {/* Center content */}
      <View style={styles.centerOverlay}>
        <MaterialCommunityIcons
          name="fish"
          size={size * 0.22}
          color={scoreColor}
          style={styles.fishIcon}
        />
        <Text
          style={[
            styles.score,
            { color: scoreColor, fontSize: size * 0.18 },
          ]}
        >
          {Math.round(safeScore)}
        </Text>
        <View style={styles.labelContainer}>
          <Text
            style={[
              styles.scoreLabel,
              { color: theme.colors.text, fontSize: size * 0.075 },
            ]}
          >
            {scoreLabel}
          </Text>
          <Text
            style={[
              styles.sublabel,
              { color: theme.colors.textSecondary, fontSize: size * 0.06 },
            ]}
          >
            Fishing Score
          </Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    justifyContent: 'center',
    alignItems: 'center',
    alignSelf: 'center',
  },
  centerOverlay: {
    position: 'absolute',
    justifyContent: 'center',
    alignItems: 'center',
  },
  fishIcon: {
    marginBottom: 2,
  },
  score: {
    fontWeight: '800',
    includeFontPadding: false,
    lineHeight: 28,
  },
  labelContainer: {
    alignItems: 'center',
    marginTop: 2,
  },
  scoreLabel: {
    fontWeight: '700',
  },
  sublabel: {
    fontWeight: '500',
    marginTop: 1,
  },
});
