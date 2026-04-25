/**
 * Settings v2 — Card-free rows, cleaner layout
 */
import React from 'react';
import { View, Text, Pressable, ScrollView, Alert, StyleSheet, Platform } from 'react-native';
import { Colors, Fonts, Type, Space, Radius } from '../../constants/theme';
import {
  MODEL_ARTIFACT_CONTEXT_TOKENS,
  MODEL_ARTIFACT_SIZE_LABEL,
  MODEL_BACKBONE_LABEL,
  MODEL_DISPLAY_NAME,
  MODEL_REPO_ID,
  MODEL_RUNTIME_CONTEXT_TOKENS,
  MODEL_RUNTIME_LABEL,
  MODEL_VARIANT_LABEL,
} from '../../constants/model';
import { useTheme } from '../../providers/ThemeProvider';
import { useAppStore } from '../../stores/appStore';
import { useThreadStore } from '../../stores/threadStore';
import { ScreenHeader } from '../../components/ScreenHeader';
import { AnchorIcon } from '../../components/icons';
import { clearAllThreads } from '../../database/operations';

export default function SettingsScreen() {
  const { colors, toggleMode, isDark } = useTheme();
  const { modelStatus } = useAppStore();
  const { setThreads } = useThreadStore();

  const handleClear = () => {
    if (Platform.OS === 'web') {
      if (confirm('Clear all conversations? This cannot be undone.')) doClear();
    } else {
      Alert.alert('Clear All', 'Delete all chat history? This cannot be undone.', [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Clear', style: 'destructive', onPress: doClear },
      ]);
    }
  };
  const doClear = async () => {
    await clearAllThreads();
    setThreads([]);
  };

  return (
    <View style={[styles.container, { backgroundColor: colors.bgPage }]}>
      <ScreenHeader title="Settings" />
      <ScrollView contentContainerStyle={styles.scroll}>
        {/* Model section */}
        <Text style={[styles.section, { color: colors.text4 }]}>Model</Text>
        <View style={[styles.group, { backgroundColor: colors.bgSurface, borderColor: colors.borderSubtle }]}>
          <SettingsRow
            label="Status"
            value={modelStatus === 'active' ? 'Loaded' : modelStatus === 'loading' ? 'Loading' : 'Offline'}
            colors={colors}
          />
          <Divider color={colors.borderSubtle} />
          <SettingsRow label="Variant" value={MODEL_VARIANT_LABEL} colors={colors} />
          <Divider color={colors.borderSubtle} />
          <SettingsRow label="Backbone" value={MODEL_BACKBONE_LABEL} colors={colors} />
          <Divider color={colors.borderSubtle} />
          <SettingsRow label="Artifact Size" value={MODEL_ARTIFACT_SIZE_LABEL} colors={colors} />
          <Divider color={colors.borderSubtle} />
          <SettingsRow label="Context" value={`${MODEL_ARTIFACT_CONTEXT_TOKENS.toLocaleString()} artifact / ${MODEL_RUNTIME_CONTEXT_TOKENS.toLocaleString()} runtime`} colors={colors} />
          <Divider color={colors.borderSubtle} />
          <SettingsRow label="Runtime" value={MODEL_RUNTIME_LABEL} colors={colors} />
          <Divider color={colors.borderSubtle} />
          <SettingsRow label="Repo" value={MODEL_REPO_ID} colors={colors} />
        </View>

        {/* Appearance */}
        <Text style={[styles.section, { color: colors.text4 }]}>Appearance</Text>
        <View style={[styles.group, { backgroundColor: colors.bgSurface, borderColor: colors.borderSubtle }]}>
          <Pressable onPress={toggleMode} style={styles.row}>
            <Text style={[styles.label, { color: colors.text1 }]}>Theme</Text>
            <Text style={[styles.value, { color: Colors.amber }]}>{isDark ? 'Dark' : 'Light'}</Text>
          </Pressable>
        </View>

        {/* Data */}
        <Text style={[styles.section, { color: colors.text4 }]}>Data</Text>
        <View style={[styles.group, { backgroundColor: colors.bgSurface, borderColor: colors.borderSubtle }]}>
          <Pressable onPress={handleClear} style={styles.row}>
            <Text style={[styles.label, { color: Colors.danger }]}>Clear All Conversations</Text>
          </Pressable>
        </View>

        {/* About */}
        <Text style={[styles.section, { color: colors.text4 }]}>About</Text>
        <View style={[styles.group, { backgroundColor: colors.bgSurface, borderColor: colors.borderSubtle }]}>
          <View style={styles.aboutRow}>
            <AnchorIcon size={24} color={Colors.amber} />
            <View style={styles.aboutText}>
              <Text style={[styles.aboutName, { color: colors.text1 }]}>{MODEL_DISPLAY_NAME}</Text>
              <Text style={[styles.aboutVer, { color: colors.text4 }]}>v1.0.0</Text>
            </View>
          </View>
          <Divider color={colors.borderSubtle} />
          <Text style={[styles.aboutDesc, { color: colors.text3 }]}>
            Your custom Ship fine-tune runs fully on-device after download. No chat API is called at inference time;
            the app loads the local GGUF and chats through a local llama.cpp runtime.
          </Text>
        </View>
      </ScrollView>
    </View>
  );
}

function SettingsRow({ label, value, colors }: { label: string; value: string; colors: any }) {
  return (
    <View style={styles.row}>
      <Text style={[styles.label, { color: colors.text2 }]}>{label}</Text>
      <Text style={[styles.value, { color: colors.text1 }]} numberOfLines={2}>
        {value}
      </Text>
    </View>
  );
}

function Divider({ color }: { color: string }) {
  return <View style={[styles.divider, { backgroundColor: color }]} />;
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: {
    paddingHorizontal: Space.screenPadding,
    paddingBottom: 100,
  },
  section: {
    fontFamily: Fonts.bodySemibold,
    fontSize: Type.xs.fontSize,
    letterSpacing: 0.5,
    textTransform: 'uppercase',
    marginTop: Space['2xl'],
    marginBottom: Space.sm,
    paddingLeft: Space.xs,
  },
  group: {
    borderRadius: Radius.md,
    borderWidth: StyleSheet.hairlineWidth,
    overflow: 'hidden',
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: Space.lg,
    paddingVertical: 14,
    minHeight: Space.tapTarget,
  },
  label: {
    fontFamily: Fonts.body,
    fontSize: Type.base.fontSize,
  },
  value: {
    fontFamily: Fonts.body,
    fontSize: Type.sm.fontSize,
    flexShrink: 1,
    textAlign: 'right',
    marginLeft: Space.lg,
  },
  divider: {
    height: StyleSheet.hairlineWidth,
    marginLeft: Space.lg,
  },
  aboutRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Space.md,
    padding: Space.lg,
  },
  aboutText: { gap: 2 },
  aboutName: {
    fontFamily: Fonts.display,
    fontSize: Type.md.fontSize,
  },
  aboutVer: {
    fontFamily: Fonts.body,
    fontSize: Type.xs.fontSize,
  },
  aboutDesc: {
    fontFamily: Fonts.body,
    fontSize: Type.sm.fontSize,
    lineHeight: Type.sm.lineHeight,
    padding: Space.lg,
    paddingTop: 0,
  },
});
