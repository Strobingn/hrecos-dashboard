// HRECOS RiverWatch - Constants & Parameter Metadata

// Parameter metadata for display
export const PARAM_INFO = {
  temp: {
    key: 'temp',
    label: 'Water Temp',
    unit: '°C',
    icon: 'thermometer',
    chartColor: '#E74C3C',
    description: 'Water temperature in degrees Celsius',
    thresholds: { good: [0, 30], caution: [30, 35], concern: 35 },
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
    description: 'Electrical conductivity of water',
    thresholds: { good: [50, 1500], caution: [1500, 3000], concern: 3000 },
  },
  salinity: {
    key: 'salinity',
    label: 'Salinity',
    unit: 'ppt',
    icon: 'shaker-outline',
    chartColor: '#1ABC9C',
    description: 'Salt concentration in water',
    thresholds: { good: [0, 0.5], caution: [0.5, 30], concern: 30 },
  },
  depth: {
    key: 'depth',
    label: 'Depth',
    unit: 'm',
    icon: 'arrow-collapse-down',
    chartColor: '#34495E',
    description: 'Water depth at station',
    thresholds: { good: [0, 50], caution: [50, 100], concern: 100 },
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
    unit: 'm/s',
    icon: 'weather-windy',
    chartColor: '#00BCD4',
    description: 'Wind speed at station',
    thresholds: { good: [0, 10], caution: [10, 20], concern: 20 },
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
  air_temp: {
    key: 'air_temp',
    label: 'Air Temp',
    unit: '°C',
    icon: 'thermometer-lines',
    chartColor: '#FF5722',
    description: 'Air temperature',
    thresholds: { good: [-20, 40], caution: [40, 50], concern: 50 },
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
    unit: 'hPa',
    icon: 'gauge',
    chartColor: '#795548',
    description: 'Barometric pressure',
    thresholds: { good: [980, 1040], caution: [960, 980], concern: 960 },
  },
  tide: {
    key: 'tide',
    label: 'Tide Height',
    unit: 'm',
    icon: 'waves-arrow-up',
    chartColor: '#1A6BAA',
    description: 'Tide height relative to mean sea level',
    thresholds: {},
  },
};

// Station metadata — Cornwall-on-Hudson at West Point corridor
export const STATIONS = [
  {
    id: 'newburgh',
    name: 'Newburgh',
    mile: 60,
    lat: 41.50,
    lon: -74.007,
    source: 'NOAA',
    sourceLabel: 'NOAA',
    status: 'offline',
    parameters: ['tide'],
    description: 'NOAA tide station 8518935 — ~3 mi south of Cornwall-on-Hudson.',
  },
  {
    id: 'west_point',
    name: 'West Point',
    mile: 50,
    lat: 41.386,
    lon: -73.955,
    source: 'USGS',
    sourceLabel: 'USGS',
    status: 'offline',
    parameters: ['temp', 'turbidity', 'do', 'ph', 'conductivity'],
    description: 'USMA / Cornwall-on-Hudson area — decommissioned 2014.',
  },
  {
    id: 'norrie_point',
    name: 'Norrie Point',
    mile: 88,
    lat: 41.831,
    lon: -73.942,
    source: 'NDBC',
    sourceLabel: 'NDBC',
    status: 'live',
    parameters: ['air_temp', 'wind_speed', 'wind_dir', 'pressure'],
    description: 'Nearest live met station upstream — air/wind only.',
  },
  {
    id: 'turkey_point',
    name: 'Turkey Point',
    mile: 84,
    lat: 42.014,
    lon: -73.939,
    source: 'NOAA',
    sourceLabel: 'NOAA',
    status: 'live',
    parameters: ['temp', 'conductivity'],
    description: 'Nearest live water temp upstream of West Point gap.',
  },
  {
    id: 'bear_mountain',
    name: 'Bear Mountain',
    mile: 46,
    lat: 41.314,
    lon: -73.985,
    source: 'NDBC',
    sourceLabel: 'NDBC',
    status: 'offline',
    parameters: ['air_temp', 'wind_speed', 'pressure'],
    description: 'HRNERR met station — offline.',
  },
];

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
  distance: '~3 mi south of Cornwall-on-Hudson',
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
