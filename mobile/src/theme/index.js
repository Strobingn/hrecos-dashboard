// HRECOS RiverWatch - Theme Configuration

export const COLORS = {
  // Primary palette - Hudson River blues
  primary: '#1A6BAA',
  primaryLight: '#4A9BD4',
  primaryDark: '#0D4A7A',
  primaryFaded: '#1A6BAA20',

  // Secondary accent - teal/water
  secondary: '#2A9D8F',
  secondaryLight: '#4DBFAF',
  secondaryFaded: '#2A9D8F20',

  // Status colors
  success: '#28A745',
  successLight: '#28A74520',
  warning: '#F0A030',
  warningLight: '#F0A03020',
  danger: '#DC3545',
  dangerLight: '#DC354520',
  info: '#17A2B8',
  infoLight: '#17A2B820',

  // Water quality colors
  wqiExcellent: '#28A745',
  wqiGood: '#8BC34A',
  wqiModerate: '#FFC107',
  wqiPoor: '#FF9800',
  wqiBad: '#DC3545',

  // Backgrounds
  background: '#F0F4F8',
  card: '#FFFFFF',
  surface: '#FFFFFF',
  surfaceVariant: '#E8EDF2',

  // Text
  text: '#1A2332',
  textPrimary: '#1A2332',
  textSecondary: '#5A6A7A',
  textTertiary: '#8A96A5',
  textInverse: '#FFFFFF',

  // Misc UI
  transparent: 'transparent',
  disabled: '#B0B8C4',
  accent: '#FF8F00',
  chartGrid: '#E2E8F0',

  // Border & dividers
  border: '#D5DDE5',
  divider: '#E2E8F0',

  // Chart colors
  chartTemp: '#E74C3C',
  chartTurbidity: '#8E44AD',
  chartDO: '#3498DB',
  chartPH: '#2ECC71',
  chartConductivity: '#F39C12',
  chartSalinity: '#1ABC9C',
  chartDepth: '#34495E',
  chartSpeed: '#E67E22',
  chartDirection: '#9B59B6',

  // Tide colors
  tideHigh: '#E74C3C',
  tideLow: '#3498DB',

  // Transparency helpers
  overlay: 'rgba(0,0,0,0.4)',
  overlayLight: 'rgba(0,0,0,0.15)',
};

export const SPACING = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  xxxl: 32,
};

export const FONTS = {
  // Using system fonts - these map to fontWeight values
  bold: '700',
  semibold: '600',
  medium: '500',
  regular: '400',
  light: '300',

  size: {
    xs: 10,
    sm: 12,
    md: 14,
    lg: 16,
    xl: 18,
    xxl: 20,
    xxxl: 24,
    display: 32,
  },
};

export const SHADOWS = {
  small: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  medium: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.12,
    shadowRadius: 4,
    elevation: 4,
  },
  large: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 6,
  },
};

export const RADIUS = {
  sm: 6,
  md: 10,
  lg: 14,
  xl: 20,
  round: 999,
};

export const DARK_THEME = {
  ...COLORS,
  background: '#0F1923',
  card: '#1A2332',
  surface: '#1A2332',
  surfaceVariant: '#253042',
  text: '#E8EDF2',
  textPrimary: '#E8EDF2',
  textSecondary: '#9AA8B8',
  textTertiary: '#6A7A8A',
  border: '#354050',
  divider: '#2A3A4A',
  chartGrid: '#2A3A4A',
};

export const getTheme = (isDark = false) => ({
  colors: isDark ? DARK_THEME : COLORS,
  spacing: SPACING,
  fonts: FONTS,
  shadows: SHADOWS,
  radius: RADIUS,
  isDark,
});
