import { useQuery } from '@tanstack/react-query';
import { STATIONS_BY_ID } from '../constants';
import { normalizeWeather } from '../utils/weather';

// Coordinates come from the shared station registry, centered on West Point.
const station = STATIONS_BY_ID.west_point;

async function fetchWeather({ signal }) {
  const variables = 'temperature_2m,weather_code,wind_speed_10m,wind_gusts_10m';
  const url = 'https://api.open-meteo.com/v1/forecast'
    + `?latitude=${station.lat}&longitude=${station.lon}`
    + `&current=${variables}&hourly=${variables},rain,precipitation_probability`
    + '&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=mm'
    + '&timeformat=unixtime&timezone=GMT&forecast_days=2';
  const controller = new AbortController();
  const abort = () => controller.abort();
  signal?.addEventListener('abort', abort);
  const timeout = setTimeout(abort, 15000);
  try {
    if (signal?.aborted) controller.abort();
    const response = await fetch(url, { signal: controller.signal });
    if (!response.ok) throw new Error('Weather is unavailable. Pull to try again.');
    return normalizeWeather(await response.json());
  } finally {
    clearTimeout(timeout);
    signal?.removeEventListener('abort', abort);
  }
}

export function useWeather() {
  return useQuery({ queryKey: ['weather', station.id], queryFn: fetchWeather, staleTime: 5 * 60000, refetchInterval: 5 * 60000, retry: 1 });
}
