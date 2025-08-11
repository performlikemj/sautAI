import { Text, View, StyleSheet, Button } from 'react-native';
import { useEffect, useState } from 'react';
import { userDetails, getHealthMetrics, saveHealthMetrics } from '../src/api';

export default function ProfileScreen() {
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [metrics, setMetrics] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await userDetails();
      setProfile(res);
      if (res?.id) {
        const m = await getHealthMetrics(res.id);
        console.log('health_metrics', m);
        setMetrics(Array.isArray(m) ? m : []);
      }
    } catch (e: any) {
      setError(e?.message || 'Failed to load');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Profile</Text>
      {loading && <Text>Loading…</Text>}
      {error && <Text style={{ color: 'red' }}>{error}</Text>}
      {profile && (
        <View>
          <Text>Username: {profile.username}</Text>
          <Text>Email: {profile.email}</Text>
          <Text>Role: {profile.current_role}</Text>
          <Text style={{marginTop: 12, fontWeight: '600'}}>Latest Metrics:</Text>
          {metrics.length ? (
            <Text>{JSON.stringify(metrics[0]).slice(0, 200)}…</Text>
          ) : (
            <Text>No metrics yet.</Text>
          )}
        </View>
      )}
      <Button title="Reload" onPress={load} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 12 },
  title: { fontSize: 22, fontWeight: '600', marginBottom: 8 },
});


