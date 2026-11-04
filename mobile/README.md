# HRECOS RiverWatch

An Android app for monitoring Hudson River environmental conditions in real-time. Built with React Native and Expo.

![HRECOS RiverWatch](https://img.shields.io/badge/HRECOS-RiverWatch-0A7EA4?style=for-the-badge)
![React Native](https://img.shields.io/badge/React_Native-0.85-61DAFB?style=for-the-badge&logo=react)
![Expo](https://img.shields.io/badge/Expo-SDK_56-000020?style=for-the-badge&logo=expo)
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
- Data from NOAA Station 8518935 (Newburgh)

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

- **Framework**: React Native with Expo SDK 56
- **Navigation**: React Navigation v7 (Stack + Bottom Tabs)
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
npm install --legacy-peer-deps
```

3. **Start the development server**:
```bash
npx expo start
```

4. **Run on Android**:
- Press `a` to open on Android emulator
- Or scan the QR code with the Expo Go app on your physical device

### Building for Production

**GitHub APK build**:

[Build Android APK](https://github.com/Strobingn/hrecos-dashboard/actions/workflows/build.yml) runs on mobile changes pushed to `main` or `codex`. It can also be started with **Run workflow**. It runs the mobile tests, generates Android files, builds the release APK, verifies its signature and uploads `hrecos-riverwatch-apk` as a downloadable artifact. The artifact contains `hrecos-riverwatch.apk` and its SHA-256 checksum.

**EAS APK build**:
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
npm install --legacy-peer-deps
```

## License

MIT License - feel free to use, modify, and distribute!

---

Built with passion for the Hudson River community. Data provided by HRECOS, USGS, NOAA, and NDBC.

## Units, weather and alert limits

The API publishes temperatures in Fahrenheit. The app converts readings only for display. Choose Imperial or Metric in Settings, or use the °F / °C control on Home. The shared preference persists across restarts and updates station readings, historical values, fishing temperatures and tide heights.

Home and Alerts show weather for the West Point location in the shared station registry. The forecast is from [Open-Meteo](https://open-meteo.com/en/docs) and refreshes every five minutes while the app is in use. Weather also works when the configured HRECOS API is unavailable.

Settings → Weather alerts lets you enable or disable warnings, set sustained-wind, gust and hourly-rain limits, and choose a 3, 6, 12 or 24-hour window. Wind limits use mph or km/h; rain limits use inches or millimeters per hour. Limits are stored on this device. Changing display units preserves their physical values.

Warnings appear inside the app when current wind or an hourly forecast crosses a limit. They are not official weather warnings or background push notifications. Alerts pause when the last successful forecast is more than 30 minutes old. Missing weather values stay unavailable. Hourly rain is the total for the hour ending at the provider's timestamp.

Run the checks after installing dependencies:

```bash
cd mobile
npm test
npx expo export --platform android --output-dir /tmp/riverwatch-android
```

Tests cover temperature conversion, zero and missing values, weather thresholds, forecast windows, stale data and unit changes. The source check parses JSX and verifies local imports. CI also exports an Android JavaScript bundle with [Expo CLI](https://docs.expo.dev/more/expo-cli/); device testing is still needed.
