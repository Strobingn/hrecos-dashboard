import { useState, useEffect, useCallback } from 'react';
import { getTides } from '../api/hrecosApi';
import { TIDE_LOCATION } from '../constants';

function inferPhase(current) {
  const type = (current?.current_type || '').toLowerCase();
  if (type === 'high' || type === 'h') return 'high';
  if (type === 'low' || type === 'l') return 'low';
  if (current?.next_type) {
    const next = current.next_type.toLowerCase();
    if (next === 'high' || next === 'h') return 'rising';
    if (next === 'low' || next === 'l') return 'falling';
  }
  return 'rising';
}

function normalizeTideResponse(payload) {
  const current = payload?.current || {};
  const predictions = (payload?.predictions || []).map((p) => ({
    timestamp: p.time,
    time: p.time,
    height: p.height,
    type: p.type,
  }));

  return {
    location: TIDE_LOCATION,
    stationId: payload?.station || TIDE_LOCATION.stationId,
    stationName: payload?.station_name || TIDE_LOCATION.stationName,
    current: {
      height: current.current_height ?? current.height ?? null,
      phase: inferPhase(current),
      type: current.current_type,
      timestamp: new Date().toISOString(),
      nextTime: current.next_time,
      nextType: current.next_type,
      nextHeight: current.next_height,
    },
    predictions,
  };
}

const generateTideData = () => {
  const now = Date.now();
  const cycleMs = 12.42 * 60 * 60 * 1000;
  const progress = (now % cycleMs) / cycleMs;
  const height = 1.0 + 0.9 * Math.sin(progress * Math.PI * 2 - Math.PI / 2);

  let phase;
  if (progress > 0.45 && progress < 0.55) phase = 'high';
  else if (progress > 0.95 || progress < 0.05) phase = 'low';
  else if (progress > 0.05 && progress < 0.45) phase = 'rising';
  else phase = 'falling';

  const predictions = [];
  for (let i = -12; i <= 24; i += 0.5) {
    const t = now + i * 60 * 60 * 1000;
    const p = ((t % cycleMs) + cycleMs) % cycleMs / cycleMs;
    const h = 1.0 + 0.9 * Math.sin(p * Math.PI * 2 - Math.PI / 2);
    predictions.push({
      timestamp: new Date(t).toISOString(),
      time: new Date(t).toISOString(),
      height: parseFloat(h.toFixed(2)),
    });
  }

  return {
    location: TIDE_LOCATION,
    stationId: TIDE_LOCATION.stationId,
    stationName: TIDE_LOCATION.stationName,
    source: 'simulated',
    current: {
      height: parseFloat(height.toFixed(2)),
      phase,
      timestamp: new Date().toISOString(),
    },
    predictions,
  };
};

export const useTides = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      try {
        const payload = await getTides(48);
        setData({ ...normalizeTideResponse(payload), source: 'api' });
      } catch (apiErr) {
        console.warn('Tide API unavailable, using simulated data:', apiErr.message);
        setData(generateTideData());
        setError(null);
      }
    } catch (err) {
      setError(err.message || 'Failed to load tide data');
      setData(generateTideData());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15 * 60 * 1000);
    return () => clearInterval(interval);
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
};