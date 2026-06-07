# HRECOS RiverWatch

A rockstar Android app for monitoring Hudson River environmental conditions in real-time. Built with React Native and Expo.

![HRECOS RiverWatch](https://img.shields.io/badge/HRECOS-RiverWatch-0A7EA4?style=for-the-badge)
![React Native](https://img.shields.io/badge/React_Native-0.72+-61DAFB?style=for-the-badge&logo=react)
![Expo](https://img.shields.io/badge/Expo-SDK_52-000020?style=for-the-badge&logo=expo)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

## Features

### Core Environmental Monitoring
- **Real-time Water Data** from 5 HRECOS monitoring stations
- **Water Temperature** tracking with trends and comfort zones
- **Water Flow/Discharge** monitoring with flood level awareness
- **Turbidity (Water Clarity)** visual indicator - see how clean or dirty the water is
- **Dissolved Oxygen, pH, Salinity, Conductance** tracking
- **AI Anomaly Detection** alerts for unusual readings

### Tide Information
- **48-Hour Tide Charts** with high/low predictions
- **Current Tide Status** - rising or falling with countdown to next tide
- **Moon Phase** with illumination percentage
- Data from NOAA Station 8518490 (Newburgh)

### Water Quality Assessment
- **Water Quality Index (WQI)** - overall river health score 0-100
- **Swimming Safety Rating** - Safe, Caution, or Unsafe based on real conditions
- **Water Clarity Visualizer** - from Crystal Clear to Very Dirty
- **Per-Station Quality Breakdown** with detailed parameter analysis

### Fishing Conditions Predictor
- **Fishing Score** 0-100 based on multiple factors
- **Score Breakdown**: Water Temp, Clarity, Flow, Tide Phase, Time of Day
- **Best Fishing Times** for today
- **Dynamic Tips** based on current conditions

### App Features
- **Dark Mode** support with beautiful ocean-themed palette
- **Push Notifications** for water quality alerts and fishing updates
- **Offline Support** with cached data
- **6-Tab Navigation**: Home, Stations, Tides, Quality, Fish, Alerts
- **Material Design 3** with custom water-themed styling
- **Favorite Stations** for quick access
- **Configurable Units** (Imperial/Metric)

## Screenshots

| Dashboard | Stations | Station Detail |
|-----------|----------|----------------|
| Overview of all stations | List with search & filter | Detailed parameter view |
| Water quality gauge | Live/offline indicators | Historical charts |
| Quick stats row | Key readings preview | Statistics & trends |

| Tides | Water Quality | Fishing |
|-------|--------------|---------|
| 48-hour tide chart | WQI gauge | Fishing score |
| Current tide status | Swimming safety | Score breakdown |
| Moon phase | Clarity visualizer | Best times |

## Tech Stack

- **Framework**: React Native with Expo SDK 52
- **Navigation**: React Navigation v6 (Stack + Bottom Tabs)
- **State Management**: TanStack Query (React Query) for server state
- **Charts**: react-native-chart-kit
- **Styling**: StyleSheet with custom theme system
- **Storage**: AsyncStorage for persistence
- **Notifications**: expo-notifications

## Quick Start

### Prerequisites
- Node.js 18+ and npm/yarn
- Expo CLI: `npm install -g expo-cli`
- Android Studio (for Android emulator) or a physical Android device

### Installation

1. **Clone or download this project**:
```bash
cd hrecos-riverwatch
```

2. **Install dependencies**:
```bash
npm install
```

3. **Start the development server**:
```bash
npx expo start
```

4. **Run on Android**:
- Press `a` to open on Android emulator
- Or scan the QR code with the Expo Go app on your physical device

### Building for Production

**APK Build (easiest)**:
```bash
npx eas build -p android --profile preview
```

**AAB Build (for Play Store)**:
```bash
npx eas build -p android --profile production
```

## Project Structure

```
├── App.js                          # Root component
├── app.json                        # Expo configuration
├── package.json                    # Dependencies
├── babel.config.js                 # Babel configuration
└── src/
    ├── api/
    │   └── hrecosApi.js            # REST API client
    ├── components/
    │   ├── common/                 # Shared UI components
    │   │   ├── Card.js
    │   │   ├── Badge.js
    │   │   ├── LoadingSpinner.js
    │   │   ├── ErrorView.js
    │   │   └── SectionHeader.js
    │   ├── charts/                 # Chart components
    │   │   ├── LineChart.js
    │   │   ├── BarChart.js
    │   │   └── TideChart.js
    │   ├── gauges/                 # Circular gauges
    │   │   ├── WaterQualityGauge.js
    │   │   ├── FishingScoreGauge.js
    │   │   └── TemperatureGauge.js
    │   └── cards/                  # Data cards
    │       ├── StationCard.js
    │       ├── MetricCard.js
    │       ├── TideCard.js
    │       ├── AlertCard.js
    │       └── ParameterCard.js
    ├── screens/
    │   ├── DashboardScreen.js      # Main overview
    │   ├── StationsScreen.js       # Station list
    │   ├── StationDetailScreen.js  # Station details
    │   ├── TidesScreen.js          # Tide predictions
    │   ├── WaterQualityScreen.js   # Water quality
    │   ├── FishingScreen.js        # Fishing predictor
    │   ├── AlertsScreen.js         # Anomaly alerts
    │   └── SettingsScreen.js       # App settings
    ├── hooks/                      # React Query data hooks
    │   ├── useStations.js
    │   ├── useStationData.js
    │   ├── useTides.js
    │   ├── useHistorical.js
    │   ├── useStats.js
    │   ├── useDashboard.js
    │   ├── useAnomalies.js
    │   └── useTheme.js
    ├── navigation/
    │   └── AppNavigator.js         # Navigation setup
    ├── context/
    │   └── ThemeContext.js         # Dark/light mode
    ├── theme/
    │   ├── colors.js               # Color palette
    │   ├── typography.js           # Font styles
    │   ├── spacing.js              # Spacing scale
    │   └── index.js                # Theme barrel export
    ├── utils/
    │   ├── constants.js            # App constants
    │   ├── formatters.js           # Data formatting
    │   └── calculations.js         # Score calculations
    └── constants/
        └── index.js                # UI constants
```

## Data Sources

This app connects to the HRECOS Dashboard API which aggregates data from:
- **USGS** (United States Geological Survey) - Water parameters
- **NOAA** (National Oceanic and Atmospheric Administration) - Tide predictions
- **NDBC** (National Data Buoy Center) - Meteorological data

### Live Monitoring Stations

| Station | Location | Parameters | Status |
|---------|----------|------------|--------|
| Turkey Point | Catskill, NY | Temp, Conductance | Live |
| Norrie Point | Staatsburg, NY | Air Temp, Wind, Pressure | Live (Met) |
| Coxsackie | Coxsackie, NY | Temp | Live |
| Schodack Landing | Schodack, NY | Temp, DO, pH, Turbidity | Live |
| Albany | Albany, NY | Temp | Live |

## Water Parameters Monitored

- **Water Temperature** (F) - River water temperature
- **Turbidity** (NTU) - Water clarity/cloudiness
- **Dissolved Oxygen** (mg/L) - Oxygen available for aquatic life
- **pH** - Acidity/alkalinity balance
- **Conductance** (uS/cm) - Water's ability to conduct electricity
- **Salinity** (PSU) - Salt content
- **Discharge/Flow** (ft/s) - River flow rate
- **Air Temperature** (F) - From meteorological stations
- **Wind Speed/Direction** - From meteorological stations
- **Pressure** (inHg) - Atmospheric pressure

## Calculations

### Water Quality Index (WQI)
```
WQI = (Turbidity_Score * 0.30) + (DO_Score * 0.30) + (pH_Score * 0.20) + (Temp_Score * 0.20)
```

### Fishing Score
```
Score = (Temp * 0.25) + (Clarity * 0.20) + (Flow * 0.20) + (Tide * 0.20) + (Time * 0.15)
```

### Swimming Safety
Based on WQI: 80+ = Safe, 60-79 = Caution, 40-59 = Unsafe, <40 = Hazardous

## API Configuration

By default, the app connects to `https://hrecos.yourdomain.com`. You can change this in the Settings screen or by modifying `src/utils/constants.js`:

```javascript
export const API_BASE_URL = 'https://your-hrecos-api.com';
```

## Troubleshooting

### Metro bundler issues
```bash
npx expo start --clear
```

### Android build fails
```bash
cd android && ./gradlew clean && cd .. && npx expo run:android
```

### Dependency issues
```bash
rm -rf node_modules package-lock.json
npm install
```

## License

MIT License - feel free to use, modify, and distribute!

---

Built with passion for the Hudson River community. Data provided by HRECOS, USGS, NOAA, and NDBC.
