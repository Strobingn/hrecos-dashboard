// ============================================================================
// HRECOS RiverWatch - Application Constants
// Station data, API configuration, and parameter metadata
// Station list: data/stations.json (copied to mobile/src/data/stations.json)
// ============================================================================

import registry from '../data/stations.json';

// =============================================================================
// STATIONS - shared registry
// =============================================================================

const PROVIDER_LABEL = { usgs: 'USGS', noaa: 'NOAA', ndbc: 'NDBC', hrecos: 'HRECOS' };

export const STATIONS = registry.stations.map((station) => ({
  id: station.key,
  name: station.name,
  shortName: station.name,
  location: station.place || '',
  lat: station.lat,
  lon: station.lon,
  riverMile: station.river_mile,
  source: PROVIDER_LABEL[station.provider] || station.provider,
  sourceId: station.id,
  params: (station.parameters || []).map((param) => param.field),
  live: !!station.live,
  focus: !!station.focus,
  description: station.note || '',
}));

// Station lookup by ID
export const STATIONS_BY_ID = STATIONS.reduce((acc, station) => {
  acc[station.id] = station;
  return acc;
}, {});

// =============================================================================
// API CONFIGURATION
// =============================================================================

export const API_BASE_URL = 'https://hrecos.yourdomain.com';
export const REFRESH_INTERVAL = 300000; // 5 minutes in milliseconds
export const REQUEST_TIMEOUT = 15000; // 15 seconds

// =============================================================================
// PARAMETER METADATA
// =============================================================================

export const PARAM_INFO = {
  temp: {
    label: 'Water Temperature',
    shortLabel: 'Temp',
    unit: '°F',
    metricUnit: '°C',
    icon: 'thermometer',
    iconFamily: 'MaterialCommunityIcons',
    idealRange: { min: 50, max: 80 },
    description: 'Surface water temperature measured at 1-meter depth.',
    category: 'physical',
  },
  air_temp: {
    label: 'Air Temperature',
    shortLabel: 'Air Temp',
    unit: '°F',
    metricUnit: '°C',
    icon: 'thermometer-lines',
    iconFamily: 'MaterialCommunityIcons',
    idealRange: { min: 60, max: 90 },
    description: 'Ambient air temperature at 2 meters above water surface.',
    category: 'meteorological',
  },
  wind_speed: {
    label: 'Wind Speed',
    shortLabel: 'Wind',
    unit: 'mph',
    metricUnit: 'm/s',
    icon: 'weather-windy',
    iconFamily: 'MaterialCommunityIcons',
    idealRange: { min: 0, max: 15 },
    description: 'Sustained wind speed averaged over 10 minutes.',
    category: 'meteorological',
  },
  wind_direction: {
    label: 'Wind Direction',
    shortLabel: 'Wind Dir',
    unit: '°',
    metricUnit: '°',
    icon: 'compass',
    iconFamily: 'MaterialCommunityIcons',
    idealRange: null,
    description: 'Direction from which the wind is blowing, in degrees true.',
    category: 'meteorological',
  },
  pressure: {
    label: 'Barometric Pressure',
    shortLabel: 'Pressure',
    unit: 'inHg',
    metricUnit: 'hPa',
    icon: 'gauge',
    iconFamily: 'MaterialCommunityIcons',
    idealRange: { min: 29.8, max: 30.4 },
    description: 'Atmospheric pressure measured at station elevation.',
    category: 'meteorological',
  },
  dewpoint: {
    label: 'Dew Point',
    shortLabel: 'Dew Pt',
    unit: '°F',
    metricUnit: '°C',
    icon: 'water-outline',
    iconFamily: 'MaterialCommunityIcons',
    idealRange: { min: 45, max: 65 },
    description: 'Temperature at which air becomes saturated with moisture.',
    category: 'meteorological',
  },
  conductance: {
    label: 'Specific Conductance',
    shortLabel: 'Conductance',
    unit: 'μS/cm',
    metricUnit: 'μS/cm',
    icon: 'lightning-bolt',
    iconFamily: 'MaterialCommunityIcons',
    idealRange: { min: 100, max: 50000 },
    description: 'Measure of water\'s ability to conduct electrical current. Indicates salinity/freshwater mixing.',
    category: 'physical',
  },
  dissolved_oxygen: {
    label: 'Dissolved Oxygen',
    shortLabel: 'DO',
    unit: 'mg/L',
    metricUnit: 'mg/L',
    icon: 'water',
    iconFamily: 'MaterialCommunityIcons',
    idealRange: { min: 6, max: 14 },
    description: 'Concentration of oxygen dissolved in water. Critical for aquatic life.',
    category: 'chemical',
  },
  turbidity: {
    label: 'Turbidity',
    shortLabel: 'Turbidity',
    unit: 'NTU',
    metricUnit: 'NTU',
    icon: 'weather-fog',
    iconFamily: 'MaterialCommunityIcons',
    idealRange: { min: 0, max: 10 },
    description: 'Cloudiness or haziness of water caused by suspended particles.',
    category: 'physical',
  },
  ph: {
    label: 'pH',
    shortLabel: 'pH',
    unit: '',
    metricUnit: '',
    icon: 'flask',
    iconFamily: 'MaterialCommunityIcons',
    idealRange: { min: 6.5, max: 8.5 },
    description: 'Measure of water acidity or alkalinity.',
    category: 'chemical',
  },
  salinity: {
    label: 'Salinity',
    shortLabel: 'Salinity',
    unit: 'ppt',
    metricUnit: 'psu',
    icon: 'shaker-outline',
    iconFamily: 'MaterialCommunityIcons',
    idealRange: { min: 0, max: 35 },
    description: 'Salt concentration in water. Varies with tidal influence and river flow.',
    category: 'physical',
  },
  flow: {
    label: 'River Flow',
    shortLabel: 'Flow',
    unit: 'ft³/s',
    metricUnit: 'm³/s',
    icon: 'waves',
    iconFamily: 'MaterialCommunityIcons',
    idealRange: { min: 1000, max: 5000 },
    description: 'Rate of water discharge at the monitoring location.',
    category: 'physical',
  },
  depth: {
    label: 'Water Depth',
    shortLabel: 'Depth',
    unit: 'ft',
    metricUnit: 'm',
    icon: 'arrow-expand-vertical',
    iconFamily: 'MaterialCommunityIcons',
    idealRange: null,
    description: 'Water depth at the monitoring station.',
    category: 'physical',
  },
};

// =============================================================================
// FISHING OPTIMAL CONDITIONS
// =============================================================================

export const FISHING_IDEAL_TEMPS = {
  min: 55,
  max: 75,
  unit: '°F',
};

export const FISHING_IDEAL_FLOW = {
  min: 1000,
  max: 5000,
  unit: 'ft³/s',
};

// Optimal fishing times (hours before/after sunrise/sunset)
export const FISHING_MAJOR_PERIOD_HOURS = 2;
export const FISHING_MINOR_PERIOD_HOURS = 1;

// =============================================================================
// SWIMMING SAFETY THRESHOLDS
// =============================================================================

export const SWIMMING_THRESHOLDS = {
  excellent: { wqi: 90, label: 'Excellent', color: '#00BCD4' },
  good: { wqi: 70, label: 'Good', color: '#4CAF50' },
  moderate: { wqi: 50, label: 'Moderate', color: '#FF9800' },
  poor: { wqi: 0, label: 'Poor', color: '#F44336' },
};

// =============================================================================
// TURBIDITY CLARITY SCALE
// =============================================================================

export const TURBIDITY_SCALE = [
  { max: 1, label: 'Crystal Clear', color: '#00BCD4', clarity: 'Excellent' },
  { max: 5, label: 'Very Clear', color: '#4CAF50', clarity: 'Very Good' },
  { max: 10, label: 'Clear', color: '#8BC34A', clarity: 'Good' },
  { max: 25, label: 'Slightly Cloudy', color: '#FF9800', clarity: 'Fair' },
  { max: 50, label: 'Cloudy', color: '#FF5722', clarity: 'Poor' },
  { max: Infinity, label: 'Very Cloudy', color: '#F44336', clarity: 'Very Poor' },
];

// =============================================================================
// MOON PHASES
// =============================================================================

export const MOON_PHASES = [
  { name: 'New Moon', illumination: 0, icon: 'moon-new' },
  { name: 'Waxing Crescent', illumination: 0.25, icon: 'moon-waxing-crescent' },
  { name: 'First Quarter', illumination: 0.5, icon: 'moon-first-quarter' },
  { name: 'Waxing Gibbous', illumination: 0.75, icon: 'moon-waxing-gibbous' },
  { name: 'Full Moon', illumination: 1, icon: 'moon-full' },
  { name: 'Waning Gibbous', illumination: 0.75, icon: 'moon-waning-gibbous' },
  { name: 'Last Quarter', illumination: 0.5, icon: 'moon-last-quarter' },
  { name: 'Waning Crescent', illumination: 0.25, icon: 'moon-waning-crescent' },
];

// =============================================================================
// WIND DIRECTION LABELS
// =============================================================================

export const WIND_DIRECTIONS = [
  'N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
  'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW',
];

// =============================================================================
// NOTIFICATION CONFIG
// =============================================================================

export const NOTIFICATION_CHANNELS = {
  waterQualityAlerts: {
    id: 'water-quality-alerts',
    name: 'Water Quality Alerts',
    description: 'Alerts for significant changes in water quality',
    importance: 'high',
  },
  fishingUpdates: {
    id: 'fishing-updates',
    name: 'Fishing Updates',
    description: 'Daily fishing condition summaries',
    importance: 'default',
  },
  general: {
    id: 'general',
    name: 'General',
    description: 'General app notifications',
    importance: 'default',
  },
};

// =============================================================================
// CACHE CONFIGURATION
// =============================================================================

export const CACHE_KEYS = {
  stationReadings: (stationId) => `@readings_${stationId}`,
  lastRefresh: '@last_refresh_time',
  themePreference: '@hrecos_theme_preference',
  favoriteStations: '@favorite_stations',
  userSettings: '@user_settings',
};

export const CACHE_TTL = {
  readings: 5 * 60 * 1000, // 5 minutes
  stationList: 24 * 60 * 60 * 1000, // 24 hours
  userSettings: Infinity,
};
