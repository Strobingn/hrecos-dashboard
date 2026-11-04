import test from 'node:test';
import assert from 'node:assert/strict';
import { measurement, formatMeasurement } from '../src/utils/measurements.js';
import { DEFAULT_WEATHER_ALERTS, validateWeatherAlerts, weatherSettingsDraft, parseWeatherSettingsDraft, normalizeWeather, weatherAlerts } from '../src/utils/weather.js';

const now = Date.UTC(2026, 10, 4, 15, 30);
const hour = 3600000;
const settings = { ...DEFAULT_WEATHER_ALERTS };
function forecast(overrides = {}) {
  return { updatedAt: now, current: { time: now, wind: 4, gust: 8, temperature: 68 }, hours: Array.from({ length: 24 }, (_, i) => ({ time: now + (i + 0.5) * hour, wind: 5, gust: 10, rain: 0, ...overrides })) };
}

test('API Fahrenheit values switch to Celsius and back without changing raw readings', () => {
  const raw = { temp: 68, air_temp: 32, dewpoint: 50 };
  assert.equal(formatMeasurement(raw.temp, 'temp'), '68.0°F');
  assert.equal(formatMeasurement(raw.temp, 'temp', 'metric'), '20.0°C');
  assert.equal(formatMeasurement(raw.temp, 'temp', 'imperial'), '68.0°F');
  assert.equal(formatMeasurement(raw.air_temp, 'air_temp', 'metric'), '0.0°C');
  assert.equal(formatMeasurement(raw.dewpoint, 'dewpoint', 'metric'), '10.0°C');
  assert.deepEqual(raw, { temp: 68, air_temp: 32, dewpoint: 50 });
});

test('zero is a valid temperature and missing readings stay missing', () => {
  assert.equal(formatMeasurement(0, 'temp'), '0.0°F');
  assert.equal(formatMeasurement(0, 'temp', 'metric'), '-17.8°C');
  for (const value of [null, undefined, NaN, Infinity, '', '--']) assert.equal(formatMeasurement(value, 'temp'), '—');
});

test('wind, tide, pressure and rain values convert with their labels', () => {
  assert.equal(formatMeasurement(10, 'wind_speed', 'metric'), '16.1 km/h');
  assert.equal(formatMeasurement(10, 'tide', 'metric'), '3.0 m');
  assert.equal(formatMeasurement(1, 'rain', 'metric'), '25.4 mm');
  assert.equal(formatMeasurement(30, 'pressure', 'metric'), '1015.9 hPa');
  assert.deepEqual(measurement(0, 'ph', 'metric', 'pH'), { value: 0, unit: 'pH' });
});

test('wind, gust and rain thresholds trigger independently at the limit', () => {
  const data = forecast({ wind: 20, gust: 30, rain: 5 });
  assert.deepEqual(weatherAlerts(data, settings, now).map((a) => a.type), ['wind', 'gust', 'rain']);
  assert.equal(weatherAlerts(data, { ...settings, windMph: 21, gustMph: 31, rainMm: 6 }, now).length, 0);
});

test('current wind can trigger an alert even when the hourly forecast is lower', () => {
  const data = forecast();
  data.current.wind = 24;
  assert.equal(weatherAlerts(data, settings, now)[0].peak, 24);
});

test('alerts honor the enabled switch, forecast window and data freshness', () => {
  const data = forecast();
  data.hours[8].wind = 50;
  assert.equal(weatherAlerts(data, settings, now).length, 0);
  assert.equal(weatherAlerts(data, { ...settings, hours: 12 }, now).length, 1);
  assert.equal(weatherAlerts(data, { ...settings, hours: 12, enabled: false }, now).length, 0);
  assert.equal(weatherAlerts({ ...data, updatedAt: now - hour }, { ...settings, hours: 12 }, now).length, 0);
});

test('rain from an already ended hour does not trigger a future-rain warning', () => {
  const data = forecast();
  data.hours.unshift({ time: now - hour / 2, wind: 0, gust: 0, rain: 40 });
  assert.equal(weatherAlerts(data, settings, now).length, 0);
});

test('missing or zero forecast values do not become heavy weather', () => {
  assert.equal(weatherAlerts(forecast({ wind: null, gust: null, rain: null }), settings, now).length, 0);
  assert.equal(weatherAlerts(forecast({ wind: 0, gust: 0, rain: 0 }), settings, now).length, 0);
});

test('invalid alert thresholds are rejected before persistence', () => {
  for (const value of [0, -1, Infinity, NaN, '20', null]) assert.throws(() => validateWeatherAlerts({ ...settings, windMph: value }));
  assert.throws(() => validateWeatherAlerts({ ...settings, rainMm: 0 }));
  assert.throws(() => validateWeatherAlerts({ ...settings, hours: 0 }));
});

test('unit switching and saving preserves exact weather thresholds', () => {
  for (const units of ['imperial', 'metric']) {
    for (const original of [settings, { ...settings, windMph: 150, gustMph: 200, rainMm: 100 }]) {
      assert.deepEqual(parseWeatherSettingsDraft(weatherSettingsDraft(original, units), original, units), original);
    }
  }
});

test('edited metric limits and imperial rain limits persist in canonical units', () => {
  const metric = weatherSettingsDraft(settings, 'metric');
  const edited = parseWeatherSettingsDraft({ ...metric, wind: '16.09344', rain: '10' }, settings, 'metric');
  assert.equal(edited.windMph, 10);
  assert.equal(edited.rainMm, 10);
  const imperial = weatherSettingsDraft(settings, 'imperial');
  assert.equal(parseWeatherSettingsDraft({ ...imperial, rain: '1' }, settings, 'imperial').rainMm, 25.4);
  assert.throws(() => parseWeatherSettingsDraft({ ...imperial, rain: '' }, settings, 'imperial'));
});

test('provider timestamps use UTC seconds and missing array values remain null', () => {
  const data = normalizeWeather({ current: { time: now / 1000, temperature_2m: 68, wind_speed_10m: 0 }, hourly: { time: [(now + hour) / 1000], rain: [0] } }, now);
  assert.equal(data.current.time, now);
  assert.equal(data.current.temperature, 68);
  assert.equal(data.current.wind, 0);
  assert.equal(data.hours[0].time, now + hour);
  assert.equal(data.hours[0].rain, 0);
  assert.equal(data.hours[0].gust, null);
  assert.throws(() => normalizeWeather({}, now));
  assert.throws(() => normalizeWeather({ current: { time: now / 1000 }, hourly: { time: [(now - 2 * hour) / 1000] } }, now));
});
