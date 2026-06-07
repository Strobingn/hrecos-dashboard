import { useState, useEffect, useCallback } from 'react';
import { getAnomalies } from '../api/hrecosApi';
import { normalizeAnomalies } from '../utils/apiNormalize';

export const useAnomalies = (limit = null) => {
  const [anomalies, setAnomalies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const payload = await getAnomalies();
      const list = normalizeAnomalies(payload);
      setAnomalies(limit ? list.slice(0, limit) : list);
    } catch (err) {
      console.warn('Anomalies API failed:', err.message);
      setAnomalies([]);
      setError(null);
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { anomalies, loading, error, refetch: fetchData };
};