import { useState, useEffect, useCallback } from 'react';
import { getHistorical } from '../api/hrecosApi';
import { normalizeHistorical } from '../utils/apiNormalize';

export const useHistorical = (stationId, hours = 24) => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    if (!stationId) return;
    try {
      setLoading(true);
      setError(null);
      const payload = await getHistorical(stationId, hours);
      setData(normalizeHistorical(payload, stationId));
    } catch (err) {
      console.warn(`Historical ${stationId} API failed:`, err.message);
      setData({});
      setError(err.message || 'Failed to load historical data');
    } finally {
      setLoading(false);
    }
  }, [stationId, hours]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
};