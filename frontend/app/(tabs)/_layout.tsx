/**
 * Tab Layout v2 — Flat, no elevated center button
 *
 * 3 tabs: Conversations | New (+) | Settings
 * Active: amber text + thin bottom indicator, sentence case
 */
import React from 'react';
import { View, StyleSheet, Platform } from 'react-native';
import { Tabs } from 'expo-router';
import { Colors, Fonts, Space } from '../../constants/theme';
import { useTheme } from '../../providers/ThemeProvider';
import { ChatIcon, PlusCircleIcon, GearIcon } from '../../components/icons';

export default function TabLayout() {
  const { colors } = useTheme();

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          backgroundColor: colors.tabBarBg,
          borderTopColor: colors.borderSubtle,
          borderTopWidth: StyleSheet.hairlineWidth,
          height: Platform.OS === 'web' ? Space.tabBarHeight + 4 : Space.tabBarHeight + 30,
          paddingBottom: Platform.OS === 'web' ? 4 : 28,
          paddingTop: 6,
        },
        tabBarActiveTintColor: Colors.amber,
        tabBarInactiveTintColor: colors.text4,
        tabBarLabelStyle: {
          fontFamily: Fonts.body,
          fontSize: 11,
          marginTop: 1,
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Chats',
          tabBarIcon: ({ color }) => <ChatIcon size={21} color={color} />,
        }}
      />
      <Tabs.Screen
        name="new"
        options={{
          title: 'New',
          tabBarIcon: ({ color }) => <PlusCircleIcon size={23} color={color} />,
        }}
      />
      <Tabs.Screen
        name="settings"
        options={{
          title: 'Settings',
          tabBarIcon: ({ color }) => <GearIcon size={21} color={color} />,
        }}
      />
    </Tabs>
  );
}
