import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useTheme } from '../../hooks/useTheme';

export default function TideCard({
  currentTide,
  nextTide,
  tidePhase,
}) {
  const theme = useTheme();

  const isRising = tidePhase === 'rising';
  const arrowRotation = isRising ? '0deg' : '180deg';
  const phaseColor = isRising ? theme.colors.success : theme.colors.warning;
  const phaseIcon = isRising ? 'arrow-up' : 'arrow-down';
  const phaseLabel = isRising ? 'Rising' : 'Falling';

  const safeCurrent = currentTide || {};
  const safeNext = nextTide || {};

  return (
    <View
      style={[
        styles.container,
        {
          backgroundColor: theme.colors.card,
          borderColor: theme.colors.border,
          shadowColor: theme.isDark ? '#000' : '#64748B',
        },
      ]}
    >
      {/* Header with wave icon */}
      <View style={styles.header}>
        <View
          style={[
            styles.waveIconContainer,
            { backgroundColor: theme.colors.secondary + '18' },
          ]}
        >
          <MaterialCommunityIcons
            name="waves"
            size={22}
            color={theme.colors.secondary}
          />
        </View>
        <View style={styles.headerText}>
          <Text style={[styles.headerTitle, { color: theme.colors.text }]}>
            Tide
          </Text>
          <Text
            style={[
              styles.headerSubtitle,
              { color: theme.colors.textSecondary },
            ]}
          >
            Hudson River
          </Text>
        </View>
      </View>

      {/* Current Tide */}
      <View style={styles.currentSection}>
        <Text
          style={[
            styles.currentLabel,
            { color: theme.colors.textSecondary },
          ]}
        >
          Current Height
        </Text>
        <View style={styles.currentValueRow}>
          <Text style={[styles.currentValue, { color: theme.colors.text }]}>
            {safeCurrent.height != null ? safeCurrent.height.toFixed(1) : '--'}
          </Text>
          <Text
            style={[styles.currentUnit, { color: theme.colors.textTertiary }]}
          >
            ft
          </Text>
          {/* Direction arrow */}
          <View
            style={[
              styles.directionBadge,
              { backgroundColor: phaseColor + '18' },
            ]}
          >
            <MaterialCommunityIcons
              name={phaseIcon}
              size={16}
              color={phaseColor}
            />
            <Text
              style={[
                styles.directionText,
                { color: phaseColor },
              ]}
            >
              {phaseLabel}
            </Text>
          </View>
        </View>
      </View>

      {/* Next Tide */}
      {safeNext.time && (
        <View
          style={[
            styles.nextSection,
            { borderTopColor: theme.colors.divider },
          ]}
        >
          <MaterialCommunityIcons
            name={safeNext.type === 'high' ? 'triangle' : 'triangle-down'}
            size={14}
            color={
              safeNext.type === 'high'
                ? theme.colors.success
                : theme.colors.warning
            }
            style={styles.nextTideIcon}
          />
          <View style={styles.nextInfo}>
            <Text
              style={[styles.nextLabel, { color: theme.colors.textSecondary }]}
            >
              Next{' '}
              <Text style={{ color: theme.colors.text, fontWeight: '700' }}>
                {safeNext.type === 'high' ? 'High' : 'Low'}
              </Text>{' '}
              Tide
            </Text>
            <Text style={[styles.nextTime, { color: theme.colors.text }]}>
              {safeNext.time}
              {safeNext.height != null && (
                <Text
                  style={[
                    styles.nextHeight,
                    { color: theme.colors.textSecondary },
                  ]}
                >
                  {' '}
                  ({safeNext.height.toFixed(1)} ft)
                </Text>
              )}
            </Text>
          </View>
          <View style={styles.timeRemainingBadge}>
            <MaterialCommunityIcons
              name="clock-outline"
              size={12}
              color={theme.colors.primary}
              style={styles.clockIcon}
            />
            <Text
              style={[
                styles.timeRemaining,
                { color: theme.colors.primary },
              ]}
            >
              {safeNext.timeRemaining || 'Soon'}
            </Text>
          </View>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginHorizontal: 16,
    marginVertical: 6,
    borderRadius: 14,
    borderWidth: 1,
    padding: 14,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 6,
    elevation: 2,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  waveIconContainer: {
    width: 38,
    height: 38,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerText: {
    marginLeft: 10,
  },
  headerTitle: {
    fontSize: 15,
    fontWeight: '700',
  },
  headerSubtitle: {
    fontSize: 12,
    marginTop: 1,
  },
  currentSection: {
    marginBottom: 10,
  },
  currentLabel: {
    fontSize: 12,
    fontWeight: '500',
    marginBottom: 4,
  },
  currentValueRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
  },
  currentValue: {
    fontSize: 32,
    fontWeight: '800',
    includeFontPadding: false,
  },
  currentUnit: {
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 2,
    marginRight: 12,
  },
  directionBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 8,
  },
  directionText: {
    fontSize: 12,
    fontWeight: '700',
    marginLeft: 4,
  },
  nextSection: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingTop: 10,
    borderTopWidth: 1,
  },
  nextTideIcon: {
    marginRight: 8,
  },
  nextInfo: {
    flex: 1,
  },
  nextLabel: {
    fontSize: 12,
    fontWeight: '500',
  },
  nextTime: {
    fontSize: 14,
    fontWeight: '700',
    marginTop: 2,
  },
  nextHeight: {
    fontSize: 12,
    fontWeight: '500',
  },
  timeRemainingBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 8,
  },
  clockIcon: {
    marginRight: 4,
  },
  timeRemaining: {
    fontSize: 12,
    fontWeight: '700',
  },
});
