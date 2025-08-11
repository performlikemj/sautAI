import { Text, View, StyleSheet, Button } from 'react-native';
import { useEffect, useState } from 'react';
import { chefDashboardStats } from '../src/api';

export default function ChefScreen() {
  const [stats, setStats] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await chefDashboardStats();
      console.log('chef_stats', res);
      setStats(res);
    } catch (e: any) {
      setError(e?.message || 'Failed to load');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Chef</Text>
      {loading && <Text>Loading…</Text>}
      {error && <Text style={{ color: 'red' }}>{error}</Text>}
      {stats ? <Text>{JSON.stringify(stats).slice(0, 300)}…</Text> : <Text>No stats.</Text>}
      <Button title="Reload" onPress={load} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 12 },
  title: { fontSize: 22, fontWeight: '600', marginBottom: 8 },
});


