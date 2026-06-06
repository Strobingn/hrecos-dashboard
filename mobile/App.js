import React, { useState, useEffect } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet,
  SafeAreaView, StatusBar, Dimensions, Switch
} from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import Svg, { Circle, Path, G, Text as SvgText } from 'react-native-svg';

// ===== DATA =====
const STATIONS = [
  { id: 'turkey', name: 'Turkey Point', loc: 'Catskill, NY', rm: 84, src: 'NOAA', params: ['temp', 'conductance'], live: true, readings: { temp: 68.4, conductance: 285 } },
  { id: 'norrie', name: 'Norrie Point', loc: 'Staatsburg, NY', rm: 88, src: 'NDBC', params: ['air_temp', 'wind_speed', 'pressure', 'dewpoint'], live: true, readings: { air_temp: 72.1, wind_speed: 8.5, pressure: 30.12, dewpoint: 62.3 } },
  { id: 'schodack', name: 'Schodack Landing', loc: 'Schodack, NY', rm: 120, src: 'USGS', params: ['temp', 'conductance', 'dissolved_oxygen', 'turbidity'], live: true, readings: { temp: 66.2, conductance: 310, dissolved_oxygen: 8.4, turbidity: 12.5 } },
  { id: 'albany', name: 'Albany', loc: 'Albany, NY', rm: 143, src: 'USGS', params: ['temp'], live: true, readings: { temp: 65.1 } },
];

const PARAMS = {
  temp: { label: 'Water Temp', unit: '\u00B0F' },
  conductance: { label: 'Conductance', unit: '\u03BCS/cm' },
  dissolved_oxygen: { label: 'Dissolved O\u2082', unit: 'mg/L' },
  turbidity: { label: 'Turbidity', unit: 'NTU' },
  air_temp: { label: 'Air Temp', unit: '\u00B0F' },
  wind_speed: { label: 'Wind', unit: 'mph' },
  pressure: { label: 'Pressure', unit: 'inHg' },
  dewpoint: { label: 'Dew Point', unit: '\u00B0F' },
};

// ===== COLORS =====
const COLORS = {
  primary: '#0A7EA4', primaryDark: '#065F7A', primaryLight: '#4DB8D4',
  accent: '#FF8F00', success: '#43A047', warning: '#FFB300', danger: '#E53935',
  bg: '#F0F4F8', surface: '#FFFFFF', text: '#1A2B3C', textSec: '#5A6B7C',
  border: '#D0DAE4',
};

// ===== CALCULATIONS =====
function calcWQI(r) {
  const turbidityScore = r.turbidity ? Math.max(0, 100 - r.turbidity * 2) : 75;
  const doScore = r.dissolved_oxygen ? Math.min(100, r.dissolved_oxygen * 12) : 80;
  const tempScore = r.temp ? (r.temp >= 50 && r.temp <= 80 ? 100 : r.temp >= 40 && r.temp <= 90 ? 70 : 40) : 70;
  return Math.round(turbidityScore * 0.3 + doScore * 0.3 + tempScore * 0.2 + 75 * 0.2);
}
function wqiLabel(s) { return s >= 80 ? 'Good' : s >= 60 ? 'Fair' : s >= 40 ? 'Poor' : 'Bad'; }
function swimLabel(s) { return s >= 80 ? { l: 'Safe', c: '#43A047' } : s >= 60 ? { l: 'Caution', c: '#FFB300' } : { l: 'Unsafe', c: '#E53935' }; }
function clarityLabel(t) { return t < 5 ? 'Crystal Clear' : t < 15 ? 'Clean' : t < 35 ? 'Slightly Murky' : t < 75 ? 'Murky' : 'Very Dirty'; }
function fishScore(r, hr) {
  const ts = r.temp >= 55 && r.temp <= 75 ? 100 : r.temp >= 45 && r.temp <= 85 ? 60 : 20;
  const cs = r.turbidity ? Math.max(0, 100 - r.turbidity * 2) : 70;
  const tds = (hr >= 5 && hr <= 9) || (hr >= 17 && hr <= 20) ? 100 : hr >= 10 && hr <= 16 ? 60 : 40;
  return Math.round(ts * 0.3 + cs * 0.25 + 80 * 0.2 + tds * 0.25);
}
function fishLabel(s) { return s >= 90 ? 'Excellent' : s >= 70 ? 'Great' : s >= 50 ? 'Good' : s >= 30 ? 'Fair' : 'Poor'; }
function genTides() {
  const now = new Date(), tides = [];
  for (let i = 0; i < 24; i++) {
    const tm = new Date(now.getTime() + i * 3600000);
    const h = 2.5 + 2.1 * Math.sin((tm.getTime() / 3600000) * Math.PI / 6.2 + 1);
    tides.push({ t: tm, h: Math.abs(h), ty: Math.cos((tm.getTime() / 3600000) * Math.PI / 6.2 + 1) > 0 ? 'high' : 'low' });
  }
  return tides;
}

// ===== COMPONENTS =====
function Card({ children, style }) {
  return <View style={[styles.card, style]}>{children}</View>;
}

function SectionTitle({ text }) {
  return <Text style={styles.sectionTitle}>{text}</Text>;
}

function CircularGauge({ score, label, size = 160 }) {
  const pct = Math.min(100, Math.max(0, score));
  const color = pct >= 80 ? '#00BCD4' : pct >= 60 ? '#4CAF50' : pct >= 40 ? '#FF9800' : '#F44336';
  const radius = (size - 20) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (pct / 100) * circumference;
  return (
    <View style={{ alignItems: 'center', paddingVertical: 10 }}>
      <Svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <G rotation="-90" origin={`${size / 2}, ${size / 2}`}>
          <Circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="#E0E0E0" strokeWidth="12" />
          <Circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke={color} strokeWidth="12"
            strokeDasharray={circumference} strokeDashoffset={strokeDashoffset} strokeLinecap="round" />
        </G>
        <SvgText x={size / 2} y={size / 2 - 5} textAnchor="middle" fontSize="36" fontWeight="bold" fill={color}>{score}</SvgText>
        <SvgText x={size / 2} y={size / 2 + 20} textAnchor="middle" fontSize="11" fill="#5A6B7C">{label}</SvgText>
      </Svg>
    </View>
  );
}

function ProgressBar({ label, score, value }) {
  const color = score >= 80 ? '#4CAF50' : score >= 60 ? '#8BC34A' : score >= 40 ? '#FF9800' : '#F44336';
  return (
    <View style={{ marginBottom: 10 }}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 3 }}>
        <Text style={{ fontSize: 13 }}>{label}</Text>
        <Text style={{ fontSize: 13, fontWeight: '600', color }}>{value}</Text>
      </View>
      <View style={{ height: 18, backgroundColor: '#F0F4F8', borderRadius: 9, overflow: 'hidden' }}>
        <View style={{ height: '100%', width: score + '%', backgroundColor: color, borderRadius: 9 }} />
      </View>
    </View>
  );
}

// ===== SCREENS =====
function HomeScreen() {
  const live = STATIONS.filter(s => s.live);
  const avgTemp = Math.round(live.reduce((a, s) => a + (s.readings.temp || 0), 0) / live.filter(s => s.readings.temp).length);
  const T = genTides();
  const turkey = STATIONS.find(s => s.id === 'turkey');
  const wqi = calcWQI(turkey.readings);
  return (
    <ScrollView style={styles.screen} showsVerticalScrollIndicator={false}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Cornwall RiverWatch</Text>
        <Text style={styles.headerSub}>Cornwall-on-Hudson, NY - Hudson River</Text>
      </View>
      <CircularGauge score={wqi} label="Water Quality Index" />
      <Text style={{ textAlign: 'center', fontSize: 18, fontWeight: '700', color: wqi >= 80 ? '#00BCD4' : wqi >= 60 ? '#8BC34A' : '#FF9800', marginTop: -8, marginBottom: 16 }}>
        {wqiLabel(wqi)}
      </Text>
      <View style={styles.metricsGrid}>
        {[{ i: '\uD83C\uDF21', v: avgTemp + '\u00B0F', l: 'Avg Water Temp' }, { i: '\uD83D\uDCF6', v: '' + live.length, l: 'Stations Live' }, { i: '\uD83C\uDF0A', v: T[0].h.toFixed(1) + 'ft', l: (T[0].ty === 'high' ? 'High' : 'Low') + ' Tide' }, { i: '\uD83D\uDD14', v: '3', l: 'Alerts' }].map((m, idx) => (
          <View key={idx} style={styles.metric}><Text style={{ fontSize: 24 }}>{m.i}</Text><Text style={styles.metricValue}>{m.v}</Text><Text style={styles.metricLabel}>{m.l}</Text></View>
        ))}
      </View>
      <Card>
        <SectionTitle text="Stations Near Cornwall (RM 56)" />
        {STATIONS.map(s => (
          <View key={s.id} style={styles.stationRow}>
            <View style={[styles.dot, { backgroundColor: s.live ? COLORS.success : '#999' }]} />
            <View style={{ flex: 1 }}>
              <Text style={styles.stationName}>{s.name}</Text>
              <Text style={styles.stationLoc}>River Mile {s.rm} - {s.loc}</Text>
              <Text style={styles.stationParams}>
                {s.params.filter(p => s.readings[p] !== undefined).map(p => (PARAMS[p]?.label || p) + ': ' + s.readings[p] + (PARAMS[p]?.unit || '')).join(' - ')}
              </Text>
            </View>
          </View>
        ))}
      </Card>
    </ScrollView>
  );
}

function StationsScreen() {
  return (
    <ScrollView style={styles.screen} showsVerticalScrollIndicator={false}>
      <View style={styles.header}><Text style={styles.headerTitle}>Stations</Text><Text style={styles.headerSub}>Hudson River monitoring network</Text></View>
      {STATIONS.map(s => {
        const q = calcWQI(s.readings);
        return (
          <Card key={s.id}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
              <View style={{ flex: 1 }}>
                <Text style={styles.stationName}>{s.name} <Text style={{ fontSize: 12, color: q >= 80 ? '#00BCD4' : q >= 60 ? '#8BC34A' : '#FF9800' }}>WQI {q}</Text></Text>
                <Text style={styles.stationLoc}>River Mile {s.rm} - {s.loc} - {s.src} - {s.live ? 'LIVE' : 'OFFLINE'}</Text>
              </View>
              <View style={[styles.dot, { backgroundColor: s.live ? COLORS.success : '#999' }]} />
            </View>
            <Text style={[styles.stationParams, { marginTop: 8 }]}>
              {s.params.filter(p => s.readings[p] !== undefined).map(p => (PARAMS[p]?.label || p) + ': ' + s.readings[p] + (PARAMS[p]?.unit || '')).join(' - ')}
            </Text>
          </Card>
        );
      })}
    </ScrollView>
  );
}

function TidesScreen() {
  const T = genTides();
  const cur = T[0];
  const upcoming = T.filter(t => t.t > new Date()).slice(0, 12);
  return (
    <ScrollView style={styles.screen} showsVerticalScrollIndicator={false}>
      <View style={styles.header}><Text style={styles.headerTitle}>Tide Predictions</Text><Text style={styles.headerSub}>Cornwall-on-Hudson - NOAA 8518490</Text></View>
      <Card style={{ alignItems: 'center', padding: 24 }}>
        <Text style={{ fontSize: 48 }}>\uD83C\uDF0A</Text>
        <Text style={{ fontSize: 42, fontWeight: '700', color: COLORS.primary }}>{cur.h.toFixed(1)}<Text style={{ fontSize: 18 }}> ft</Text></Text>
        <Text style={{ fontSize: 15, color: COLORS.textSec, marginTop: 4 }}>{cur.ty === 'high' ? 'High Tide' : 'Low Tide'}</Text>
      </Card>
      <Card>
        <SectionTitle text="Upcoming Tides" />
        {upcoming.map((t, i) => (
          <View key={i} style={{ flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#F0F4F8' }}>
            <Text style={{ fontWeight: '700', color: t.ty === 'high' ? COLORS.primary : COLORS.primaryLight }}>{t.ty === 'high' ? '\u25B2 High' : '\u25BC Low'}</Text>
            <Text>{t.h.toFixed(1)} ft</Text>
            <Text style={{ color: COLORS.textSec }}>{t.t.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}</Text>
          </View>
        ))}
      </Card>
    </ScrollView>
  );
}

function QualityScreen() {
  const turkey = STATIONS.find(s => s.id === 'turkey');
  const wqi = calcWQI(turkey.readings);
  const sw = swimLabel(wqi);
  const turbidity = turkey.readings.turbidity;
  const clarity = turbidity ? clarityLabel(turbidity) : 'No data';
  return (
    <ScrollView style={styles.screen} showsVerticalScrollIndicator={false}>
      <View style={styles.header}><Text style={styles.headerTitle}>Water Quality</Text><Text style={styles.headerSub}>River cleanliness and safety</Text></View>
      <CircularGauge score={wqi} label="Water Quality Index" />
      <View style={[styles.swimCard, { backgroundColor: sw.c + '15' }]}>
        <Text style={{ fontSize: 22, fontWeight: '700', color: sw.c }}>Swimming: {sw.l}</Text>
        <Text style={{ fontSize: 13, color: COLORS.textSec, marginTop: 4 }}>{sw.l === 'Safe' ? 'Water quality is good for swimming.' : sw.l === 'Caution' ? 'Check conditions before swimming.' : 'Avoid swimming.'}</Text>
      </View>
      {turbidity && (
        <Card>
          <SectionTitle text="Water Clarity (Turbidity)" />
          <ProgressBar label="Clarity Score" score={Math.max(0, 100 - turbidity * 2)} value={turbidity + ' NTU - ' + clarity} />
          <Text style={{ textAlign: 'center', padding: 10, borderRadius: 8, backgroundColor: (turbidity < 15 ? '#4CAF50' : turbidity < 50 ? '#FF9800' : '#F44336') + '15', color: turbidity < 15 ? '#4CAF50' : turbidity < 50 ? '#FF9800' : '#F44336', marginTop: 8 }}>
            {clarity} water
          </Text>
        </Card>
      )}
      <Card>
        <SectionTitle text="Turkey Point Readings (closest to Cornwall)" />
        {turkey.params.filter(p => turkey.readings[p] !== undefined).map(p => (
          <View key={p} style={{ flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#F0F4F8' }}>
            <Text>{PARAMS[p]?.label || p}</Text>
            <Text style={{ fontWeight: '700', color: COLORS.primary }}>{turkey.readings[p]} {PARAMS[p]?.unit || ''}</Text>
          </View>
        ))}
      </Card>
    </ScrollView>
  );
}

function FishScreen() {
  const sch = STATIONS.find(s => s.id === 'schodack') || STATIONS[2];
  const hr = new Date().getHours();
  const fs = fishScore(sch.readings, hr);
  const fl = fishLabel(fs);
  const timeLabel = hr >= 5 && hr <= 9 ? 'Morning' : hr >= 10 && hr <= 16 ? 'Afternoon' : hr >= 17 && hr <= 20 ? 'Evening' : 'Night';
  const timeScore = (hr >= 5 && hr <= 9) || (hr >= 17 && hr <= 20) ? 100 : hr >= 10 && hr <= 16 ? 60 : 40;
  return (
    <ScrollView style={styles.screen} showsVerticalScrollIndicator={false}>
      <View style={styles.header}><Text style={styles.headerTitle}>Fishing Conditions</Text><Text style={styles.headerSub}>Hudson River at Cornwall, NY</Text></View>
      <CircularGauge score={fs} label="Fishing Score" />
      <Text style={{ textAlign: 'center', fontSize: 20, fontWeight: '700', color: fs >= 70 ? '#4CAF50' : fs >= 50 ? '#8BC34A' : '#FF9800', marginTop: -8, marginBottom: 16 }}>{fl}</Text>
      <Card>
        <SectionTitle text="Score Breakdown" />
        <ProgressBar label="Water Temp" score={sch.readings.temp >= 55 && sch.readings.temp <= 75 ? 100 : sch.readings.temp >= 45 && sch.readings.temp <= 85 ? 60 : 20} value={sch.readings.temp + '\u00B0F'} />
        <ProgressBar label="Water Clarity" score={sch.readings.turbidity ? Math.max(0, 100 - sch.readings.turbidity * 2) : 70} value={(sch.readings.turbidity || '?') + ' NTU'} />
        <ProgressBar label="Time of Day" score={timeScore} value={timeLabel} />
      </Card>
      <Card>
        <SectionTitle text="Best Fishing Windows" />
        <View style={styles.fishGrid}>
          {[{ t: '5:30-8:30 AM', l: 'Dawn Bite', r: 'Excellent' }, { t: '5:30-8:30 PM', l: 'Dusk Bite', r: 'Great' }].map((w, i) => (
            <View key={i} style={styles.fishWindow}>
              <Text style={{ fontSize: 28 }}>{i === 0 ? '\uD83C\uDF05' : '\uD83C\uDF06'}</Text>
              <Text style={{ fontWeight: '600', marginTop: 4 }}>{w.t}</Text>
              <Text style={{ fontSize: 12, color: COLORS.success }}>{w.l} - {w.r}</Text>
            </View>
          ))}
        </View>
      </Card>
    </ScrollView>
  );
}

function AlertsScreen() {
  const alerts = [
    { s: 'Schodack Landing', t: 'Temperature Spike', sev: 'medium', time: '2h ago', act: '72.4\u00B0F', exp: '65-68\u00B0F' },
    { s: 'Albany', t: 'Low DO Reading', sev: 'high', time: '1h ago', act: '4.2 mg/L', exp: '>6 mg/L' },
    { s: 'Turkey Point', t: 'Conductance Drop', sev: 'low', time: '4h ago', act: '180 \u03BCS/cm', exp: '250-350' },
  ];
  return (
    <ScrollView style={styles.screen} showsVerticalScrollIndicator={false}>
      <View style={styles.header}><Text style={styles.headerTitle}>Alerts</Text><Text style={styles.headerSub}>AI-detected anomalies</Text></View>
      {alerts.map((a, i) => (
        <View key={i} style={[styles.alertCard, { borderLeftColor: a.sev === 'high' ? COLORS.danger : a.sev === 'medium' ? COLORS.accent : COLORS.primary }]}>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 }}>
            <Text style={{ fontWeight: '600' }}>{a.s}</Text>
            <Text style={{ fontSize: 11, color: COLORS.textSec }}>{a.time}</Text>
          </View>
          <Text style={{ marginBottom: 4 }}>{a.t}</Text>
          <Text style={{ fontSize: 12, color: COLORS.textSec }}>Actual: <Text style={{ fontWeight: '700', color: COLORS.text }}>{a.act}</Text> - Expected: {a.exp}</Text>
        </View>
      ))}
      <Card>
        <SectionTitle text="About These Alerts" />
        <Text style={{ fontSize: 13, color: COLORS.textSec }}>Our system monitors HRECOS station data in real-time and flags readings outside normal ranges. Always verify conditions before making water activity decisions.</Text>
      </Card>
    </ScrollView>
  );
}

// ===== NAVIGATION =====
const Tab = createBottomTabNavigator();

function App() {
  return (
    <NavigationContainer>
      <SafeAreaView style={{ flex: 1, backgroundColor: COLORS.bg }}>
        <StatusBar barStyle="light-content" backgroundColor={COLORS.primaryDark} />
        <Tab.Navigator
          screenOptions={({ route }) => ({
            tabBarIcon: ({ focused, color }) => {
              const icons = { Home: 'home', Stations: 'map-marker', Tides: 'waves', Quality: 'water-check', Fish: 'fish', Alerts: 'bell' };
              return <MaterialCommunityIcons name={icons[route.name] || 'help'} size={24} color={color} />;
            },
            tabBarActiveTintColor: COLORS.primary,
            tabBarInactiveTintColor: COLORS.textSec,
            tabBarStyle: { backgroundColor: COLORS.surface, borderTopColor: COLORS.border, paddingBottom: 6, height: 60 },
            tabBarLabelStyle: { fontSize: 11, fontWeight: '500' },
            headerShown: false,
          })}
        >
          <Tab.Screen name="Home" component={HomeScreen} />
          <Tab.Screen name="Stations" component={StationsScreen} />
          <Tab.Screen name="Tides" component={TidesScreen} />
          <Tab.Screen name="Quality" component={QualityScreen} />
          <Tab.Screen name="Fish" component={FishScreen} />
          <Tab.Screen name="Alerts" component={AlertsScreen} />
        </Tab.Navigator>
      </SafeAreaView>
    </NavigationContainer>
  );
}

// ===== STYLES =====
const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: COLORS.bg },
  header: { backgroundColor: COLORS.primary, paddingHorizontal: 20, paddingVertical: 16, borderBottomLeftRadius: 20, borderBottomRightRadius: 20 },
  headerTitle: { fontSize: 22, fontWeight: '700', color: '#FFF' },
  headerSub: { fontSize: 12, color: '#FFF', opacity: 0.8 },
  card: { backgroundColor: COLORS.surface, borderRadius: 16, padding: 16, marginHorizontal: 12, marginBottom: 12, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.08, shadowRadius: 8, elevation: 3 },
  sectionTitle: { fontSize: 13, fontWeight: '700', color: COLORS.textSec, marginBottom: 10, textTransform: 'uppercase', letterSpacing: 0.5 },
  metricsGrid: { flexDirection: 'row', flexWrap: 'wrap', paddingHorizontal: 12, gap: 10, marginBottom: 12 },
  metric: { backgroundColor: COLORS.surface, borderRadius: 14, padding: 14, alignItems: 'center', width: (Dimensions.get('window').width - 44) / 2, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.08, shadowRadius: 8, elevation: 3 },
  metricValue: { fontSize: 22, fontWeight: '700', color: COLORS.primary },
  metricLabel: { fontSize: 11, color: COLORS.textSec, marginTop: 2 },
  dot: { width: 10, height: 10, borderRadius: 5, marginRight: 12 },
  stationRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
  stationName: { fontWeight: '600', fontSize: 15 },
  stationLoc: { fontSize: 12, color: COLORS.textSec },
  stationParams: { fontSize: 12, color: COLORS.textSec, flexWrap: 'wrap' },
  swimCard: { marginHorizontal: 12, marginBottom: 16, padding: 20, borderRadius: 16, alignItems: 'center' },
  fishGrid: { flexDirection: 'row', gap: 10 },
  fishWindow: { flex: 1, backgroundColor: COLORS.surface, borderRadius: 12, padding: 14, alignItems: 'center' },
  alertCard: { backgroundColor: COLORS.surface, borderLeftWidth: 4, padding: 12, marginHorizontal: 12, marginBottom: 8, borderRadius: 0, borderTopRightRadius: 12, borderBottomRightRadius: 12, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.08, shadowRadius: 8, elevation: 3 },
});

export default App;