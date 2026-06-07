import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useTheme } from '../../hooks/useTheme';

export default function MetricCard({
  title,
  value,
  unit,
  icon = 'gauge',
  color,
  trend,
  subtitle,
  onPress,
}) {
  const theme = useTheme();

  const iconColor = color || theme.colors.primary;
  const trendIcon =
    trend === 'up'
      ? 'trending-up'
      : trend === 'down'
        ? 'trending-down'
        : trend === 'stable'
          ? 'trending-neutral'
          : null;
  const trendColor =
    trend === 'up'
      ? theme.colors.success
      : trend === 'down'
        ? theme.colors.danger
        : theme.colors.textTertiary;

  const Wrapper = onPress ? TouchableOpacity : View;
  const wrapperProps = onPress
    ? { onPress, activeOpacity: 0.8 }
    : {};

  return (
    <Wrapper
      {...wrapperProps}
      style={[
        styles.container,
        {
          backgroundColor: theme.colors.card,
          borderColor: theme.colors.border,
          shadowColor: theme.isDark ? '#000' : '#64748B',
        },
      ]}
    >
      <View style={styles.iconRow}>
        <View
          style={[
            styles.iconContainer,
            { backgroundColor: iconColor + '18' },
          ]}
        >
          <MaterialCommunityIcons
            name={icon}
            size={20}
            color={iconColor}
          />
        </View>
        {trendIcon && (
          <View style={[styles.trendBadge, { backgroundColor: trendColor + '16' }]}>
            <MaterialCommunityIcons
              name={trendIcon}
              size={14}
              color={trendColor}
            />
          </View>
        )}
      </View>

      <Text style={[styles.title, { color: theme.colors.textSecondary }]}>
        {title || 'Metric'}
      </Text>

      <View style={styles.valueRow}>
        <Text style={[styles.value, { color: theme.colors.text }]}>
          {value != null ? value : '--'}
        </Text>
        {unit && (
          <Text style={[styles.unit, { color: theme.colors.textTertiary }]}>
            {' '}{unit}
          </Text>
        )}
      </View>

      {subtitle && (
        <Text
          style={[styles.subtitle, { color: theme.colors.textTertiary }]}
          numberOfLines={1}
        >
          {subtitle}
        </Text>
      )}
    </Wrapper>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    borderRadius: 14,
    borderWidth: 1,
    padding: 14,
    margin: 4,
    minHeight: 120,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 6,
    elevation: 2,
  },
  iconRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  iconContainer: {
    width: 36,
    height: 36,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  trendBadge: {
    width: 26,
    height: 26,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
  },
  title: {
    fontSize: 12,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.3,
    marginBottom: 6,
  },
  valueRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
  },
  value: {
    fontSize: 24,
    fontWeight: '800',
    includeFontPadding: false,
  },
  unit: {
    fontSize: 13,
    fontWeight: '600',
  },
  subtitle: {
    fontSize: 11,
    fontWeight: '400',
    marginTop: 6,
  },
});
