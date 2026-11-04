import React, { useCallback, useState } from 'react';
import { View, Text, ScrollView, RefreshControl, StyleSheet, TouchableOpacity, Alert } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import { useTheme } from '../hooks/useTheme';
import { usePreferences } from '../context/PreferencesContext';
import { useDashboard } from '../hooks/useDashboard';
import { useStations } from '../hooks/useStations';
import { useTides } from '../hooks/useTides';
import { useWeather } from '../hooks/useWeather';
import { formatMeasurement } from '../utils/measurements';
import StationCard from '../components/cards/StationCard';
import WeatherPanel from '../components/cards/WeatherPanel';

export default function DashboardScreen() {
  const navigation = useNavigation();
  const { colors } = useTheme();
  const { units, setUnits } = usePreferences();
  const dashboard = useDashboard();
  const stations = useStations();
  const tides = useTides();
  const weather = useWeather();
  const [refreshing, setRefreshing] = useState(false);
  const measure = (value, param) => formatMeasurement(value, param, units);
  const reporting = stations.stations.filter((s) => s.readings && Object.keys(s.readings).length);
  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    try { await Promise.all([dashboard.refetch(), stations.refetch(), tides.refetch(), weather.refetch()]); }
    finally { setRefreshing(false); }
  }, [dashboard.refetch, stations.refetch, tides.refetch, weather.refetch]);
  const changeUnits = async (value) => {
    try { await setUnits(value); }
    catch { Alert.alert('Could not save units', 'Please try again.'); }
  };
  return (
    <ScrollView style={{ backgroundColor: colors.background }} contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} colors={[colors.primary]} />}>
      <View style={styles.header}>
        <View style={styles.grow}>
          <Text style={[styles.eyebrow, { color: colors.primary }]}>HUDSON RIVER</Text>
          <Text style={[styles.heading, { color: colors.text }]}>Your river, at a glance.</Text>
          <Text style={[styles.subtitle, { color: colors.textSecondary }]}>West Point · Cornwall · Newburgh</Text>
        </View>
        <TouchableOpacity style={[styles.settings, { backgroundColor: colors.card, borderColor: colors.border }]} onPress={() => navigation.navigate('Settings')} accessibilityLabel="Open settings" accessibilityRole="button">
          <MaterialCommunityIcons name="tune-variant" size={22} color={colors.text} />
        </TouchableOpacity>
      </View>
      <View style={styles.hero}>
        <View style={styles.heroTop}>
          <Text style={styles.heroLabel}>AVERAGE WATER TEMPERATURE</Text>
          <View style={styles.unitToggle}>
            {['imperial', 'metric'].map((option) => <TouchableOpacity key={option} onPress={() => changeUnits(option)} accessibilityRole="button" accessibilityLabel={option === 'imperial' ? 'Use Fahrenheit and imperial units' : 'Use Celsius and metric units'} accessibilityState={{ selected: units === option }} style={[styles.unitButton, units === option && styles.unitSelected]}>
              <Text style={[styles.unitText, { color: units === option ? '#123D3B' : '#C4DEDA' }]}>{option === 'imperial' ? '°F' : '°C'}</Text>
            </TouchableOpacity>)}
          </View>
        </View>
        <Text style={styles.heroValue}>{measure(dashboard.data?.avgWaterTemp, 'temp')}</Text>
        <Text style={styles.heroNote}>{dashboard.error ? 'River readings unavailable · pull to retry' : dashboard.loading && !dashboard.data ? 'Getting river readings…' : 'From available HRECOS stations'}</Text>
        <View style={styles.heroBottom}>
          <View style={styles.grow}>
            <Text style={styles.heroLabel}>CURRENT TIDE</Text>
            <Text style={styles.heroMetric}>{measure(tides.data?.current?.height, 'tide')}</Text>
            <Text style={styles.heroNote}>{tides.data?.source === 'simulated' ? 'Simulated · NOAA unavailable' : 'NOAA · Newburgh'}</Text>
          </View>
          <View style={styles.heroDivider} />
          <View style={styles.grow}>
            <Text style={styles.heroLabel}>RIVER STATIONS</Text>
            <Text style={styles.heroMetric}>{reporting.length} reporting</Text>
            <Text style={styles.heroNote}>{dashboard.data?.lastUpdated ? `Updated ${new Date(dashboard.data.lastUpdated).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}` : 'Waiting for observations'}</Text>
          </View>
        </View>
      </View>
      <WeatherPanel onConfigure={() => navigation.navigate('Settings')} />
      <View style={styles.sectionHead}>
        <View style={styles.grow}>
          <Text style={[styles.sectionTitle, { color: colors.text }]}>Along the river</Text>
          <Text style={[styles.subtitle, { color: colors.textSecondary }]}>Your nearest monitoring stations</Text>
        </View>
        <TouchableOpacity style={styles.linkButton} accessibilityRole="button" onPress={() => navigation.navigate('Stations')}>
          <Text style={{ color: colors.primary, fontWeight: '600' }}>View all ↗</Text>
        </TouchableOpacity>
      </View>
      <View style={styles.stationList}>
        {reporting.slice(0, 3).map((station) => <StationCard key={station.id} station={station} onPress={() => navigation.navigate('StationDetail', { stationId: station.id, stationName: station.name })} />)}
        {!reporting.length && <Text style={[styles.emptyText, { color: colors.textSecondary }]}>{stations.loading ? 'Getting station readings…' : 'No current station readings. Pull to refresh.'}</Text>}
      </View>
      <TouchableOpacity style={[styles.alertLink, { backgroundColor: colors.card, borderColor: colors.border }]} onPress={() => navigation.navigate('Alerts')} accessibilityRole="button">
        <MaterialCommunityIcons name="bell-outline" size={22} color={colors.primary} />
        <View style={styles.grow}>
          <Text style={[styles.sectionTitle, { color: colors.text }]}>Conditions & alerts</Text>
          <Text style={[styles.subtitle, { color: colors.textSecondary }]}>Weather warnings and river anomalies</Text>
        </View>
        <MaterialCommunityIcons name="chevron-right" size={22} color={colors.textSecondary} />
      </TouchableOpacity>
      <Text style={[styles.footer, { color: colors.textSecondary }]}>HRECOS RIVERWATCH · TAPPAN ZEE TO POUGHKEEPSIE</Text>
    </ScrollView>
  );
}
const styles = StyleSheet.create({
  content: { paddingTop: 16, paddingBottom: 32 },
  header: { paddingHorizontal: 20, paddingBottom: 24, flexDirection: 'row', alignItems: 'center', gap: 8 },
  eyebrow: { fontSize: 10, fontWeight: '700', letterSpacing: 2, marginBottom: 8 },
  heading: { fontSize: 25, fontWeight: '700', letterSpacing: -1 },
  subtitle: { fontSize: 12, lineHeight: 18, marginTop: 4 },
  settings: { borderRadius: 14, borderWidth: 1, padding: 12 },
  hero: { marginHorizontal: 20, padding: 22, borderRadius: 24, backgroundColor: '#153E3C' },
  heroTop: { gap: 14, flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center' },
  heroLabel: { color: '#B2CFCA', fontSize: 9, fontWeight: '600', letterSpacing: 1 },
  heroValue: { fontSize: 57, letterSpacing: -2.5, fontWeight: '500', color: '#FAFCF7', marginTop: 16 },
  heroNote: { color: '#B2CFCA', fontSize: 11, lineHeight: 17, marginTop: 4 },
  heroBottom: { flexDirection: 'row', marginTop: 25, paddingTop: 20, borderTopWidth: 1, borderTopColor: '#365A56', gap: 16 },
  heroMetric: { fontSize: 19, fontWeight: '600', color: '#FAFCF7', marginTop: 8 },
  heroDivider: { width: 1, backgroundColor: '#365A56' },
  grow: { flex: 1 },
  unitToggle: { flexDirection: 'row', backgroundColor: '#2F5350', padding: 3, borderRadius: 12 },
  unitButton: { minWidth: 44, minHeight: 44, alignItems: 'center', justifyContent: 'center', borderRadius: 9 },
  unitSelected: { backgroundColor: '#E9F3E8' },
  unitText: { fontSize: 13, fontWeight: '700' },
  sectionHead: { marginHorizontal: 20, marginTop: 16, marginBottom: 14, flexDirection: 'row', alignItems: 'center', gap: 8 },
  sectionTitle: { fontSize: 18, fontWeight: '700', letterSpacing: -0.4 },
  linkButton: { minHeight: 44, justifyContent: 'center' },
  stationList: { marginHorizontal: 20 },
  emptyText: { fontSize: 13, lineHeight: 20, textAlign: 'center', padding: 24 },
  alertLink: { marginHorizontal: 20, marginTop: 18, padding: 18, borderRadius: 20, borderWidth: 1, flexDirection: 'row', alignItems: 'center', gap: 12 },
  footer: { fontSize: 8, letterSpacing: 1.3, textAlign: 'center', paddingHorizontal: 20, marginTop: 30 },
});
