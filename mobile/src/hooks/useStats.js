import { useState, useEffect, useCallback } from 'react';
import { getStats } from '../api/hrecosApi';
import { normalizeStats } from '../utils/apiNormalize';

export const useStats = (stationId, parameters = [], hours = 24) => {
  const [data, setData] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchStats = useCallback(async () => {
    if (!stationId || parameters.length === 0) {
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const payload = await getStats(stationId, hours);
      setData(normalizeStats(payload, parameters));
    } catch (err) {
      console.warn('Stats API failed:', err.message);
      setError(err.message || 'Failed to load statistics');
      setData({});
    } finally {
      setLoading(false);
    }
  }, [stationId, parameters, hours]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  return { data, loading, error, refetch: fetchStats };
};