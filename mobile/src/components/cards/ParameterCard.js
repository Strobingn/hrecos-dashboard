import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useTheme } from '../../hooks/useTheme';
import { PARAM_INFO } from '../../constants';

export const ParameterCard = ({
  paramKey,
  value,
  unit,
  trend,
  min,
  max,
  onPress,
  isSelected,
}) => {
  const { theme } = useTheme();
  const info = PARAM_INFO[paramKey] || { label: paramKey, icon: 'circle', chartColor: theme.colors.primary };

  const getValueColor = () => {
    const v = parseFloat(value);
    if (isNaN(v)) return theme.colors.textSecondary;
    const { thresholds } = info;
    if (!thresholds) return theme.colors.textSecondary;
    const { concern, caution, good } = thresholds;
    if (concern !== undefined && v >= concern) return theme.colors.danger;
    if (caution && v >= caution[0] && v <= caution[1]) return theme.colors.warning;
    if (good && v >= good[0] && v <= good[1]) return theme.colors.success;
    return theme.colors.textSecondary;
  };

  const getTrendIcon = () => {
    if (trend === 'up') return 'arrow-up-bold';
    if (trend === 'down') return 'arrow-down-bold';
    return 'minus';
  };

  const getTrendColor = () => {
    if (trend === 'up') return theme.colors.danger;
    if (trend === 'down') return theme.colors.primary;
    return theme.colors.textTertiary;
  };

  return (
    <View
      style={[
        styles.card,
        {
          backgroundColor: isSelected ? info.chartColor + '18' : theme.colors.card,
          borderColor: isSelected ? info.chartColor : theme.colors.border,
        },
        theme.shadows.small,
      ]}
    >
      <View style={styles.header}>
        <View style={[styles.iconContainer, { backgroundColor: info.chartColor + '20' }]}>
          <MaterialCommunityIcons name={info.icon} size={18} color={info.chartColor} />
        </View>
        <Text style={[styles.label, { color: theme.colors.textSecondary }]} numberOfLines={1}>
          {info.label}
        </Text>
      </View>

      <View style={styles.valueRow}>
        <Text style={[styles.value, { color: theme.colors.text }]}>
          {value !== undefined && value !== null ? value : 'N/A'}
        </Text>
        {value !== undefined && value !== null && (
          <>
            <Text style={[styles.unit, { color: theme.colors.textTertiary }]}>
              {unit || info.unit}
            </Text>
            {trend && (
              <MaterialCommunityIcons
                name={getTrendIcon()}
                size={14}
                color={getTrendColor()}
                style={styles.trendIcon}
              />
            )}
          </>
        )}
      </View>

      {(min !== undefined || max !== undefined) && (
        <View style={styles.rangeRow}>
          <Text style={[styles.rangeText, { color: theme.colors.textTertiary }]}>
            Min: {min !== undefined ? min : '--'}
          </Text>
          <Text style={[styles.rangeText, { color: theme.colors.textTertiary }]}>
            Max: {max !== undefined ? max : '--'}
          </Text>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    flex: 1,
    borderRadius: 12,
    padding: 12,
    borderWidth: 1.5,
    minWidth: 0,
    margin: 4,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  iconContainer: {
    width: 30,
    height: 30,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 6,
  },
  label: {
    fontSize: 11,
    fontWeight: '600',
    flex: 1,
  },
  valueRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    marginBottom: 4,
  },
  value: {
    fontSize: 20,
    fontWeight: '700',
  },
  unit: {
    fontSize: 12,
    marginLeft: 3,
  },
  trendIcon: {
    marginLeft: 4,
  },
  rangeRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  rangeText: {
    fontSize: 10,
  },
});
