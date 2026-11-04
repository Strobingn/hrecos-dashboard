import React, { createContext, useContext, useEffect, useState, useCallback, useMemo } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { DEFAULT_WEATHER_ALERTS, validateWeatherAlerts } from '../utils/weather';

const PreferencesContext = createContext(null);
const UNITS_KEY = '@hrecos_units';
const WEATHER_KEY = '@hrecos_weather_alerts';

export function PreferencesProvider({ children }) {
  const [units, setUnitsState] = useState('imperial');
  const [weatherSettings, setWeatherState] = useState(DEFAULT_WEATHER_ALERTS);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [savedUnits, savedWeather] = await Promise.all([
          AsyncStorage.getItem(UNITS_KEY), AsyncStorage.getItem(WEATHER_KEY),
        ]);
        if (cancelled) return;
        if (savedUnits === 'metric' || savedUnits === 'imperial') setUnitsState(savedUnits);
        if (savedWeather) {
          try { setWeatherState(validateWeatherAlerts(JSON.parse(savedWeather))); }
          catch { /* Invalid saved limits fall back to the defaults. */ }
        }
      } catch (error) {
        console.warn('Could not load display preferences:', error);
      } finally {
        if (!cancelled) setLoaded(true);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  const setUnits = useCallback(async (value) => {
    if (!['metric', 'imperial'].includes(value)) return;
    await AsyncStorage.setItem(UNITS_KEY, value);
    setUnitsState(value);
  }, []);

  const setWeatherSettings = useCallback(async (value) => {
    const valid = validateWeatherAlerts(value);
    await AsyncStorage.setItem(WEATHER_KEY, JSON.stringify(valid));
    setWeatherState(valid);
  }, []);

  const value = useMemo(() => ({ units, setUnits, weatherSettings, setWeatherSettings }), [units, setUnits, weatherSettings, setWeatherSettings]);
  if (!loaded) return null;
  return <PreferencesContext.Provider value={value}>{children}</PreferencesContext.Provider>;
}

export function usePreferences() {
  const context = useContext(PreferencesContext);
  if (!context) throw new Error('usePreferences requires PreferencesProvider');
  return context;
}
