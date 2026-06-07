import { useState, useEffect, useCallback } from 'react';
import { getLatestData } from '../api/hrecosApi';
import { STATIONS_BY_ID } from '../constants';
import { mergeStationWithReading, normalizeStationMeta } from '../utils/apiNormalize';

export const useStationData = (stationId) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    if (!stationId) return;
    try {
      setLoading(true);
      setError(null);
      const local = STATIONS_BY_ID[stationId];
      if (!local) {
        setError('Station not found');
        return;
      }
      const payload = await getLatestData(stationId);
      const raw = payload?.data || payload?.readings?.[stationId] || payload;
      const meta = normalizeStationMeta({ key: stationId, name: local.name, live: local.status === 'live', location: { lat: local.lat, lon: local.lon }, parameters: local.parameters });
      setData(mergeStationWithReading(meta, raw));
    } catch (err) {
      console.warn(`Station ${stationId} API failed:`, err.message);
      const local = STATIONS_BY_ID[stationId];
      setData(local ? { ...local, readings: {}, source: 'offline' } : null);
      setError(err.message || 'Failed to load station data');
    } finally {
      setLoading(false);
    }
  }, [stationId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
};