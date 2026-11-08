// HRECOS RiverWatch - Constants & Parameter Metadata
// Station list: data/stations.json (linked from mobile/src/data/stations.json)

import registry from '../data/stations.json';

// Fishing ideal ranges (used by calculations.js)
export const FISHING_IDEAL_TEMPS = { min: 55, max: 75 };
export const FISHING_IDEAL_FLOW = { min: 100, max: 5000 };

// Parameter metadata for display
export const PARAM_INFO = {
  temp: {
    key: 'temp',
    label: 'Water Temp',
    unit: '°F',
    icon: 'thermometer',
    chartColor: '#E74C3C',
    description: 'Water temperature in degrees Fahrenheit',
    thresholds: { good: [32, 80], caution: [80, 88], concern: 88 },
  },
  turbidity: {
    key: 'turbidity',
    label: 'Turbidity',
    unit: 'NTU',
    icon: 'water-opacity',
    chartColor: '#8E44AD',
    description: 'Water clarity measurement',
    thresholds: { good: [0, 10], caution: [10, 50], concern: 50 },
  },
  do: {
    key: 'do',
    label: 'Dissolved O₂',
    unit: 'mg/L',
    icon: 'molecule-co2',
    chartColor: '#3498DB',
    description: 'Dissolved oxygen concentration',
    thresholds: { good: [6, 15], caution: [4, 6], concern: 4 },
  },
  ph: {
    key: 'ph',
    label: 'pH Level',
    unit: '',
    icon: 'flask',
    chartColor: '#2ECC71',
    description: 'Acidity/basicity of water',
    thresholds: { good: [6.5, 8.5], caution: [6, 6.5], concern_low: 6, concern_high: 8.5 },
  },
  conductivity: {
    key: 'conductivity',
    label: 'Conductivity',
    unit: 'μS/cm',
    icon: 'lightning-bolt',
    chartColor: '#F39C12',
    description: 'Specific conductance. Brackish at Tappan Zee, fresh at Poughkeepsie.',
    thresholds: { good: [50, 25000], caution: [25000, 40000], concern: 40000 },
  },
  salinity: {
    key: 'salinity',
    label: 'Salinity',
    unit: 'ppt',
    icon: 'shaker-outline',
    chartColor: '#1ABC9C',
    description: 'Salt concentration. The focus reach is tidal and brackish at Tappan Zee.',
    thresholds: { good: [0, 15], caution: [15, 25], concern: 30 },
  },
  depth: {
    key: 'depth',
    label: 'Depth',
    unit: 'ft',
    icon: 'arrow-collapse-down',
    chartColor: '#34495E',
    description: 'Sensor depth. The API converts HRECOS meters to feet.',
    thresholds: { good: [0, 30], caution: [30, 60], concern: 60 },
  },
  speed: {
    key: 'speed',
    label: 'Flow Speed',
    unit: 'm/s',
    icon: 'waves',
    chartColor: '#E67E22',
    description: 'Current flow speed',
    thresholds: { good: [0, 2], caution: [2, 4], concern: 4 },
  },
  direction: {
    key: 'direction',
    label: 'Direction',
    unit: '°',
    icon: 'compass',
    chartColor: '#9B59B6',
    description: 'Flow direction in degrees',
    thresholds: {},
  },
  wind_speed: {
    key: 'wind_speed',
    label: 'Wind Speed',
    unit: 'mph',
    icon: 'weather-windy',
    chartColor: '#00BCD4',
    description: 'Wind speed at station',
    thresholds: { good: [0, 20], caution: [20, 40], concern: 40 },
  },
  wind_dir: {
    key: 'wind_dir',
    label: 'Wind Dir',
    unit: '°',
    icon: 'compass-outline',
    chartColor: '#607D8B',
    description: 'Wind direction',
    thresholds: {},
  },
  do_sat: {
    key: 'do_sat',
    label: 'DO Saturation',
    unit: '%',
    icon: 'molecule-co2',
    chartColor: '#5DADE2',
    description: 'Dissolved oxygen as percent saturation. Piermont publishes this and not mg/L.',
    thresholds: { good: [70, 130], caution: [50, 70], concern: 140 },
  },
  chlorophyll: {
    key: 'chlorophyll',
    label: 'Chlorophyll',
    unit: 'RFU',
    icon: 'leaf',
    chartColor: '#27AE60',
    description: 'Chlorophyll fluorescence from the HRECOS sonde',
    thresholds: {},
  },
  phycocyanin: {
    key: 'phycocyanin',
    label: 'Phycocyanin',
    unit: 'RFU',
    icon: 'leaf-circle-outline',
    chartColor: '#16A085',
    description: 'Phycocyanin fluorescence from the HRECOS sonde',
    thresholds: {},
  },
  air_temp: {
    key: 'air_temp',
    label: 'Air Temp',
    unit: '°F',
    icon: 'thermometer-lines',
    chartColor: '#FF5722',
    description: 'Air temperature',
    thresholds: { good: [10, 90], caution: [90, 100], concern: 100 },
  },
  humidity: {
    key: 'humidity',
    label: 'Humidity',
    unit: '%',
    icon: 'water-percent',
    chartColor: '#03A9F4',
    description: 'Relative humidity',
    thresholds: { good: [0, 100], caution: [], concern: -1 },
  },
  pressure: {
    key: 'pressure',
    label: 'Pressure',
    unit: 'inHg',
    icon: 'gauge',
    chartColor: '#795548',
    description: 'Barometric pressure',
    thresholds: { good: [29.2, 30.7], caution: [28.5, 29.2], concern: 28.5 },
  },
  tide: {
    key: 'tide',
    label: 'Tide Height',
    unit: 'ft',
    icon: 'waves-arrow-up',
    chartColor: '#1A6BAA',
    description: 'Predicted tide height in feet (NOAA MLLW)',
    thresholds: {},
  },
};

const PROVIDER_LABEL = { usgs: 'USGS', noaa: 'NOAA', ndbc: 'NDBC', hrecos: 'HRECOS' };
const APP_PARAM = {
  temp: 'temp',
  dissolved_oxygen: 'do',
  dissolved_oxygen_saturation: 'do_sat',
  conductance: 'conductivity',
  chlorophyll: 'chlorophyll',
  phycocyanin: 'phycocyanin',
  turbidity: 'turbidity',
  ph: 'ph',
  salinity: 'salinity',
  depth: 'depth',
  air_temp: 'air_temp',
  wind_speed: 'wind_speed',
  wind_direction: 'wind_dir',
  pressure: 'pressure',
  tide_prediction: 'tide',
  water_level: 'tide',
};

export const STATIONS = registry.stations.map((station) => ({
  id: station.key,
  name: station.name,
  mile: station.river_mile,
  lat: station.lat,
  lon: station.lon,
  source: PROVIDER_LABEL[station.provider] || station.provider,
  sourceLabel: PROVIDER_LABEL[station.provider] || station.provider,
  sourceId: station.id,
  status: station.live ? 'live' : 'offline',
  focus: !!station.focus,
  kind: station.kind,
  parameters: [...new Set((station.parameters || []).map((param) => APP_PARAM[param.field]).filter(Boolean))],
  description: station.note || '',
}));

export const STATIONS_BY_ID = STATIONS.reduce((acc, station) => {
  acc[station.id] = station;
  return acc;
}, {});

// Status badge config
export const STATUS_CONFIG = {
  live: { label: 'Live', color: '#28A745', bgColor: '#28A74520' },
  offline: { label: 'Offline', color: '#DC3545', bgColor: '#DC354520' },
  intermittent: { label: 'Intermittent', color: '#F0A030', bgColor: '#F0A03020' },
};

// Tide phases
export const TIDE_PHASES = {
  rising: { label: 'Rising', icon: 'arrow-up-bold', color: '#E74C3C' },
  falling: { label: 'Falling', icon: 'arrow-down-bold', color: '#3498DB' },
  high: { label: 'High Tide', icon: 'arrow-collapse-up', color: '#28A745' },
  low: { label: 'Low Tide', icon: 'arrow-collapse-down', color: '#8E44AD' },
  slack: { label: 'Slack', icon: 'minus', color: '#8A96A5' },
};

// WQI (Water Quality Index) thresholds
export const WQI_LEVELS = [
  { max: 25, label: 'Excellent', color: '#28A745', description: 'Water quality is excellent.' },
  { max: 50, label: 'Good', color: '#8BC34A', description: 'Water quality is good.' },
  { max: 75, label: 'Moderate', color: '#FFC107', description: 'Water quality is moderate - some parameters show slight concern.' },
  { max: 100, label: 'Poor', color: '#FF9800', description: 'Water quality is poor - several parameters exceed guidelines.' },
  { max: 999, label: 'Bad', color: '#DC3545', description: 'Water quality is very poor - immediate attention needed.' },
];

export const getWQILevel = (wqi) => {
  return WQI_LEVELS.find(l => wqi <= l.max) || WQI_LEVELS[WQI_LEVELS.length - 1];
};

// Tide chart location — Cornwall-on-Hudson at West Point
export const TIDE_LOCATION = {
  place: 'Cornwall-on-Hudson, NY',
  landmark: 'West Point',
  stationName: 'Newburgh',
  stationId: '8518935',
  distance: 'Subordinate tide station ~3 mi south of Cornwall-on-Hudson',
  apiEndpoint: '/api/tides',
  dataProvider: 'NOAA CO-OPS',
};

// Auto-refresh interval
export const REFRESH_INTERVAL = 5 * 60 * 1000; // 5 minutes

// Chart time ranges
export const TIME_RANGES = [
  { label: '6H', hours: 6 },
  { label: '24H', hours: 24 },
  { label: '7D', hours: 168 },
];

// Source badge colors
export const SOURCE_COLORS = {
  USGS: '#1A6BAA',
  NOAA: '#28A745',
  NDBC: '#E67E22',
  HRECOS: '#9B59B6',
};
