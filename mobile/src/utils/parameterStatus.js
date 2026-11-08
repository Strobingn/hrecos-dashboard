/**
 * Hudson River status bands. Temperatures are Fahrenheit.
 * Higher water-quality scores are better.
 */

function band(label, color) {
  return { label, color };
}

const GREEN = '#43A047';
const TEAL = '#00ACC1';
const AMBER = '#FFB300';
const ORANGE = '#FB8C00';
const RED = '#E53935';
const BLUE = '#1E88E5';
const GRAY = '#8A96A5';

function numberOrNull(value) {
  const n = typeof value === 'number' ? value : parseFloat(value);
  return Number.isFinite(n) ? n : null;
}

/**
 * Status for one live reading. Returns a label for every parameter that
 * has a reasonable Hudson range, instead of "Unknown".
 */
function classifyParameter(param, value) {
  const n = numberOrNull(value);
  if (n == null) return band('No data', GRAY);

  switch (param) {
    case 'temp':
    case 'water_temp':
      if (n >= 45 && n <= 70) return band('Normal', GREEN);
      if (n >= 35 && n < 45) return band('Cool', TEAL);
      if (n > 70 && n <= 78) return band('Warm', AMBER);
      if (n > 78 && n <= 85) return band('Hot', ORANGE);
      if (n < 35 && n >= 32) return band('Cold', TEAL);
      return band(n < 32 ? 'Freezing' : 'Extreme', RED);
    case 'air_temp':
      if (n >= 20 && n <= 85) return band('Normal', GREEN);
      if (n > 85 && n <= 95) return band('Warm', AMBER);
      return band(n < 20 ? 'Cold' : 'Hot', ORANGE);
    case 'do':
    case 'dissolved_oxygen':
      if (n >= 8) return band('Excellent', GREEN);
      if (n >= 6) return band('Good', '#8BC34A');
      if (n >= 4) return band('Fair', AMBER);
      return band('Poor', RED);
    case 'do_sat':
    case 'dissolved_oxygen_saturation':
      if (n >= 85 && n <= 110) return band('Excellent', GREEN);
      if ((n >= 70 && n < 85) || (n > 110 && n <= 120)) return band('Good', '#8BC34A');
      if (n >= 50 && n < 70) return band('Fair', AMBER);
      return band(n < 50 ? 'Low' : 'Supersaturated', ORANGE);
    case 'ph':
      if (n >= 6.8 && n <= 8.2) return band('Optimal', GREEN);
      if (n >= 6.5 && n <= 8.6) return band('Good', '#8BC34A');
      if (n >= 6 && n <= 9) return band('Fair', AMBER);
      return band('Poor', RED);
    case 'turbidity':
      if (n < 10) return band('Clear', GREEN);
      if (n <= 25) return band('Typical', TEAL);
      if (n <= 50) return band('Elevated', AMBER);
      return band('High', ORANGE);
    case 'conductivity':
    case 'conductance':
      if (n < 800) return band('Fresh', GREEN);
      if (n < 5000) return band('Slightly brackish', TEAL);
      if (n < 20000) return band('Brackish', BLUE);
      if (n < 45000) return band('Saline', BLUE);
      return band('Very saline', ORANGE);
    case 'salinity':
      if (n < 0.5) return band('Fresh', GREEN);
      if (n < 5) return band('Oligohaline', TEAL);
      if (n < 18) return band('Brackish', BLUE);
      return band('Saline', BLUE);
    case 'chlorophyll':
      if (n < 2) return band('Low', GREEN);
      if (n <= 10) return band('Moderate', TEAL);
      if (n <= 30) return band('Elevated', AMBER);
      return band('Bloom', ORANGE);
    case 'phycocyanin':
      if (n < 2) return band('Low', GREEN);
      if (n <= 8) return band('Moderate', TEAL);
      return band('Elevated', AMBER);
    case 'depth':
      if (n < 1) return band('Surface', TEAL);
      if (n <= 20) return band('Typical', GREEN);
      return band('Deep', BLUE);
    case 'speed':
    case 'flow':
      if (n < 0.3) return band('Slow', TEAL);
      if (n <= 1.5) return band('Moderate', GREEN);
      if (n <= 3) return band('Fast', AMBER);
      return band('Very fast', ORANGE);
    default:
      return band('Recorded', GRAY);
  }
}

function getWQILevel(wqi) {
  const score = Number(wqi);
  if (!Number.isFinite(score)) {
    return { label: 'Unknown', color: GRAY, description: 'Water quality is unavailable.' };
  }
  if (score >= 90) {
    return { label: 'Excellent', color: '#28A745', description: 'Water quality is excellent.' };
  }
  if (score >= 75) {
    return { label: 'Good', color: '#43A047', description: 'Water quality is good.' };
  }
  if (score >= 55) {
    return { label: 'Fair', color: '#F9A825', description: 'Water quality is fair.' };
  }
  if (score >= 35) {
    return { label: 'Poor', color: '#FB8C00', description: 'Water quality is poor.' };
  }
  return { label: 'Bad', color: '#E53935', description: 'Water quality is very poor.' };
}

function windowExtent(points, current) {
  const values = [];
  (points || []).forEach((point) => {
    const n = numberOrNull(point?.value);
    if (n != null) values.push(n);
  });
  const live = numberOrNull(current);
  if (live != null) values.push(live);
  if (!values.length) return { min: null, max: null };
  return { min: Math.min(...values), max: Math.max(...values) };
}

function formatStat(value) {
  const n = numberOrNull(value);
  if (n == null) return '--';
  const digits = Math.abs(n) >= 100 ? 1 : 2;
  return String(Number(n.toFixed(digits)));
}

module.exports = {
  classifyParameter,
  getWQILevel,
  windowExtent,
  formatStat,
};
