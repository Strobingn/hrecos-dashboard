// API readings stay in imperial units. Convert only for display.
const PARAMETERS = {
  temp: ['°F', '°C', (v) => (v - 32) * 5 / 9],
  air_temp: ['°F', '°C', (v) => (v - 32) * 5 / 9],
  dewpoint: ['°F', '°C', (v) => (v - 32) * 5 / 9],
  wind_speed: ['mph', 'km/h', (v) => v * 1.609344],
  wind_gusts: ['mph', 'km/h', (v) => v * 1.609344],
  pressure: ['inHg', 'hPa', (v) => v * 33.86389],
  tide: ['ft', 'm', (v) => v * 0.3048],
  depth: ['ft', 'm', (v) => v * 0.3048],
  flow: ['ft³/s', 'm³/s', (v) => v * 0.0283168466],
  rain: ['in', 'mm', (v) => v * 25.4],
};

export function measurement(value, parameter, units = 'imperial', fallbackUnit = '') {
  const spec = PARAMETERS[parameter];
  const metric = units === 'metric';
  const unit = spec ? spec[metric ? 1 : 0] : fallbackUnit;
  if (value == null || value === '' || !Number.isFinite(Number(value))) return { value: null, unit };
  const numeric = Number(value);
  return { value: spec && metric ? spec[2](numeric) : numeric, unit };
}

export function formatMeasurement(value, parameter, units = 'imperial', digits = 1, fallbackUnit = '') {
  const result = measurement(value, parameter, units, fallbackUnit);
  if (result.value == null) return '—';
  return `${result.value.toFixed(digits)}${result.unit.startsWith('°') ? '' : ' '}${result.unit}`.trim();
}
