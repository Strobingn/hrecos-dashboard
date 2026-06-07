// ============================================================================
// HRECOS RiverWatch - Data Formatters
// Value formatting, date/time display, and trend indicators
// ============================================================================

import { PARAM_INFO } from './constants';

// =============================================================================
// TEMPERATURE CONVERSION
// =============================================================================

const C_TO_F = 9 / 5;
const F_TO_C = 5 / 9;

/**
 * Convert Celsius to Fahrenheit.
 * @param {number} celsius
 * @returns {number}
 */
function celsiusToFahrenheit(celsius) {
  return celsius * C_TO_F + 32;
}

/**
 * Convert Fahrenheit to Celsius.
 * @param {number} fahrenheit
 * @returns {number}
 */
function fahrenheitToCelsius(fahrenheit) {
  return (fahrenheit - 32) * F_TO_C;
}

// =============================================================================
// VALUE FORMATTING
// =============================================================================

/**
 * Format a sensor value based on its parameter type with appropriate units.
 *
 * @param {number|null|undefined} value - Raw sensor value
 * @param {string} param - Parameter key (e.g., 'temp', 'dissolved_oxygen')
 * @param {Object} options - Formatting options
 * @param {boolean} options.useMetric - Use metric units
 * @param {number} options.decimals - Number of decimal places
 * @returns {string} Formatted value with units
 */
export function formatValue(value, param, options = {}) {
  const { useMetric = false, decimals = null } = options;

  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return '--';
  }

  const numValue = Number(value);
  const info = PARAM_INFO[param];

  if (!info) {
    // Fallback for unknown parameters
    return `${numValue.toFixed(1)}`;
  }

  let displayValue = numValue;
  let unit = useMetric && info.metricUnit ? info.metricUnit : info.unit;

  // Apply unit conversions
  if (param === 'temp' || param === 'air_temp' || param === 'dewpoint') {
    displayValue = useMetric ? numValue : celsiusToFahrenheit(numValue);
  } else if (param === 'wind_speed') {
    displayValue = useMetric ? numValue * 0.44704 : numValue;
  } else if (param === 'pressure') {
    displayValue = useMetric ? numValue * 33.8639 : numValue;
  } else if (param === 'flow') {
    displayValue = useMetric ? numValue * 0.0283168 : numValue;
  }

  // Determine decimal places
  let places;
  if (decimals !== null) {
    places = decimals;
  } else {
    switch (param) {
      case 'temp':
      case 'air_temp':
      case 'dewpoint':
        places = 1;
        break;
      case 'wind_speed':
        places = 1;
        break;
      case 'wind_direction':
        places = 0;
        break;
      case 'pressure':
        places = useMetric ? 1 : 2;
        break;
      case 'dissolved_oxygen':
        places = 1;
        break;
      case 'turbidity':
        places = 1;
        break;
      case 'ph':
        places = 2;
        break;
      case 'salinity':
        places = 1;
        break;
      case 'conductance':
        places = 0;
        break;
      default:
        places = 1;
    }
  }

  const formatted = displayValue.toFixed(places);

  // Remove trailing zeros after decimal
  const cleaned = formatted.includes('.') ? formatted.replace(/\.?0+$/, '') : formatted;

  return unit ? `${cleaned} ${unit}` : cleaned;
}

/**
 * Format temperature with °F or °C.
 *
 * @param {number|null} value - Temperature value (assumed stored as °F unless from API)
 * @param {boolean} useMetric - Display in Celsius
 * @returns {string} Formatted temperature
 */
export function formatTemp(value, useMetric = false) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return '--';
  }

  const numValue = Number(value);
  const displayValue = useMetric ? fahrenheitToCelsius(numValue) : numValue;
  const unit = useMetric ? '°C' : '°F';

  return `${displayValue.toFixed(1)}${unit}`;
}

/**
 * Format river flow with ft³/s or m³/s.
 *
 * @param {number|null} value - Flow value in ft³/s
 * @param {boolean} useMetric - Display in m³/s
 * @returns {string} Formatted flow
 */
export function formatFlow(value, useMetric = false) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return '--';
  }

  const numValue = Number(value);
  const displayValue = useMetric ? numValue * 0.0283168 : numValue;
  const unit = useMetric ? 'm³/s' : 'ft³/s';

  if (displayValue >= 1000) {
    return `${(displayValue / 1000).toFixed(1)}K ${unit}`;
  }

  return `${Math.round(displayValue).toLocaleString()} ${unit}`;
}

/**
 * Format turbidity with NTU and descriptive label.
 *
 * @param {number|null} value - Turbidity in NTU
 * @returns {string} Formatted turbidity with description
 */
export function formatTurbidity(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return '--';
  }

  const ntu = Number(value);
  let description = '';

  if (ntu <= 1) {
    description = 'Crystal Clear';
  } else if (ntu <= 5) {
    description = 'Very Clear';
  } else if (ntu <= 10) {
    description = 'Clear';
  } else if (ntu <= 25) {
    description = 'Slightly Cloudy';
  } else if (ntu <= 50) {
    description = 'Cloudy';
  } else {
    description = 'Very Cloudy';
  }

  return `${ntu.toFixed(1)} NTU - ${description}`;
}

// =============================================================================
// DATE & TIME FORMATTING
// =============================================================================

/**
 * Parse a date string into a Date object.
 * Handles ISO strings, API formats, and timestamps.
 *
 * @param {string|number|Date} dateStr
 * @returns {Date|null}
 */
function parseDate(dateStr) {
  if (!dateStr) return null;
  if (dateStr instanceof Date) return isNaN(dateStr.getTime()) ? null : dateStr;

  const d = new Date(dateStr);
  return isNaN(d.getTime()) ? null : d;
}

/**
 * Format a date string to a human-readable date.
 *
 * @param {string|Date} dateStr
 * @returns {string}
 */
export function formatDate(dateStr) {
  const date = parseDate(dateStr);
  if (!date) return '--';

  const now = new Date();
  const isToday = date.toDateString() === now.toDateString();
  const isYesterday = new Date(now.getTime() - 86400000).toDateString() === date.toDateString();

  if (isToday) return 'Today';
  if (isYesterday) return 'Yesterday';

  const months = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
  ];

  const month = months[date.getMonth()];
  const day = date.getDate();
  const year = date.getFullYear();

  if (year === now.getFullYear()) {
    return `${month} ${day}`;
  }

  return `${month} ${day}, ${year}`;
}

/**
 * Format a date string to a human-readable time.
 *
 * @param {string|Date} dateStr
 * @param {boolean} use24Hour - Use 24-hour format
 * @returns {string}
 */
export function formatTime(dateStr, use24Hour = false) {
  const date = parseDate(dateStr);
  if (!date) return '--';

  const hours = date.getHours();
  const minutes = date.getMinutes().toString().padStart(2, '0');

  if (use24Hour) {
    return `${hours.toString().padStart(2, '0')}:${minutes}`;
  }

  const period = hours >= 12 ? 'PM' : 'AM';
  const displayHours = hours === 0 ? 12 : hours > 12 ? hours - 12 : hours;

  return `${displayHours}:${minutes} ${period}`;
}

/**
 * Format a date as relative time (e.g., "5 min ago").
 *
 * @param {string|Date} dateStr
 * @returns {string}
 */
export function formatRelativeTime(dateStr) {
  const date = parseDate(dateStr);
  if (!date) return '--';

  const now = new Date();
  const diffMs = now.getTime() - date.getTime();

  if (diffMs < 0) {
    // Future time
    const absDiff = Math.abs(diffMs);
    if (absDiff < 60000) return 'in moments';
    if (absDiff < 3600000) return `in ${Math.ceil(absDiff / 60000)} min`;
    if (absDiff < 86400000) return `in ${Math.ceil(absDiff / 3600000)} hr`;
    return `in ${Math.ceil(absDiff / 86400000)} days`;
  }

  const seconds = Math.floor(diffMs / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (seconds < 10) return 'just now';
  if (seconds < 60) return `${seconds} sec ago`;
  if (minutes < 60) return `${minutes} min ago`;
  if (hours < 24) return `${hours} hr ago`;
  if (days < 7) return `${days} day${days > 1 ? 's' : ''} ago`;
  if (days < 30) return `${Math.floor(days / 7)} wk ago`;

  return formatDate(dateStr);
}

/**
 * Format a full datetime string.
 *
 * @param {string|Date} dateStr
 * @returns {string}
 */
export function formatDateTime(dateStr) {
  const date = parseDate(dateStr);
  if (!date) return '--';

  return `${formatDate(dateStr)} at ${formatTime(dateStr)}`;
}

// =============================================================================
// TREND INDICATORS
// =============================================================================

/**
 * Get a trend arrow with color based on current vs previous value.
 *
 * @param {number|null} current - Current value
 * @param {number|null} previous - Previous value
 * @param {Object} options
 * @param {boolean} options.lowerIsBetter - Whether a decrease is positive (e.g., turbidity)
 * @param {number} options.threshold - Minimum change to register as a trend (default: 0)
 * @returns {{ arrow: string, color: string, direction: string, change: string }}
 */
export function getTrendArrow(current, previous, options = {}) {
  const { lowerIsBetter = false, threshold = 0 } = options;

  if (
    current === null ||
    current === undefined ||
    previous === null ||
    previous === undefined ||
    Number.isNaN(Number(current)) ||
    Number.isNaN(Number(previous))
  ) {
    return { arrow: '→', color: '#9E9E9E', direction: 'stable', change: '--' };
  }

  const diff = Number(current) - Number(previous);
  const absDiff = Math.abs(diff);

  if (absDiff <= threshold) {
    return { arrow: '→', color: '#9E9E9E', direction: 'stable', change: '0' };
  }

  const isIncreasing = diff > 0;

  // For parameters where lower is better (turbidity, pollutants)
  // an increase is bad (red), decrease is good (green)
  let color;
  if (lowerIsBetter) {
    color = isIncreasing ? '#E53935' : '#43A047';
  } else {
    // Default: increase is neutral/positive for things like temp, DO
    color = isIncreasing ? '#43A047' : '#E53935';
  }

  const arrow = isIncreasing ? '↑' : '↓';
  const direction = isIncreasing ? 'rising' : 'falling';
  const change = absDiff < 1 ? absDiff.toFixed(2) : absDiff.toFixed(1);

  return { arrow, color, direction, change: `${isIncreasing ? '+' : '-'}${change}` };
}

// =============================================================================
// WIND DIRECTION FORMATTING
// =============================================================================

/**
 * Convert wind direction degrees to compass label.
 *
 * @param {number|null} degrees - Wind direction in degrees (0-360)
 * @returns {string}
 */
export function formatWindDirection(degrees) {
  if (degrees === null || degrees === undefined || Number.isNaN(Number(degrees))) {
    return '--';
  }

  const dirs = [
    'N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
    'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW',
  ];
  const idx = Math.round((Number(degrees) % 360) / 22.5) % 16;
  return dirs[idx];
}

// =============================================================================
// CONDUCTANCE / SALINITY FORMATTING
// =============================================================================

/**
 * Format specific conductance with appropriate scaling.
 *
 * @param {number|null} value - Conductance in μS/cm
 * @returns {string}
 */
export function formatConductance(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return '--';
  }

  const val = Number(value);

  if (val >= 1000) {
    return `${(val / 1000).toFixed(2)} mS/cm`;
  }

  return `${Math.round(val)} μS/cm`;
}

/**
 * Estimate salinity from conductance using a simplified conversion.
 * Reference: Practical Salinity Scale approximation.
 *
 * @param {number|null} conductance - Specific conductance in μS/cm at 25°C
 * @returns {string} Estimated salinity in ppt
 */
export function estimateSalinity(conductance) {
  if (conductance === null || conductance === undefined || Number.isNaN(Number(conductance))) {
    return '--';
  }

  // Simplified: salinity (ppt) ≈ conductance (μS/cm) / 2100 for 0-40 ppt range
  // This is a rough approximation for freshwater-to-brackish conditions
  const salinity = Number(conductance) / 2100;

  if (salinity < 0.5) {
    return `${salinity.toFixed(2)} ppt (Fresh)`;
  } else if (salinity < 5) {
    return `${salinity.toFixed(2)} ppt (Slightly Brackish)`;
  } else if (salinity < 18) {
    return `${salinity.toFixed(1)} ppt (Brackish)`;
  } else {
    return `${salinity.toFixed(1)} ppt (Saline)`;
  }
}
