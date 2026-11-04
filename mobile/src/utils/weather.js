export const DEFAULT_WEATHER_ALERTS = Object.freeze({
  enabled: true,
  windMph: 20,
  gustMph: 30,
  rainMm: 5,
  hours: 6,
});

export function validateWeatherAlerts(value) {
  const limits = { windMph: [1, 150], gustMph: [1, 200], rainMm: [0.1, 100] };
  for (const [key, [min, max]] of Object.entries(limits)) {
    if (typeof value[key] !== 'number' || !Number.isFinite(value[key]) || value[key] < min || value[key] > max) {
      throw new Error('Enter positive wind and rain limits within the displayed ranges.');
    }
  }
  if (![3, 6, 12, 24].includes(value.hours)) throw new Error('Choose a forecast window.');
  if (typeof value.enabled !== 'boolean') throw new Error('Choose whether weather alerts are enabled.');
  return { enabled: value.enabled, windMph: value.windMph, gustMph: value.gustMph, rainMm: value.rainMm, hours: value.hours };
}

export function weatherSettingsDraft(settings, units) {
  const metric = units === 'metric';
  return {
    enabled: settings.enabled,
    wind: (settings.windMph * (metric ? 1.609344 : 1)).toFixed(1),
    gust: (settings.gustMph * (metric ? 1.609344 : 1)).toFixed(1),
    rain: (settings.rainMm / (metric ? 1 : 25.4)).toFixed(metric ? 1 : 3),
    hours: settings.hours,
  };
}

export function parseWeatherSettingsDraft(draft, settings, units) {
  const metric = units === 'metric';
  const original = weatherSettingsDraft(settings, units);
  return validateWeatherAlerts({
    enabled: draft.enabled,
    windMph: draft.wind === original.wind ? settings.windMph : Number(draft.wind) / (metric ? 1.609344 : 1),
    gustMph: draft.gust === original.gust ? settings.gustMph : Number(draft.gust) / (metric ? 1.609344 : 1),
    rainMm: draft.rain === original.rain ? settings.rainMm : Number(draft.rain) * (metric ? 1 : 25.4),
    hours: draft.hours,
  });
}

export function normalizeWeather(payload, now = Date.now()) {
  const current = payload?.current;
  const hourly = payload?.hourly;
  if (!Number.isFinite(current?.time) || !Array.isArray(hourly?.time)) throw new Error('Weather provider returned an incomplete forecast.');
  const finite = (value) => typeof value === 'number' && Number.isFinite(value) ? value : null;
  const hours = hourly.time.map((time, i) => ({
    time: time * 1000,
    temperature: finite(hourly.temperature_2m?.[i]),
    wind: finite(hourly.wind_speed_10m?.[i]),
    gust: finite(hourly.wind_gusts_10m?.[i]),
    rain: finite(hourly.rain?.[i]),
    probability: finite(hourly.precipitation_probability?.[i]),
    code: finite(hourly.weather_code?.[i]),
  })).filter((row) => Number.isFinite(row.time) && row.time + 3600000 > now);
  if (!hours.length) throw new Error('Weather forecast has expired. Pull to refresh.');
  return {
    updatedAt: now,
    current: {
      time: current.time * 1000,
      temperature: finite(current.temperature_2m),
      wind: finite(current.wind_speed_10m),
      gust: finite(current.wind_gusts_10m),
      code: finite(current.weather_code),
    },
    hours,
  };
}

export function weatherAlerts(weather, settings, now = Date.now()) {
  if (!settings.enabled || !weather || now - weather.updatedAt > 30 * 60000) return [];
  const end = now + settings.hours * 3600000;
  const rows = weather.hours.filter((row) => row.time + 3600000 > now && row.time <= end);
  const current = weather.current;
  const alerts = [];
  for (const [type, threshold, title] of [
    ['wind', settings.windMph, 'Strong wind'],
    ['gust', settings.gustMph, 'Strong gusts'],
    ['rain', settings.rainMm, 'Heavy rain'],
  ]) {
    // Hourly rain is the total for the hour ending at the forecast timestamp.
    const candidates = type === 'rain' ? rows.filter((row) => row.time > now) : [current, ...rows];
    const exceeded = candidates.filter((row) => Number.isFinite(row[type]) && row[type] >= threshold);
    if (!exceeded.length) continue;
    const first = exceeded[0];
    const peak = Math.max(...exceeded.map((row) => row[type]));
    alerts.push({ id: `weather-${type}`, type, title, peak, threshold, time: first.time, severity: 'warning' });
  }
  return alerts;
}

export function weatherDescription(code) {
  if (code === 0) return 'Clear sky';
  if (code != null && code <= 3) return 'Partly cloudy';
  if ([45, 48].includes(code)) return 'Fog';
  if (code >= 51 && code <= 57) return 'Drizzle';
  if (code >= 61 && code <= 67) return 'Rain';
  if (code >= 71 && code <= 77) return 'Snow';
  if (code >= 80 && code <= 82) return 'Rain showers';
  if (code >= 85 && code <= 86) return 'Snow showers';
  if (code >= 95) return 'Thunderstorms';
  return 'Weather conditions';
}
