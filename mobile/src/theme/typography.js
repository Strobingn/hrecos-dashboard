// ============================================================================
// HRECOS RiverWatch - Typography Scale
// Clean, readable type hierarchy for environmental data display
// ============================================================================

const fontFamily = {
  regular: 'System',
  medium: 'System',
  semibold: 'System',
  bold: 'System',
};

export const typography = {
  // Display headings
  h1: {
    fontSize: 32,
    fontWeight: 'bold',
    fontFamily: fontFamily.bold,
    lineHeight: 40,
    letterSpacing: -0.5,
  },
  h2: {
    fontSize: 24,
    fontWeight: 'bold',
    fontFamily: fontFamily.bold,
    lineHeight: 32,
    letterSpacing: -0.3,
  },
  h3: {
    fontSize: 20,
    fontWeight: '600',
    fontFamily: fontFamily.semibold,
    lineHeight: 28,
    letterSpacing: -0.2,
  },
  h4: {
    fontSize: 18,
    fontWeight: '600',
    fontFamily: fontFamily.semibold,
    lineHeight: 26,
    letterSpacing: -0.1,
  },

  // Body text
  body: {
    fontSize: 16,
    fontWeight: '400',
    fontFamily: fontFamily.regular,
    lineHeight: 24,
    letterSpacing: 0,
  },
  bodySmall: {
    fontSize: 14,
    fontWeight: '400',
    fontFamily: fontFamily.regular,
    lineHeight: 20,
    letterSpacing: 0,
  },

  // Supporting text
  caption: {
    fontSize: 12,
    fontWeight: '500',
    fontFamily: fontFamily.medium,
    lineHeight: 16,
    letterSpacing: 0.2,
  },
  label: {
    fontSize: 11,
    fontWeight: 'bold',
    fontFamily: fontFamily.bold,
    lineHeight: 14,
    letterSpacing: 0.8,
    textTransform: 'uppercase',
  },
};
