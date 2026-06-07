import React, { useState, useMemo, useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  RefreshControl,
  TextInput,
  StyleSheet,
  TouchableOpacity,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import { useTheme } from '../hooks/useTheme';
import { useStations } from '../hooks/useStations';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorView } from '../components/common/ErrorView';
import { StationCard } from '../components/cards/StationCard';

const FILTER_OPTIONS = [
  { key: 'all', label: 'All' },
  { key: 'live', label: 'Live' },
  { key: 'offline', label: 'Offline' },
];

export default function StationsScreen() {
  const navigation = useNavigation();
  const { theme } = useTheme();
  const { stations, loading, error, refetch } = useStations();

  const [searchQuery, setSearchQuery] = useState('');
  const [activeFilter, setActiveFilter] = useState('all');
  const [refreshing, setRefreshing] = useState(false);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await refetch();
    setRefreshing(false);
  }, [refetch]);

  // Filter and search logic
  const filteredStations = useMemo(() => {
    let result = [...stations];

    // Filter by status
    if (activeFilter === 'live') {
      result = result.filter(s => s.status === 'live');
    } else if (activeFilter === 'offline') {
      result = result.filter(s => s.status === 'offline' || s.status === 'intermittent');
    }

    // Search by name
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter(
        s =>
          s.name.toLowerCase().includes(q) ||
          s.id.toLowerCase().includes(q) ||
          String(s.mile).includes(q)
      );
    }

    // Sort: live first, then by river mile
    result.sort((a, b) => {
      if (a.status === 'live' && b.status !== 'live') return -1;
      if (a.status !== 'live' && b.status === 'live') return 1;
      return b.mile - a.mile;
    });

    return result;
  }, [stations, activeFilter, searchQuery]);

  const liveCount = stations.filter(s => s.status === 'live').length;
  const totalCount = stations.length;

  const handleStationPress = (stationId) => {
    navigation.navigate('StationDetail', { stationId });
  };

  const clearSearch = () => {
    setSearchQuery('');
  };

  // Loading state
  if (loading && !stations.length) {
    return (
      <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
        <LoadingSpinner fullScreen message="Loading stations..." />
      </View>
    );
  }

  // Error state
  if (error && !stations.length) {
    return (
      <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
        <View style={styles.headerSpacer} />
        <ErrorView message={error} onRetry={onRefresh} />
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
      <ScrollView
        contentContainerStyle={[
          styles.scrollContent,
          filteredStations.length === 0 && styles.emptyScrollContent,
        ]}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={theme.colors.primary}
            colors={[theme.colors.primary]}
          />
        }
        keyboardShouldPersistTaps="handled"
      >
        {/* ===== HEADER ===== */}
        <View style={styles.header}>
          <Text style={[styles.title, { color: theme.colors.text }]}>
            Monitoring Stations
          </Text>
          <Text style={[styles.subtitle, { color: theme.colors.textSecondary }]}>
            {liveCount} live of {totalCount} total stations
          </Text>
        </View>

        {/* ===== SEARCH BAR ===== */}
        <View style={[styles.searchContainer, { backgroundColor: theme.colors.card }, theme.shadows.small]}>
          <MaterialCommunityIcons
            name="magnify"
            size={20}
            color={theme.colors.textTertiary}
            style={styles.searchIcon}
          />
          <TextInput
            style={[styles.searchInput, { color: theme.colors.text }]}
            placeholder="Search stations..."
            placeholderTextColor={theme.colors.textTertiary}
            value={searchQuery}
            onChangeText={setSearchQuery}
            autoCapitalize="none"
            autoCorrect={false}
          />
          {searchQuery.length > 0 && (
            <TouchableOpacity onPress={clearSearch} style={styles.clearButton} activeOpacity={0.7}>
              <MaterialCommunityIcons name="close-circle" size={18} color={theme.colors.textTertiary} />
            </TouchableOpacity>
          )}
        </View>

        {/* ===== FILTER CHIPS ===== */}
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.filterScroll}
        >
          {FILTER_OPTIONS.map(option => {
            const isActive = activeFilter === option.key;
            return (
              <TouchableOpacity
                key={option.key}
                style={[
                  styles.filterChip,
                  {
                    backgroundColor: isActive
                      ? theme.colors.primary
                      : theme.colors.card,
                  },
                  theme.shadows.small,
                ]}
                onPress={() => setActiveFilter(option.key)}
                activeOpacity={0.8}
              >
                <Text
                  style={[
                    styles.filterChipText,
                    {
                      color: isActive
                        ? theme.colors.textInverse
                        : theme.colors.textSecondary,
                    },
                  ]}
                >
                  {option.label}
                </Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>

        {/* ===== STATION LIST ===== */}
        {filteredStations.length > 0 ? (
          <View style={styles.stationsList}>
            {filteredStations.map(station => (
              <StationCard
                key={station.id}
                station={station}
                onPress={() => handleStationPress(station.id)}
              />
            ))}
          </View>
        ) : (
          /* ===== EMPTY STATE ===== */
          <View style={styles.emptyState}>
            <MaterialCommunityIcons
              name={searchQuery ? "magnify-close" : "satellite-uplink"}
              size={56}
              color={theme.colors.textTertiary}
            />
            <Text style={[styles.emptyTitle, { color: theme.colors.textSecondary }]}>
              {searchQuery ? 'No stations found' : 'No stations'}
            </Text>
            <Text style={[styles.emptyMessage, { color: theme.colors.textTertiary }]}>
              {searchQuery
                ? `No stations match "${searchQuery}". Try a different search.`
                : activeFilter !== 'all'
                ? `No ${activeFilter} stations available.`
                : 'Stations will appear here when they come online.'}
            </Text>
            {searchQuery && (
              <TouchableOpacity
                style={[styles.clearSearchButton, { backgroundColor: theme.colors.primary }]}
                onPress={clearSearch}
                activeOpacity={0.8}
              >
                <Text style={[styles.clearSearchText, { color: theme.colors.textInverse }]}>
                  Clear Search
                </Text>
              </TouchableOpacity>
            )}
          </View>
        )}

        {/* Footer spacing */}
        <View style={styles.footer} />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scrollContent: {
    paddingTop: 12,
  },
  emptyScrollContent: {
    flexGrow: 1,
  },
  headerSpacer: {
    height: 100,
  },
  header: {
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 12,
  },
  title: {
    fontSize: 22,
    fontWeight: '800',
    letterSpacing: -0.5,
  },
  subtitle: {
    fontSize: 13,
    marginTop: 2,
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: 16,
    marginVertical: 8,
    borderRadius: 12,
    paddingHorizontal: 12,
    height: 44,
  },
  searchIcon: {
    marginRight: 8,
  },
  searchInput: {
    flex: 1,
    fontSize: 15,
    height: 44,
  },
  clearButton: {
    padding: 4,
  },
  filterScroll: {
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  filterChip: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    marginRight: 8,
  },
  filterChipText: {
    fontSize: 13,
    fontWeight: '600',
  },
  stationsList: {
    marginTop: 4,
  },
  emptyState: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 32,
    marginTop: 60,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '700',
    marginTop: 16,
  },
  emptyMessage: {
    fontSize: 13,
    textAlign: 'center',
    marginTop: 8,
    lineHeight: 20,
  },
  clearSearchButton: {
    marginTop: 20,
    paddingHorizontal: 24,
    paddingVertical: 10,
    borderRadius: 8,
  },
  clearSearchText: {
    fontSize: 14,
    fontWeight: '600',
  },
  footer: {
    height: 30,
  },
});
