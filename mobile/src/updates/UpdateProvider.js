import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Modal,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { downloadAndInstall, findUpdate, getInstalledVersion } from './appUpdates';

const UpdateContext = createContext({
  installedVersion: '1.0.1',
  checkForUpdate: async () => {},
  checking: false,
});

export function useAppUpdate() {
  return useContext(UpdateContext);
}

export function UpdateProvider({ children }) {
  const [installedVersion, setInstalledVersion] = useState(getInstalledVersion());
  const [checking, setChecking] = useState(false);
  const [offer, setOffer] = useState(null);
  const [downloading, setDownloading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [errorText, setErrorText] = useState('');

  const checkForUpdate = useCallback(async (manual = false) => {
    if (checking || downloading) return;
    setChecking(true);
    try {
      const update = await findUpdate();
      setInstalledVersion(getInstalledVersion());
      if (update) {
        setErrorText('');
        setProgress(0);
        setOffer(update);
      } else if (manual) {
        Alert.alert('Up to date', `You're on version ${getInstalledVersion()}.`);
      }
    } catch (error) {
      console.warn('Update check failed:', error?.message || error);
      if (manual) {
        Alert.alert(
          "Couldn't check for updates",
          'Check your connection and try again.'
        );
      }
    } finally {
      setChecking(false);
    }
  }, [checking, downloading]);

  useEffect(() => {
    checkForUpdate(false);
    // Launch check runs once. Manual checks go through the settings button.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const startUpdate = useCallback(async () => {
    if (!offer || downloading) return;
    setDownloading(true);
    setErrorText('');
    setProgress(0);
    try {
      await downloadAndInstall(offer, setProgress);
      setOffer(null);
    } catch (error) {
      console.warn('Update install failed:', error?.message || error);
      setErrorText(
        error?.code === 'INSTALL_PERMISSION'
          ? error.message
          : 'The download did not finish. Try again when you have a connection.'
      );
    } finally {
      setDownloading(false);
    }
  }, [offer, downloading]);

  const percent = Math.round(progress * 100);

  return (
    <UpdateContext.Provider value={{ installedVersion, checkForUpdate, checking }}>
      {children}
      <Modal visible={!!offer} transparent animationType="fade" onRequestClose={() => !downloading && setOffer(null)}>
        <View style={styles.backdrop}>
          <View style={styles.card}>
            <Text style={styles.title}>Update {offer?.version}</Text>
            <Text style={styles.subtitle}>
              Installed version {installedVersion}
              {offer?.prerelease ? ' · prerelease' : ''}
            </Text>
            <ScrollView style={styles.notes} contentContainerStyle={styles.notesContent}>
              <Text style={styles.notesText}>
                {offer?.notes || 'No release notes.'}
              </Text>
            </ScrollView>
            {downloading && (
              <View style={styles.progressTrack}>
                <View style={[styles.progressFill, { width: `${percent}%` }]} />
              </View>
            )}
            {!!errorText && <Text style={styles.error}>{errorText}</Text>}
            <View style={styles.actions}>
              <TouchableOpacity
                style={styles.later}
                disabled={downloading}
                onPress={() => setOffer(null)}
              >
                <Text style={styles.laterText}>Later</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.update}
                disabled={downloading}
                onPress={startUpdate}
              >
                {downloading ? (
                  <ActivityIndicator color="#FFFFFF" />
                ) : (
                  <Text style={styles.updateText}>
                    {errorText ? 'Try again' : 'Update'}
                  </Text>
                )}
              </TouchableOpacity>
            </View>
            {downloading && (
              <Text style={styles.progressLabel}>Downloading {percent}%</Text>
            )}
          </View>
        </View>
      </Modal>
    </UpdateContext.Provider>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(15, 23, 42, 0.45)',
    justifyContent: 'center',
    padding: 24,
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 20,
    maxHeight: '80%',
  },
  title: {
    fontSize: 20,
    fontWeight: '700',
    color: '#0F172A',
  },
  subtitle: {
    marginTop: 4,
    fontSize: 13,
    color: '#64748B',
  },
  notes: {
    marginTop: 14,
    maxHeight: 220,
  },
  notesContent: {
    paddingBottom: 4,
  },
  notesText: {
    fontSize: 14,
    lineHeight: 20,
    color: '#334155',
  },
  progressTrack: {
    marginTop: 14,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#E2E8F0',
    overflow: 'hidden',
  },
  progressFill: {
    height: 8,
    backgroundColor: '#0A7EA4',
  },
  progressLabel: {
    marginTop: 8,
    textAlign: 'center',
    color: '#64748B',
    fontSize: 12,
  },
  error: {
    marginTop: 12,
    color: '#B91C1C',
    fontSize: 13,
    lineHeight: 18,
  },
  actions: {
    marginTop: 16,
    flexDirection: 'row',
    justifyContent: 'flex-end',
  },
  later: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    marginRight: 8,
  },
  laterText: {
    color: '#475569',
    fontSize: 15,
    fontWeight: '600',
  },
  update: {
    backgroundColor: '#0A7EA4',
    borderRadius: 10,
    minWidth: 110,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  updateText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '700',
  },
});
