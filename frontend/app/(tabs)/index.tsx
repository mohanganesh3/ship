/**
 * Thread List v2 — Cleaner, no inline action buttons
 */
import React, { useEffect, useCallback, useMemo } from 'react';
import { View, FlatList, TextInput, StyleSheet, RefreshControl } from 'react-native';
import { useRouter } from 'expo-router';
import { Colors, Fonts, Type, Space, Radius } from '../../constants/theme';
import { useTheme } from '../../providers/ThemeProvider';
import { useThreadStore, type Thread } from '../../stores/threadStore';
import { ScreenHeader } from '../../components/ScreenHeader';
import { ThreadListItem, DateSeparator, getDateGroup } from '../../components/ThreadListItem';
import { SearchIcon } from '../../components/icons';
import { getThreads } from '../../database/operations';

type ListItem =
  | { type: 'separator'; label: string }
  | { type: 'thread'; thread: Thread; index: number };

export default function ThreadListScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const { filteredThreads, setThreads, setSearchQuery, searchQuery } = useThreadStore();
  const [refreshing, setRefreshing] = React.useState(false);

  useEffect(() => {
    loadThreads();
  }, []);

  const loadThreads = async () => {
    const t = await getThreads();
    setThreads(t);
  };

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await loadThreads();
    setRefreshing(false);
  }, []);

  const handlePress = (thread: Thread) => {
    router.push(`/chat/${thread.id}`);
  };

  const listData = useMemo<ListItem[]>(() => {
    const items: ListItem[] = [];
    let lastGroup = '';
    let idx = 0;
    filteredThreads.forEach(thread => {
      const group = getDateGroup(thread.updatedAt);
      if (group !== lastGroup) {
        items.push({ type: 'separator', label: group });
        lastGroup = group;
      }
      items.push({ type: 'thread', thread, index: idx++ });
    });
    return items;
  }, [filteredThreads]);

  const renderItem = ({ item }: { item: ListItem }) => {
    if (item.type === 'separator') return <DateSeparator label={item.label} />;
    return <ThreadListItem thread={item.thread} index={item.index} onPress={handlePress} />;
  };

  return (
    <View style={[styles.container, { backgroundColor: colors.bgPage }]}>
      <ScreenHeader title="Conversations" showStatus />

      {/* Search */}
      <View style={[styles.searchWrap, { borderBottomColor: colors.borderSubtle }]}>
        <View style={[styles.searchBar, { backgroundColor: colors.bgSurface }]}>
          <SearchIcon size={16} color={colors.text4} />
          <TextInput
            style={[styles.searchInput, { color: colors.text1 }]}
            value={searchQuery}
            onChangeText={setSearchQuery}
            placeholder="Search conversations..."
            placeholderTextColor={colors.text4}
          />
        </View>
      </View>

      <FlatList
        data={listData}
        renderItem={renderItem}
        keyExtractor={(item, i) =>
          item.type === 'separator' ? `s-${i}` : `t-${(item as any).thread.id}`
        }
        contentContainerStyle={{ paddingBottom: 100 }}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.amber} />
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  searchWrap: {
    paddingHorizontal: Space.screenPadding,
    paddingVertical: Space.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  searchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: Radius.md,
    paddingHorizontal: Space.md,
    height: 38,
    gap: Space.sm,
  },
  searchInput: {
    flex: 1,
    fontFamily: Fonts.body,
    fontSize: Type.sm.fontSize,
  },
});
