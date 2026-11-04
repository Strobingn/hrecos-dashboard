import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, Linking, ActivityIndicator } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useTheme } from '../../hooks/useTheme';
import { usePreferences } from '../../context/PreferencesContext';
import { useWeather } from '../../hooks/useWeather';
import { formatMeasurement } from '../../utils/measurements';
import { weatherAlerts, weatherDescription } from '../../utils/weather';

export default function WeatherPanel({ onConfigure, details = false }) {
  const { colors } = useTheme();
  const { units, weatherSettings } = usePreferences();
  const { data, isPending, isFetching, error, refetch } = useWeather();
  const now = Date.now();
  const stale = !data || now - data.updatedAt > 30 * 60000;
  const alerts = stale ? [] : weatherAlerts(data, weatherSettings, now);
  const forecast = (data?.hours || []).filter((h) => h.time > now && h.time <= now + weatherSettings.hours * 3600000);
  const incomplete = forecast.length < weatherSettings.hours || forecast.some((h) => h.wind == null || h.gust == null || h.rain == null);
  const rain = forecast.length && forecast.every((h) => h.rain != null) ? forecast.reduce((sum, h) => sum + h.rain, 0) : null;
  const measure = (value, type, digits = 1) => formatMeasurement(value, type, units, digits);
  const time = (ms) => new Date(ms).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  const alertValue = (a, value) => a.type === 'rain'
    ? `${measure(value == null ? null : value / 25.4, 'rain', units === 'imperial' ? 2 : 1)}/h`
    : measure(value, 'wind_speed', 0);

  return (
    <View style={[styles.card, { backgroundColor: colors.card, borderColor: colors.border }]}>
      <View style={styles.row}>
        <View style={styles.grow}>
          <Text style={[styles.eyebrow, { color: colors.textSecondary }]}>WEATHER · WEST POINT</Text>
          <Text style={[styles.title, { color: colors.text }]}>Before you head out</Text>
        </View>
        <TouchableOpacity onPress={() => refetch()} accessibilityRole="button" accessibilityLabel="Refresh weather" style={styles.action}>
          {isFetching ? <ActivityIndicator color={colors.primary} /> : <MaterialCommunityIcons name="refresh" size={22} color={colors.primary} />}
        </TouchableOpacity>
      </View>
      {isPending ? <Text style={[styles.note, { color: colors.textSecondary }]}>Getting the local forecast…</Text> : !data ? (
        <Text accessibilityRole="alert" style={[styles.note, { color: colors.textSecondary }]}>Weather unavailable. Tap refresh to try again.</Text>
      ) : (
        <>
          <View style={[styles.row, { marginVertical: 16 }]}>
            <MaterialCommunityIcons name={data.current.code >= 51 ? 'weather-rainy' : 'weather-partly-cloudy'} size={40} color={colors.primary} />
            <Text style={[styles.temperature, { color: colors.text }]}>{measure(data.current.temperature, 'air_temp', 0)}</Text>
            <View style={styles.grow}>
              <Text style={[styles.condition, { color: colors.text }]}>{weatherDescription(data.current.code)}</Text>
              <Text style={[styles.note, { color: colors.textSecondary }]}>Updated {time(data.updatedAt)}</Text>
            </View>
          </View>
          <View style={[styles.metrics, { backgroundColor: colors.surfaceVariant }]}>
            {[['Wind', measure(data.current.wind, 'wind_speed', 0)], ['Gusts', measure(data.current.gust, 'wind_gusts', 0)], [`Rain · ${weatherSettings.hours}h`, measure(rain == null ? null : rain / 25.4, 'rain', units === 'imperial' ? 2 : 1)]].map(([label, value]) => (
              <View key={label} style={styles.metric}>
                <Text style={[styles.note, { color: colors.textSecondary }]}>{label}</Text>
                <Text style={[styles.metricValue, { color: colors.text }]}>{value}</Text>
              </View>
            ))}
          </View>
          {error || stale ? (
            <Text accessibilityRole="alert" style={[styles.notice, { color: colors.text }]}>Forecast could not refresh{stale ? '; data is out of date and alerts are paused.' : '. Showing the last update.'}</Text>
          ) : alerts.length ? alerts.map((alert) => (
            <View key={alert.id} accessibilityRole="alert" style={[styles.warning, { backgroundColor: colors.warningLight }]}>
              <MaterialCommunityIcons name={alert.type === 'rain' ? 'weather-pouring' : 'weather-windy'} size={21} color={colors.warning} />
              <View style={styles.grow}>
                <Text style={[styles.condition, { color: colors.text }]}>{alert.title} · {alertValue(alert, alert.peak)}</Text>
                <Text style={[styles.note, { color: colors.textSecondary }]}>From {time(alert.time)} · your limit {alertValue(alert, alert.threshold)}</Text>
              </View>
            </View>
          )) : (
            <Text style={[styles.notice, { color: colors.textSecondary }]}>{!weatherSettings.enabled ? 'Your weather alerts are turned off.' : incomplete ? 'Some forecast measurements are unavailable. Weather alerts may be incomplete.' : `No weather thresholds exceeded in the next ${weatherSettings.hours} hours.`}</Text>
          )}
          {details && (
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.forecast}>
              {forecast.map((hour) => (
                <View key={hour.time} style={[styles.hour, { borderColor: colors.border }]}>
                  <Text style={[styles.note, { color: colors.textSecondary }]}>{time(hour.time)}</Text>
                  <Text style={[styles.condition, { color: colors.text }]}>{measure(hour.temperature, 'air_temp', 0)}</Text>
                  <Text style={[styles.note, { color: colors.textSecondary }]}>{measure(hour.wind, 'wind_speed', 0)}</Text>
                  <Text style={[styles.note, { color: colors.primary }]}>{hour.probability == null ? '—' : `${hour.probability}% rain`}</Text>
                </View>
              ))}
            </ScrollView>
          )}
        </>
      )}
      <View style={[styles.row, styles.footer, { borderTopColor: colors.divider }]}>
        <TouchableOpacity onPress={onConfigure} accessibilityRole="button" style={styles.footerButton}>
          <MaterialCommunityIcons name="tune-variant" size={17} color={colors.primary} />
          <Text style={[styles.link, { color: colors.primary }]}>Adjust weather alerts</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={() => Linking.openURL('https://open-meteo.com/')} accessibilityRole="link" accessibilityLabel="Weather data by Open-Meteo" style={styles.footerButton}>
          <Text style={[styles.note, { color: colors.textSecondary }]}>Open-Meteo ↗</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { marginHorizontal: 20, marginVertical: 12, padding: 20, borderRadius: 24, borderWidth: 1 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  grow: { flex: 1 },
  eyebrow: { fontSize: 10, fontWeight: '700', letterSpacing: 1.4, marginBottom: 5 },
  title: { fontSize: 20, fontWeight: '700', letterSpacing: -0.5 },
  action: { padding: 10, minWidth: 44, minHeight: 44, alignItems: 'center', justifyContent: 'center' },
  temperature: { fontSize: 34, fontWeight: '600', letterSpacing: -1.5 },
  condition: { fontSize: 13, fontWeight: '600' },
  note: { fontSize: 11, lineHeight: 17 },
  metrics: { flexDirection: 'row', borderRadius: 16, paddingVertical: 14 },
  metric: { flex: 1, alignItems: 'center', gap: 5 },
  metricValue: { fontSize: 15, fontWeight: '600' },
  notice: { fontSize: 12, lineHeight: 19, marginTop: 14 },
  warning: { flexDirection: 'row', alignItems: 'center', gap: 10, padding: 12, borderRadius: 12, marginTop: 12 },
  footer: { flexWrap: 'wrap', justifyContent: 'space-between', borderTopWidth: 1, marginTop: 16, paddingTop: 6 },
  footerButton: { flexDirection: 'row', alignItems: 'center', gap: 5, minHeight: 44 },
  link: { fontSize: 12, fontWeight: '600' },
  forecast: { gap: 8, paddingTop: 18 },
  hour: { padding: 12, borderWidth: 1, borderRadius: 12, gap: 6, minWidth: 92 },
});
