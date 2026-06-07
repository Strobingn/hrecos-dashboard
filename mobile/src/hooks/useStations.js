import { useState, useEffect, useCallback } from 'react';
import { getStations, getAllData } from '../api/hrecosApi';
import { STATIONS } from '../constants';
import { normalizeStationsList } from '../utils/apiNormalize';

export const useStations = () => {
  const [stations, setStations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchStations = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [stationPayload, latestPayload] = await Promise.all([
        getStations(),
        getAllData(),
      ]);
      const readings = latestPayload?.readings || {};
      const normalized = normalizeStationsList(stationPayload, readings);
      setStations(normalized.length ? normalized : STATIONS);
    } catch (err) {
      console.warn('Stations API failed:', err.message);
      setStations(STATIONS);
      setError(err.message || 'Failed to load stations');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStations();
    const interval = setInterval(fetchStations, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [fetchStations]);

  return { stations, loading, error, refetch: fetchStations };
};