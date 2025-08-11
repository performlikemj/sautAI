import { Text, View, StyleSheet, FlatList, Button } from 'react-native';
import { useEffect, useState } from 'react';
import { threadHistory } from '../src/api';
import { Link } from 'expo-router';

export default function HistoryScreen() {
  const [items, setItems] = useState<any[]>([]);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async (p = 1) => {
    try {
      setLoading(true);
      setError(null);
      const res = await threadHistory(p);
      setItems(res.results || []);
      setPage(p);
    } catch (e: any) {
      setError(e?.message || 'Failed to load');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load(1);
  }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>History</Text>
      {loading && <Text>Loading…</Text>}
      {error && <Text style={{ color: 'red' }}>{error}</Text>}
      <FlatList
        data={items}
        keyExtractor={(x) => String(x.id)}
        renderItem={({ item }) => (
          <Link href={{ pathname: '/history/[id]', params: { id: String(item.openai_thread_id || item.id) } }} asChild>
            <View style={{ paddingVertical: 10 }}>
              <Text>{item.title}</Text>
              <Text style={{ color: '#666' }}>{item.created_at}</Text>
            </View>
          </Link>
        )}
        ItemSeparatorComponent={() => <View style={{ height: StyleSheet.hairlineWidth, backgroundColor: '#eee' }} />}
      />
      <View style={{ flexDirection: 'row', gap: 8, justifyContent: 'center', paddingVertical: 8 }}>
        <Button title="Prev" onPress={() => load(Math.max(1, page - 1))} />
        <Button title="Next" onPress={() => load(page + 1)} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 12 },
  title: { fontSize: 22, fontWeight: '600', marginBottom: 8 },
});


