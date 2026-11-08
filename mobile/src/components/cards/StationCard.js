import React, { useEffect, useRef } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Animated as RNAnimated,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useTheme } from '../../hooks/useTheme';
import { PARAM_INFO } from '../../constants';

function LivePulse({ color }) {
  const pulseAnim = useRef(new RNAnimated.Value(0)).current;

  useEffect(() => {
    const pulse = RNAnimated.loop(
      RNAnimated.sequence([
        RNAnimated.timing(pulseAnim, {
          toValue: 1,
          duration: 1200,
          useNativeDriver: true,
        }),
        RNAnimated.timing(pulseAnim, {
          toValue: 0,
          duration: 1200,
          useNativeDriver: true,
        }),
      ])
    );
    pulse.start();
    return () => pulse.stop();
  }, []);

  const opacity = pulseAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [0.3, 0.9],
  });

  const scale = pulseAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [0.8, 1.6],
  });

  return (
    <View style={styles.pulseContainer}>
      <RNAnimated.View
        style={[
          styles.pulseRing,
          {
            backgroundColor: color,
            opacity,
            transform: [{ scale }],
          },
        ]}
      />
      <View style={[styles.pulseDot, { backgroundColor: color }]} />
    </View>
  );
}

export default function StationCard({
  station,
  onPress,
  isFavorite = false,
  onToggleFavorite,
}) {
  const theme = useTheme();

  if (!station) return null;

  const isLive = station.status === 'live';
  const statusColor = isLive ? theme.colors.success : theme.colors.disabled;
  const readings = station.readings || {};
  const paramKeys = station.parameters || station.params || [];

  const keyParams = [];
  const pushReading = (key, fallback) => {
    const reading = readings[key];
    const info = PARAM_INFO[key] || {};
    const rawValue = reading && typeof reading === 'object' ? reading.value : (reading ?? fallback);
    if (rawValue == null || rawValue === '') return;
    const numeric = Number(rawValue);
    keyParams.push({
      label: (reading && reading.label) || info.label || key,
      value: Number.isFinite(numeric) ? numeric.toFixed(numeric >= 100 ? 0 : 1) : String(rawValue),
      unit: (reading && reading.unit) || info.unit || '',
      icon: info.icon || 'gauge',
    });
  };

  const preferred = ['temp', 'do', 'do_sat', 'turbidity', 'salinity', 'ph', 'conductivity'];
  preferred.forEach((key) => {
    if (keyParams.length >= 3) return;
    if (paramKeys.length && !paramKeys.includes(key) && readings[key] == null) return;
    pushReading(key);
  });
  if (keyParams.length === 0) {
    pushReading('temp', readings.temperature);
    pushReading('turbidity');
    pushReading('do', readings.dissolvedOxygen);
  }

  return (
    <TouchableOpacity
      onPress={onPress}
      activeOpacity={0.8}
      style={[
        styles.container,
        {
          backgroundColor: theme.colors.card,
          borderColor: theme.colors.border,
          shadowColor: theme.isDark ? '#000' : '#64748B',
        },
      ]}
    >
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          {isLive ? (
            <LivePulse color={statusColor} />
          ) : (
            <View
              style={[
                styles.offlineDot,
                { backgroundColor: statusColor },
              ]}
            />
          )}
          <View style={styles.titleContainer}>
            <Text
              style={[styles.stationName, { color: theme.colors.text }]}>
              {station.name || 'Unknown Station'}
            </Text>
            <Text
              style={[
                styles.locationText,
                { color: theme.colors.textSecondary },
              ]}>
              {station.location || 'Hudson River'}
            </Text>
          </View>
        </View>

        <View style={styles.headerRight}>
          {onToggleFavorite && (
            <TouchableOpacity
              onPress={(e) => {
                e.stopPropagation();
                onToggleFavorite();
              }}
              hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
              style={styles.favoriteButton}
            >
              <MaterialCommunityIcons
                name={isFavorite ? 'star' : 'star-outline'}
                size={22}
                color={
                  isFavorite
                    ? theme.colors.warning
                    : theme.colors.textTertiary
                }
              />
            </TouchableOpacity>
          )}
          <MaterialCommunityIcons
            name="chevron-right"
            size={22}
            color={theme.colors.textTertiary}
          />
        </View>
      </View>

      {keyParams.length === 0 && (
        <Text style={[styles.emptyReading, { color: theme.colors.textSecondary }]}>
          {station.kind === 'prediction' ? 'Tide predictions only' : 'No sensor reading'}
        </Text>
      )}

      {/* Parameter Grid */}
      {keyParams.length > 0 && (
        <View style={styles.paramsGrid}>
          {keyParams.map((param, index) => (
            <View
              key={index}
              style={[
                styles.paramItem,
                index < keyParams.length - 1 && {
                  borderRightWidth: 1,
                  borderRightColor: theme.colors.divider,
                },
              ]}
            >
              <MaterialCommunityIcons
                name={param.icon || 'gauge'}
                size={16}
                color={theme.colors.primary}
                style={styles.paramIcon}
              />
              <Text
                style={[
                  styles.paramLabel,
                  { color: theme.colors.textSecondary },
                ]}>
                {param.label}
              </Text>
              <Text style={[styles.paramValue, { color: theme.colors.text }]}>
                {param.value != null ? param.value : '--'}
                <Text
                  style={[
                    styles.paramUnit,
                    { color: theme.colors.textTertiary },
                  ]}>
                  {' '}
                  {param.unit}
                </Text>
              </Text>
            </View>
          ))}
        </View>
      )}

      {/* Status badge */}
      <View style={styles.footer}>
        <View
          style={[
            styles.statusBadge,
            {
              backgroundColor: isLive
                ? theme.colors.successLight
                : theme.colors.disabled + '22',
            },
          ]}
        >
          <Text
            style={[
              styles.statusText,
              {
                color: isLive
                  ? theme.colors.success
                  : theme.colors.textTertiary,
              },
            ]}
          >
            {isLive ? 'LIVE' : 'OFFLINE'}
          </Text>
        </View>
        {station.lastUpdated && (
          <Text
            style={[
              styles.lastUpdated,
              { color: theme.colors.textTertiary },
            ]}
          >
            {station.lastUpdated}
          </Text>
        )}
      </View>
    </TouchableOpacity>
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
    justifyContent: 'space-between',
  },
  emptyReading: {
    marginTop: 10,
    fontSize: 13,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  headerRight: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  titleContainer: {
    marginLeft: 10,
    flex: 1,
  },
  stationName: {
    fontSize: 15,
    fontWeight: '700',
  },
  locationText: {
    fontSize: 12,
    marginTop: 1,
  },
  favoriteButton: {
    padding: 4,
    marginRight: 2,
  },
  pulseContainer: {
    width: 14,
    height: 14,
    justifyContent: 'center',
    alignItems: 'center',
  },
  pulseRing: {
    position: 'absolute',
    width: 14,
    height: 14,
    borderRadius: 7,
  },
  pulseDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  offlineDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginHorizontal: 2,
  },
  paramsGrid: {
    flexDirection: 'row',
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: 'transparent',
  },
  paramItem: {
    flex: 1,
    alignItems: 'center',
    paddingHorizontal: 6,
  },
  paramIcon: {
    marginBottom: 3,
  },
  paramLabel: {
    fontSize: 11,
    fontWeight: '500',
    marginBottom: 2,
  },
  paramValue: {
    fontSize: 15,
    fontWeight: '700',
  },
  paramUnit: {
    fontSize: 11,
    fontWeight: '500',
  },
  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 10,
    paddingTop: 8,
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 8,
  },
  statusText: {
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  lastUpdated: {
    fontSize: 11,
    fontWeight: '400',
  },
});
