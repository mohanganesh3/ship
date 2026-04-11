/**
*Root Layout — Font loading + ThemeProvider + Model init
**/
import { useEffect, useState } from 'react';
import { View, StyleSheet } from 'react-native';
import { Stack } from 'expo-router';
import { useFonts } from 'expo-font';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { ThemeProvider, useTheme } from '../providers/ThemeProvider';
import { ModelLoadingScreen } from '../components/ModelLoadingScreen';
import { useAppStore } from '../stores/appStore';
import { loadModel } from '../services/modelBridge';
import { Colors } from '../constants/theme';

import { ModelProvisioner } from '../services/ModelProvisioner';
import InitialSetupScreen from '../components/InitialSetupScreen';
import {
  setupNotificationChannel,
  __bindForegroundTask,
} from '../services/BackgroundDownloadManager';
import notifee from '@notifee/react-native';

notifee.registerForegroundService(() => {
  return new Promise((resolve) => {
    // Keep the service alive by binding the 'resolve' callback globally
    __bindForegroundTask(resolve);
  });
});

SplashScreen.preventAutoHideAsync().catch(() => {});

export default function RootLayout() {
  const [fontsLoaded, fontError] = useFonts({
    DMSerifDisplay: require('../assets/fonts/DMSerifDisplay-Regular.ttf'),
    SourceSans3Light: require('../assets/fonts/SourceSans3-Light.ttf'),
    SourceSans3: require('../assets/fonts/SourceSans3-Regular.ttf'),
    SourceSans3SemiBold: require('../assets/fonts/SourceSans3-SemiBold.ttf'),
    IBMPlexMono: require('../assets/fonts/IBMPlexMono-Regular.ttf'),
  });

  const [needsProvisioning, setNeedsProvisioning] = useState<boolean | null>(null);

  useEffect(() => {
    // Set up notification channel once at startup
    setupNotificationChannel();

    async function check() {
      const isProvisioned = await ModelProvisioner.isModelProvisioned();
      setNeedsProvisioning(!isProvisioned);
    }
    if (fontsLoaded || fontError) check();
  }, [fontsLoaded, fontError]);

  useEffect(() => {
    if ((fontsLoaded || fontError) && needsProvisioning !== null) {
      SplashScreen.hideAsync().catch(() => {});
    }
  }, [fontsLoaded, fontError, needsProvisioning]);

  if (!fontsLoaded || needsProvisioning === null) return null;

  return (
    <ThemeProvider>
      <RootLayoutContent 
        needsProvisioning={needsProvisioning} 
        onProvisionComplete={() => setNeedsProvisioning(false)}
        onReprovisionNeeded={() => setNeedsProvisioning(true)}
      />
    </ThemeProvider>
  );
}

function RootLayoutContent({ needsProvisioning, onProvisionComplete, onReprovisionNeeded }: any) {
  const { colors } = useTheme();
  const modelProgress = useAppStore(s => s.modelLoadProgress);
  const [appReady, setAppReady] = useState(false);

  useEffect(() => {
    if (!needsProvisioning) initApp();
  }, [needsProvisioning]);

  async function initApp() {
    try {
      await loadModel();
      setAppReady(true);
    } catch (e: any) {
      // Model load failed — purge corrupt file and go back to setup screen for re-download
      console.error('[Layout] loadModel failed, triggering re-provision:', e?.message);
      onReprovisionNeeded();
    }
  }

  return (
    <View style={[styles.root, { backgroundColor: colors.bgPage }]}>
      {needsProvisioning ? (
        <InitialSetupScreen onComplete={onProvisionComplete} />
      ) : !appReady ? (
        <ModelLoadingScreen progress={modelProgress} />
      ) : (
        <Stack
          screenOptions={{
            headerShown: false,
            contentStyle: { backgroundColor: colors.bgPage },
            animation: 'slide_from_right',
          }}
        />
      )}
      <StatusBar style="light" />
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
});
