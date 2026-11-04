import React, { useEffect, useState } from 'react';
import { View, Text, TextInput, Switch, TouchableOpacity, StyleSheet } from 'react-native';
import { useTheme } from '../../hooks/useTheme';
import { usePreferences } from '../../context/PreferencesContext';
import { weatherSettingsDraft, parseWeatherSettingsDraft } from '../../utils/weather';

export default function WeatherSettings() {
  const { colors } = useTheme();
  const { units, weatherSettings, setWeatherSettings } = usePreferences();
  const metric = units === 'metric';
  const [draft, setDraft] = useState({});
  const [message, setMessage] = useState('');
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    setDraft(weatherSettingsDraft(weatherSettings, units));
  }, [units, weatherSettings]);
  const update = (key, value) => { setDraft((previous) => ({ ...previous, [key]: value })); setMessage(''); };
  const save = async () => {
    setSaving(true);
    setMessage('');
    try {
      await setWeatherSettings(parseWeatherSettingsDraft(draft, weatherSettings, units));
      setMessage('Weather alert preferences saved.');
    } catch (error) {
      setMessage(error.message || 'Could not save settings. Please try again.');
    } finally { setSaving(false); }
  };
  return (
    <View style={[styles.card, { backgroundColor: colors.card, borderColor: colors.border }]}>
      <View style={styles.row}>
        <View style={styles.grow}>
          <Text style={[styles.title, { color: colors.text }]}>Weather alerts</Text>
          <Text style={[styles.note, { color: colors.textSecondary }]}>West Point / Cornwall area</Text>
        </View>
        <Switch accessibilityLabel="Enable in-app weather alerts" value={!!draft.enabled} onValueChange={(value) => update('enabled', value)} trackColor={{ true: colors.primary, false: colors.divider }} />
      </View>
      <Text style={[styles.note, { color: colors.textSecondary }]}>Choose your limits. Warnings appear on Home and Alerts while you use the app. Rain limits apply to an hourly forecast total.</Text>
      {[
        ['wind', `Sustained wind (${metric ? 'km/h' : 'mph'})`, metric ? '1.6–241' : '1–150'],
        ['gust', `Wind gusts (${metric ? 'km/h' : 'mph'})`, metric ? '1.6–322' : '1–200'],
        ['rain', `Hourly rain (${metric ? 'mm' : 'in'})`, metric ? '0.1–100' : '0.004–3.937'],
      ].map(([key, label, range]) => (
        <View key={key} style={styles.inputRow}>
          <View style={styles.grow}>
            <Text style={[styles.label, { color: colors.text }]}>{label}</Text>
            <Text style={[styles.note, { color: colors.textSecondary }]}>{range}</Text>
          </View>
          <TextInput accessibilityLabel={label} value={draft[key] ?? ''} onChangeText={(value) => update(key, value)} keyboardType="decimal-pad" selectTextOnFocus style={[styles.input, { color: colors.text, backgroundColor: colors.surfaceVariant, borderColor: colors.border }]} />
        </View>
      ))}
      <Text style={[styles.label, { color: colors.text }]}>Look ahead</Text>
      <View style={styles.windows}>
        {[3, 6, 12, 24].map((hours) => <TouchableOpacity key={hours} onPress={() => update('hours', hours)} accessibilityRole="button" accessibilityState={{ selected: draft.hours === hours }} style={[styles.chip, { backgroundColor: draft.hours === hours ? colors.primary : colors.surfaceVariant }]}>
          <Text style={{ color: draft.hours === hours ? '#FFFFFF' : colors.text, fontWeight: '600' }}>{hours}h</Text>
        </TouchableOpacity>)}
      </View>
      <TouchableOpacity onPress={save} disabled={saving} accessibilityRole="button" style={[styles.save, { backgroundColor: colors.primary, opacity: saving ? 0.6 : 1 }]}>
        <Text style={styles.saveText}>{saving ? 'Saving…' : 'Save weather alerts'}</Text>
      </TouchableOpacity>
      {!!message && <Text accessibilityLiveRegion="polite" style={[styles.note, { color: colors.text }]}>{message}</Text>}
    </View>
  );
}
const styles = StyleSheet.create({
  card: { borderRadius: 22, borderWidth: 1, padding: 20, gap: 16 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  grow: { flex: 1 },
  title: { fontSize: 20, fontWeight: '700', letterSpacing: -0.5 },
  label: { fontSize: 13, fontWeight: '600' },
  note: { fontSize: 12, lineHeight: 19 },
  inputRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  input: { borderRadius: 12, borderWidth: 1, paddingHorizontal: 14, paddingVertical: 12, width: 100, minHeight: 48, fontSize: 17, textAlign: 'right' },
  windows: { flexDirection: 'row', gap: 8 },
  chip: { flex: 1, minHeight: 44, alignItems: 'center', justifyContent: 'center', borderRadius: 12 },
  save: { minHeight: 48, borderRadius: 14, alignItems: 'center', justifyContent: 'center' },
  saveText: { color: '#FFFFFF', fontWeight: '700', fontSize: 14 },
});
