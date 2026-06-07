import { useState, useEffect, useCallback, useRef } from 'react';
import { getDashboard, getStations } from '../api/hrecosApi';
import { STATIONS } from '../constants';
import { normalizeDashboard, normalizeStationsList } from '../utils/apiNormalize';

export const useDashboard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [dashboardPayload, stationPayload] = await Promise.all([
        getDashboard(),
        getStations(),
      ]);
      const stations = normalizeStationsList(stationPayload, dashboardPayload?.latest_readings || {});
      setData(normalizeDashboard(dashboardPayload, stations.length ? stations : STATIONS));
    } catch (err) {
      console.warn('Dashboard API failed:', err.message);
      setError(err.message || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    intervalRef.current = setInterval(fetchData, 5 * 60 * 1000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
};