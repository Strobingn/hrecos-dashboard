// ============================================================================
// HRECOS RiverWatch - Environmental Calculations
// Water quality index, swimming safety, fishing scores, celestial calculations
// ============================================================================

import { FISHING_IDEAL_TEMPS, FISHING_IDEAL_FLOW } from './constants';

// =============================================================================
// WATER QUALITY INDEX (WQI)
// =============================================================================

/**
 * Calculate a composite Water Quality Index (0-100) from sensor readings.
 * Based on weighted parameter scoring against ideal ranges.
 *
 * @param {Object} readings - Object with parameter keys and numeric values
 * @param {number|null} readings.temp - Water temperature (°F)
 * @param {number|null} readings.dissolved_oxygen - DO in mg/L
 * @param {number|null} readings.turbidity - Turbidity in NTU
 * @param {number|null} readings.ph - pH value
 * @param {number|null} readings.conductance - Specific conductance in μS/cm
 * @returns {number} WQI score from 0-100
 */
export function calculateWaterQualityIndex(readings) {
  if (!readings || typeof readings !== 'object') {
    return 0;
  }

  let totalScore = 0;
  let totalWeight = 0;

  // Dissolved Oxygen (weight: 0.30) - higher is better, ideal 7-12 mg/L
  if (readings.dissolved_oxygen !== null && readings.dissolved_oxygen !== undefined) {
    const doValue = Number(readings.dissolved_oxygen);
    let doScore;
    if (doValue >= 7 && doValue <= 12) {
      doScore = 100;
    } else if (doValue >= 5) {
      doScore = 80;
    } else if (doValue >= 3) {
      doScore = 50;
    } else {
      doScore = 20;
    }
    totalScore += doScore * 0.30;
    totalWeight += 0.30;
  }

  // pH (weight: 0.20) - ideal range 6.5-8.5
  if (readings.ph !== null && readings.ph !== undefined) {
    const phValue = Number(readings.ph);
    let phScore;
    if (phValue >= 6.5 && phValue <= 8.5) {
      const distFromCenter = Math.abs(phValue - 7.5);
      phScore = 100 - distFromCenter * 15;
    } else if (phValue >= 6.0 && phValue <= 9.0) {
      phScore = 60;
    } else {
      phScore = 30;
    }
    totalScore += Math.max(0, phScore) * 0.20;
    totalWeight += 0.20;
  }

  // Turbidity (weight: 0.20) - lower is better, ideal < 5 NTU
  if (readings.turbidity !== null && readings.turbidity !== undefined) {
    const turbValue = Number(readings.turbidity);
    let turbScore;
    if (turbValue <= 1) {
      turbScore = 100;
    } else if (turbValue <= 5) {
      turbScore = 90;
    } else if (turbValue <= 10) {
      turbScore = 75;
    } else if (turbValue <= 25) {
      turbScore = 50;
    } else if (turbValue <= 50) {
      turbScore = 30;
    } else {
      turbScore = 10;
    }
    totalScore += turbScore * 0.20;
    totalWeight += 0.20;
  }

  // Temperature (weight: 0.15) - ideal range 50-75°F for aquatic life
  if (readings.temp !== null && readings.temp !== undefined) {
    const tempF = Number(readings.temp);
    let tempScore;
    if (tempF >= 50 && tempF <= 75) {
      tempScore = 100;
    } else if (tempF >= 40 && tempF <= 85) {
      const distFromIdeal = tempF < 50 ? 50 - tempF : tempF - 75;
      tempScore = 100 - distFromIdeal * 3;
    } else {
      tempScore = 40;
    }
    totalScore += Math.max(0, tempScore) * 0.15;
    totalWeight += 0.15;
  }

  // Conductance (weight: 0.15) - indicator of freshwater/brackish balance
  // For Hudson River estuary, moderate conductance indicates healthy mixing
  if (readings.conductance !== null && readings.conductance !== undefined) {
    const condValue = Number(readings.conductance);
    let condScore;
    if (condValue >= 100 && condValue <= 5000) {
      // Fresh to slightly brackish - healthy range
      condScore = 100;
    } else if (condValue <= 10000) {
      condScore = 80;
    } else if (condValue <= 30000) {
      condScore = 60;
    } else {
      condScore = 40;
    }
    totalScore += condScore * 0.15;
    totalWeight += 0.15;
  }

  if (totalWeight === 0) {
    return 0;
  }

  // Normalize to 0-100 based on available parameters
  const wqi = Math.round(totalScore / totalWeight);
  return Math.min(100, Math.max(0, wqi));
}

// =============================================================================
// SWIMMING SAFETY
// =============================================================================

/**
 * Determine swimming safety level based on Water Quality Index.
 *
 * @param {number} wqi - Water Quality Index (0-100)
 * @returns {{ level: string, color: string, icon: string, message: string }}
 */
export function getSwimmingSafety(wqi) {
  const score = Number(wqi);

  if (score >= 90) {
    return {
      level: 'excellent',
      label: 'Excellent',
      color: '#00BCD4',
      icon: 'swim',
      message: 'Water quality is excellent. Safe for all activities.',
    };
  }
  if (score >= 70) {
    return {
      level: 'good',
      label: 'Good',
      color: '#4CAF50',
      icon: 'swim',
      message: 'Water quality is good. Safe for swimming.',
    };
  }
  if (score >= 50) {
    return {
      level: 'moderate',
      label: 'Moderate',
      color: '#FF9800',
      icon: 'alert',
      message: 'Caution advised. Check for local advisories before swimming.',
    };
  }
  if (score >= 30) {
    return {
      level: 'poor',
      label: 'Poor',
      color: '#FF5722',
      icon: 'alert-circle',
      message: 'Not recommended for swimming. Poor water quality.',
    };
  }

  return {
    level: 'unsafe',
    label: 'Unsafe',
    color: '#F44336',
    icon: 'close-circle',
    message: 'Unsafe for swimming. Avoid water contact.',
  };
}

// =============================================================================
// WATER CLARITY
// =============================================================================

/**
 * Determine water clarity classification from turbidity reading.
 *
 * @param {number|null} turbidity - Turbidity in NTU
 * @returns {{ label: string, color: string, clarity: string, description: string }}
 */
export function getWaterClarity(turbidity) {
  if (turbidity === null || turbidity === undefined || Number.isNaN(Number(turbidity))) {
    return {
      label: 'Unknown',
      color: '#9E9E9E',
      clarity: 'Unknown',
      description: 'No turbidity data available.',
    };
  }

  const ntu = Number(turbidity);

  if (ntu <= 1) {
    return {
      label: 'Crystal Clear',
      color: '#00BCD4',
      clarity: 'Excellent',
      description: 'Exceptional clarity. Ideal for underwater visibility.',
    };
  }
  if (ntu <= 5) {
    return {
      label: 'Very Clear',
      color: '#4CAF50',
      clarity: 'Very Good',
      description: 'Great water clarity. Good underwater visibility.',
    };
  }
  if (ntu <= 10) {
    return {
      label: 'Clear',
      color: '#8BC34A',
      clarity: 'Good',
      description: 'Reasonable clarity. Adequate for most activities.',
    };
  }
  if (ntu <= 25) {
    return {
      label: 'Slightly Cloudy',
      color: '#FF9800',
      clarity: 'Fair',
      description: 'Some suspended particles. Visibility reduced.',
    };
  }
  if (ntu <= 50) {
    return {
      label: 'Cloudy',
      color: '#FF5722',
      clarity: 'Poor',
      description: 'Significant turbidity. Limited underwater visibility.',
    };
  }

  return {
    label: 'Very Cloudy',
    color: '#F44336',
    clarity: 'Very Poor',
    description: 'Heavy turbidity. Very poor visibility.',
  };
}

// =============================================================================
// FISHING SCORE CALCULATION
// =============================================================================

/**
 * Calculate an overall fishing condition score (0-100).
 * Combines water quality, temperature, flow, time of day, and tide phase.
 *
 * @param {Object} readings - Sensor readings
 * @param {number|null} readings.temp - Water temperature (°F)
 * @param {number|null} readings.dissolved_oxygen - DO in mg/L
 * @param {number|null} readings.turbidity - Turbidity in NTU
 * @param {number|null} readings.flow - River flow in ft³/s
 * @param {string|null} tidePhase - Current tide phase ('incoming', 'outgoing', 'slack', 'high', 'low')
 * @param {number|null} hour - Current hour (0-23)
 * @returns {number} Fishing score from 0-100
 */
export function calculateFishingScore(readings, tidePhase = null, hour = null) {
  if (!readings || typeof readings !== 'object') {
    return 0;
  }

  let score = 0;
  let factorCount = 0;

  // Water temperature score (weight: 30%)
  if (readings.temp !== null && readings.temp !== undefined) {
    const tempF = Number(readings.temp);
    const { min: tempMin, max: tempMax } = FISHING_IDEAL_TEMPS;
    const tempCenter = (tempMin + tempMax) / 2;
    const tempRange = (tempMax - tempMin) / 2;
    const tempDist = Math.abs(tempF - tempCenter);

    if (tempDist <= tempRange) {
      score += (1 - tempDist / tempRange) * 30;
    } else if (tempDist <= tempRange * 1.5) {
      score += 10;
    }
    factorCount += 30;
  }

  // Dissolved oxygen score (weight: 20%)
  if (readings.dissolved_oxygen !== null && readings.dissolved_oxygen !== undefined) {
    const doValue = Number(readings.dissolved_oxygen);
    if (doValue >= 7) {
      score += 20;
    } else if (doValue >= 5) {
      score += 15;
    } else if (doValue >= 3) {
      score += 8;
    } else {
      score += 2;
    }
    factorCount += 20;
  }

  // Turbidity score (weight: 15%) - moderate turbidity can be good for fishing
  if (readings.turbidity !== null && readings.turbidity !== undefined) {
    const turbValue = Number(readings.turbidity);
    // Slight turbidity (2-15 NTU) is ideal - attracts baitfish
    if (turbValue >= 2 && turbValue <= 15) {
      score += 15;
    } else if (turbValue <= 25) {
      score += 10;
    } else if (turbValue <= 50) {
      score += 5;
    } else {
      score += 2;
    }
    factorCount += 15;
  }

  // Flow score (weight: 20%)
  if (readings.flow !== null && readings.flow !== undefined) {
    const flowValue = Number(readings.flow);
    const { min: flowMin, max: flowMax } = FISHING_IDEAL_FLOW;
    const flowCenter = (flowMin + flowMax) / 2;
    const flowRange = (flowMax - flowMin) / 2;
    const flowDist = Math.abs(flowValue - flowCenter);

    if (flowDist <= flowRange) {
      score += (1 - flowDist / flowRange) * 20;
    } else if (flowDist <= flowRange * 2) {
      score += 8;
    } else {
      score += 3;
    }
    factorCount += 20;
  }

  // Tide phase score (weight: 10%)
  if (tidePhase) {
    const phaseScores = {
      incoming: 10, // Best - brings in baitfish
      outgoing: 8, // Good - concentrates fish
      high: 7, // Good - fish are active
      low: 5, // Fair - fish may be lethargic
      slack: 3, // Poor - low fish activity
    };
    score += phaseScores[tidePhase] || 5;
    factorCount += 10;
  }

  // Time of day score (weight: 5%) - dawn and dusk are best
  if (hour !== null && hour !== undefined) {
    const h = Number(hour);
    // Peak fishing times: 5-8 AM (dawn), 5-8 PM (dusk)
    const isDawn = h >= 5 && h <= 8;
    const isDusk = h >= 17 && h <= 20;
    const isDaytime = h >= 9 && h <= 16;
    const isNight = h >= 21 || h <= 4;

    if (isDawn || isDusk) {
      score += 5;
    } else if (isDaytime) {
      score += 3;
    } else if (isNight) {
      score += 2;
    }
    factorCount += 5;
  }

  if (factorCount === 0) {
    return 0;
  }

  // Normalize score based on available factors
  const normalizedScore = (score / factorCount) * 100;
  return Math.min(100, Math.max(0, Math.round(normalizedScore)));
}

/**
 * Get a fishing rating label with visual indicators.
 *
 * @param {number} score - Fishing score (0-100)
 * @returns {{ label: string, color: string, icon: string, advice: string }}
 */
export function getFishingRating(score) {
  const s = Number(score);

  if (s >= 85) {
    return {
      label: 'Excellent',
      color: '#00BCD4',
      icon: 'trophy',
      advice: 'Prime conditions! Fish are very active.',
    };
  }
  if (s >= 70) {
    return {
      label: 'Very Good',
      color: '#4CAF50',
      icon: 'thumb-up',
      advice: 'Great conditions. Expect good catches.',
    };
  }
  if (s >= 55) {
    return {
      label: 'Good',
      color: '#8BC34A',
      icon: 'check-circle',
      advice: 'Fair to good. Fish should be biting.',
    };
  }
  if (s >= 40) {
    return {
      label: 'Fair',
      color: '#FF9800',
      icon: 'alert',
      advice: 'Moderate conditions. Try different spots or baits.',
    };
  }
  if (s >= 25) {
    return {
      label: 'Poor',
      color: '#FF5722',
      icon: 'alert-circle',
      advice: 'Challenging conditions. Consider waiting for better timing.',
    };
  }

  return {
    label: 'Very Poor',
    color: '#F44336',
    icon: 'close-circle',
    advice: 'Unfavorable conditions. Best to wait.',
  };
}

// =============================================================================
// MOON PHASE CALCULATION
// =============================================================================

/**
 * Calculate the current moon phase and illumination percentage.
 * Uses a simplified astronomical algorithm based on known new moon date.
 *
 * @param {Date|null} date - Date to calculate for (defaults to now)
 * @returns {{ phase: string, illumination: number, icon: string, daysSinceNew: number }}
 */
export function getMoonPhase(date = null) {
  const targetDate = date || new Date();

  // Known new moon: January 6, 2000 at 18:14 UTC
  const knownNewMoon = new Date(Date.UTC(2000, 0, 6, 18, 14, 0));

  // Synodic month (lunar cycle) in days
  const synodicMonth = 29.53058867;

  // Calculate days since known new moon
  const diffMs = targetDate.getTime() - knownNewMoon.getTime();
  const daysSinceKnownNew = diffMs / (1000 * 60 * 60 * 24);

  // Calculate current position in lunar cycle (0 = new moon, 0.5 = full moon)
  const lunarCyclePosition = (daysSinceKnownNew % synodicMonth) / synodicMonth;
  const normalizedPosition = lunarCyclePosition < 0 ? lunarCyclePosition + 1 : lunarCyclePosition;

  // Determine phase
  let phase;
  let icon;

  if (normalizedPosition < 0.02 || normalizedPosition > 0.98) {
    phase = 'New Moon';
    icon = 'moon-new';
  } else if (normalizedPosition < 0.23) {
    phase = 'Waxing Crescent';
    icon = 'moon-waxing-crescent';
  } else if (normalizedPosition < 0.27) {
    phase = 'First Quarter';
    icon = 'moon-first-quarter';
  } else if (normalizedPosition < 0.48) {
    phase = 'Waxing Gibbous';
    icon = 'moon-waxing-gibbous';
  } else if (normalizedPosition < 0.52) {
    phase = 'Full Moon';
    icon = 'moon-full';
  } else if (normalizedPosition < 0.73) {
    phase = 'Waning Gibbous';
    icon = 'moon-waning-gibbous';
  } else if (normalizedPosition < 0.77) {
    phase = 'Last Quarter';
    icon = 'moon-last-quarter';
  } else {
    phase = 'Waning Crescent';
    icon = 'moon-waning-crescent';
  }

  // Calculate illumination (0% at new moon, 100% at full moon)
  // Use cosine curve for smooth illumination transition
  const illumination = (1 - Math.cos(normalizedPosition * 2 * Math.PI)) / 2;

  // Days since the most recent new moon
  const daysSinceNew = (normalizedPosition * synodicMonth).toFixed(1);

  return {
    phase,
    illumination: Math.round(illumination * 100),
    icon,
    daysSinceNew: Number(daysSinceNew),
  };
}

// =============================================================================
// SUNRISE / SUNSET CALCULATION
// =============================================================================

/**
 * Calculate sunrise and sunset times for a given location and date.
 * Uses a simplified algorithm based on astronomical equations.
 *
 * @param {number} lat - Latitude in decimal degrees
 * @param {number} lon - Longitude in decimal degrees
 * @param {Date|null} date - Date to calculate for (defaults to today)
 * @returns {{ sunrise: Date, sunset: Date, dayLength: number, isDaytime: boolean }}
 */
export function getSunriseSunset(lat, lon, date = null) {
  const targetDate = date || new Date();
  const latitude = Number(lat);
  const longitude = Number(lon);

  // Day of year (1-365/366)
  const startOfYear = new Date(targetDate.getFullYear(), 0, 1);
  const dayOfYear = Math.floor((targetDate - startOfYear) / 86400000) + 1;

  // Convert longitude to hour offset
  const longitudeHour = longitude / 15;

  // Approximate sunrise/sunset hour angle calculation
  // Using a simplified version of the NOAA algorithm

  // Solar declination angle (in radians)
  // Approximation: 23.45° * sin(360°/365 * (dayOfYear + 284))
  const declinationRad =
    ((23.45 * Math.PI) / 180) *
    Math.sin(((360 * (dayOfYear + 284)) / 365.25) * (Math.PI / 180));

  // Hour angle for sunrise/sunset
  // cos(H) = -tan(lat) * tan(declination)
  const latRad = (latitude * Math.PI) / 180;
  const cosHourAngle =
    -Math.tan(latRad) * Math.tan(declinationRad);

  // Clamp to valid range
  const clampedCosHourAngle = Math.max(-1, Math.min(1, cosHourAngle));
  const hourAngle = Math.acos(clampedCosHourAngle);

  // Convert hour angle to hours
  const hourAngleHours = (hourAngle * 180) / Math.PI / 15;

  // Solar noon (in local time approximation)
  const solarNoon = 12 - longitudeHour;

  // Sunrise and sunset times (in hours, UTC approximation)
  const sunriseHoursUtc = solarNoon - hourAngleHours;
  const sunsetHoursUtc = solarNoon + hourAngleHours;

  // Create Date objects
  const sunrise = new Date(targetDate);
  sunrise.setUTCHours(
    Math.floor(sunriseHoursUtc),
    Math.round((sunriseHoursUtc % 1) * 60),
    0,
    0
  );

  const sunset = new Date(targetDate);
  sunset.setUTCHours(
    Math.floor(sunsetHoursUtc),
    Math.round((sunsetHoursUtc % 1) * 60),
    0,
    0
  );

  // Day length in hours
  const dayLength = hourAngleHours * 2;

  // Check if currently daytime
  const now = targetDate.getTime();
  const isDaytime = now >= sunrise.getTime() && now < sunset.getTime();

  return {
    sunrise,
    sunset,
    dayLength: Number(dayLength.toFixed(2)),
    isDaytime,
  };
}

// =============================================================================
// ADDITIONAL ENVIRONMENTAL CALCULATIONS
// =============================================================================

/**
 * Calculate heat index from temperature and relative humidity.
 *
 * @param {number} tempF - Temperature in Fahrenheit
 * @param {number} humidity - Relative humidity percentage (0-100)
 * @returns {number|null} Heat index in Fahrenheit, or null if not applicable
 */
export function calculateHeatIndex(tempF, humidity) {
  if (tempF < 80 || humidity < 40) {
    return null; // Heat index not meaningful below these thresholds
  }

  const T = tempF;
  const R = humidity;

  // Rothfusz regression (simplified)
  const hi =
    -42.379 +
    2.04901523 * T +
    10.14333127 * R -
    0.22475541 * T * R -
    6.83783e-3 * T * T -
    5.481717e-2 * R * R +
    1.22874e-3 * T * T * R +
    8.5282e-4 * T * R * R -
    1.99e-6 * T * T * R * R;

  return Math.round(hi);
}

/**
 * Calculate wind chill from temperature and wind speed.
 *
 * @param {number} tempF - Temperature in Fahrenheit
 * @param {number} windSpeedMph - Wind speed in mph
 * @returns {number|null} Wind chill in Fahrenheit, or null if not applicable
 */
export function calculateWindChill(tempF, windSpeedMph) {
  if (tempF > 50 || windSpeedMph < 3) {
    return null; // Wind chill not applicable
  }

  const T = tempF;
  const V = windSpeedMph;

  // NWS wind chill formula
  const wc =
    35.74 +
    0.6215 * T -
    35.75 * Math.pow(V, 0.16) +
    0.4275 * T * Math.pow(V, 0.16);

  return Math.round(wc);
}

/**
 * Estimate relative humidity from air temperature and dew point.
 *
 * @param {number} tempF - Air temperature in Fahrenheit
 * @param {number} dewPointF - Dew point in Fahrenheit
 * @returns {number} Relative humidity percentage (0-100)
 */
export function calculateHumidity(tempF, dewPointF) {
  // Magnus formula approximation
  const T = tempF;
  const TD = dewPointF;

  if (TD >= T) return 100;

  // Simplified approximation
  const rh = 100 - 5 * (T - TD);
  return Math.max(0, Math.min(100, Math.round(rh)));
}

/**
 * Calculate dissolved oxygen saturation percentage.
 *
 * @param {number} doValue - Measured DO in mg/L
 * @param {number} tempC - Water temperature in Celsius
 * @param {number} salinityPpt - Salinity in ppt (default: 0 for freshwater)
 * @returns {number} DO saturation percentage
 */
export function calculateDOSaturation(doValue, tempC, salinityPpt = 0) {
  // Benson & Krause equation for DO saturation at given temp and salinity
  const T = tempC;
  const S = salinityPpt;

  // Temperature-dependent saturation (freshwater)
  const lnSat =
    -139.34411 +
    (1.575701e5 / (T + 273.15)) -
    (6.642308e7 / Math.pow(T + 273.15, 2)) +
    (1.2438e10 / Math.pow(T + 273.15, 3)) -
    (8.621949e11 / Math.pow(T + 273.15, 4));

  let saturation = Math.exp(lnSat);

  // Salinity correction
  if (S > 0) {
    const salinityFactor =
      S *
      (-1.7674e-2 +
        (2.0564e1 / (T + 273.15)) +
        (1.6959e-5 * Math.pow(T + 273.15, 2)));
    saturation *= Math.exp(salinityFactor);
  }

  const saturationPercent = (doValue / saturation) * 100;
  return Math.round(saturationPercent);
}
