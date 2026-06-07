import { PARAM_INFO, STATIONS, STATIONS_BY_ID, getWQILevel } from '../constants';

const PARAM_KEY_MAP = {
  temp: 'temp',
  dissolved_oxygen: 'do',
  conductance: 'conductivity',
  conductivity: 'conductivity',
  turbidity: 'turbidity',
  ph: 'ph',
  salinity: 'salinity',
  air_temp: 'air_temp',
  wind_speed: 'wind_speed',
  wind_direction: 'wind_dir',
  dewpoint: 'air_temp',
  pressure: 'pressure',
  flow: 'speed',
};

const SOURCE_FROM_KEY = {
  norrie_point: 'NDBC',
  turkey_point: 'NOAA',
  west_point: 'USGS',
  newburgh: 'NOAA',
  beacon: 'NOAA',
  bear_mountain: 'NDBC',
  coxsackie: 'NOAA',
  schodack: 'USGS',
  albany: 'USGS',
};

function mapParamList(params = []) {
  return params
    .map((p) => {
      if (p === 'dissolved_oxygen') return 'do';
      if (p === 'conductance') return 'conductivity';
      if (p === 'wind_direction') return 'wind_dir';
      if (p === 'tide') return null;
      return p;
    })
    .filter(Boolean);
}

export function normalizeStationMeta(apiStation) {
  const key = apiStation.key || apiStation.id;
  const local = STATIONS_BY_ID[key] || {};
  const parameters = mapParamList(apiStation.parameters || apiStation.params || local.parameters || []);

  return {
    id: key,
    name: apiStation.name || local.name || key,
    mile: local.mile ?? apiStation.river_mile ?? null,
    lat: apiStation.location?.lat ?? apiStation.lat ?? local.lat,
    lon: apiStation.location?.lon ?? apiStation.lon ?? local.lon,
    source: SOURCE_FROM_KEY[key] || local.source || 'HRECOS',
    sourceLabel: SOURCE_FROM_KEY[key] || local.sourceLabel || 'HRECOS',
    status: apiStation.live ? 'live' : (local.status || 'offline'),
    parameters,
    description: apiStation.note || local.description || '',
  };
}

export function buildReadings(raw = {}, parameters = []) {
  const ts = raw.timestamp
    ? (typeof raw.timestamp === 'string' ? raw.timestamp : new Date(raw.timestamp).toISOString())
    : new Date().toISOString();

  const readings = {};
  const paramList = parameters.length ? parameters : Object.keys(PARAM_KEY_MAP);

  paramList.forEach((param) => {
    const info = PARAM_INFO[param];
    if (!info) return;

    let value = null;
    if (param === 'temp') value = raw.temp ?? raw.air_temp ?? null;
    else if (param === 'air_temp') value = raw.air_temp ?? null;
    else if (param === 'do') value = raw.dissolved_oxygen ?? raw.do ?? null;
    else if (param === 'conductivity') value = raw.conductance ?? raw.conductivity ?? null;
    else if (param === 'wind_dir') value = raw.wind_direction ?? raw.wind_dir ?? null;
    else if (param === 'speed') value = raw.flow ?? raw.speed ?? null;
    else value = raw[param] ?? null;

    if (value == null) return;

    readings[param] = {
      value: typeof value === 'number' ? value : parseFloat(value),
      unit: info.unit,
      label: info.label,
      timestamp: ts,
      trend: 'stable',
    };
  });

  return readings;
}

export function mergeStationWithReading(stationMeta, rawReading) {
  const readings = buildReadings(rawReading, stationMeta.parameters);
  return { ...stationMeta, readings, source: rawReading ? 'api' : 'offline' };
}

export function normalizeStationsList(apiPayload, latestReadings = {}) {
  const list = apiPayload?.stations || apiPayload || [];
  return list.map((s) => {
    const meta = normalizeStationMeta(s);
    const key = meta.id;
    return mergeStationWithReading(meta, latestReadings[key]);
  });
}

export function normalizeDashboard(apiPayload, stations = []) {
  const latest = apiPayload?.latest_readings || {};
  const live = stations.filter((s) => s.status === 'live');
  const temps = Object.values(latest)
    .map((r) => r?.temp ?? r?.air_temp)
    .filter((v) => v != null);

  const avgWaterTemp = temps.length
    ? (temps.reduce((a, b) => a + b, 0) / temps.length).toFixed(1)
    : '--';

  const turbidityVals = Object.values(latest).map((r) => r?.turbidity).filter((v) => v != null);
  const doVals = Object.values(latest).map((r) => r?.dissolved_oxygen).filter((v) => v != null);
  const wqi = computeSimpleWQI(turbidityVals, doVals, temps);
  const wqiLevel = getWQILevel(wqi);

  return {
    stationsOnline: Object.keys(latest).length || live.length,
    totalStations: stations.length || apiPayload?.stations_online || live.length,
    avgWaterTemp,
    waterQualityIndex: wqi,
    waterQualityLevel: wqiLevel,
    lastUpdated: apiPayload?.timestamp || new Date().toISOString(),
    source: 'api',
  };
}

function computeSimpleWQI(turbidityVals, doVals, tempVals) {
  let score = 55;
  if (doVals.length) {
    const avgDo = doVals.reduce((a, b) => a + b, 0) / doVals.length;
    score += avgDo >= 7 ? 15 : avgDo >= 5 ? 5 : -10;
  }
  if (turbidityVals.length) {
    const avgTurb = turbidityVals.reduce((a, b) => a + b, 0) / turbidityVals.length;
    score += avgTurb <= 10 ? 10 : avgTurb <= 25 ? 0 : -15;
  }
  if (tempVals.length) {
    const avgTemp = tempVals.reduce((a, b) => a + b, 0) / tempVals.length;
    score += avgTemp >= 50 && avgTemp <= 75 ? 10 : 0;
  }
  return Math.max(10, Math.min(95, Math.round(score)));
}

export function normalizeAnomalies(apiPayload) {
  const list = apiPayload?.anomalies || [];
  return list.map((a) => ({
    id: String(a.id ?? `${a.station}-${a.timestamp}`),
    type: a.type || a.anomaly_type || 'anomaly',
    severity: a.severity || 'info',
    message: a.message || `${a.type || 'Anomaly'} at ${a.station}`,
    station: a.station,
    timestamp: a.timestamp,
    value: a.value,
  }));
}

export function normalizeStats(apiPayload, parameters = []) {
  const count = apiPayload?.readings_count ?? 0;
  const out = {};

  const map = {
    temp: apiPayload?.temperature,
    speed: apiPayload?.flow,
    turbidity: apiPayload?.turbidity,
  };

  parameters.forEach((param) => {
    const block = map[param];
    if (!block) return;
    out[param] = {
      avg: block.avg ?? null,
      min: block.min ?? block.avg ?? null,
      max: block.max ?? block.avg ?? null,
      count,
    };
  });

  return out;
}

export function normalizeHistorical(apiPayload, stationId) {
  const rows = apiPayload?.data || apiPayload?.[stationId] || apiPayload || [];
  const list = Array.isArray(rows) ? rows : [];
  const out = {};

  Object.entries(PARAM_KEY_MAP).forEach(([apiKey, appKey]) => {
    const points = list
      .map((row) => {
        const value = row[apiKey] ?? (appKey === 'do' ? row.dissolved_oxygen : null) ?? (appKey === 'conductivity' ? row.conductance : null);
        if (value == null) return null;
        return {
          timestamp: typeof row.timestamp === 'string' ? row.timestamp : new Date(row.timestamp).toISOString(),
          value: parseFloat(value),
        };
      })
      .filter(Boolean);
    if (points.length) out[appKey] = points;
  });

  return out;
}