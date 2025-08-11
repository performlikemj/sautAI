import { View, StyleSheet, FlatList } from 'react-native';
import { Text, Button, Card, List } from 'react-native-paper';
import { useEffect, useState } from 'react';
import { deletePantryItem, getPantry } from '../src/api';

export default function PantryScreen() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await getPantry(1);
      setItems(res.results || []);
    } catch (e: any) {
      setError(e?.message || 'Failed to load');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleDelete = async (id: number) => {
    try {
      await deletePantryItem(id);
      setItems((prev) => prev.filter((x) => x.id !== id));
    } catch (e) {
      // ignore for now
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Pantry</Text>
      <Card>
        <Card.Title title="Pantry" subtitle="Manage your items" />
        <Card.Content>
          {loading && <Text>Loading…</Text>}
          {error && <Text style={{ color: 'red' }}>{error}</Text>}
          <FlatList
            data={items}
            keyExtractor={(x) => String(x.id)}
            renderItem={({ item }) => (
              <List.Item
                title={`${item.item_name} × ${item.quantity}`}
                description={item.expiration_date ? `Expires: ${item.expiration_date}` : undefined}
                right={() => <Button onPress={() => handleDelete(item.id)}>Delete</Button>}
              />
            )}
            ItemSeparatorComponent={() => <View style={{ height: StyleSheet.hairlineWidth, backgroundColor: '#eee' }} />}
          />
          <Button mode="contained" onPress={load} style={{ marginTop: 12 }}>Reload</Button>
        </Card.Content>
      </Card>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 12 },
  title: { fontSize: 22, fontWeight: '600', marginBottom: 8 },
  row: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10 },
});


