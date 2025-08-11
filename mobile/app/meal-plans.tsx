import { Text, View, StyleSheet, Button } from 'react-native';
import { useEffect, useState } from 'react';
import { approveMealPlan, getMealPlans } from '../src/api';

export default function MealPlansScreen() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<any>(null);
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null);

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await getMealPlans({});
      console.log('meal_plans', res);
      setData(res);
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
      <Text style={styles.title}>Meal Plans</Text>
      {loading && <Text>Loading…</Text>}
      {error && <Text style={{ color: 'red' }}>{error}</Text>}
      {Array.isArray(data?.results) && data.results.length > 0 ? (
        <>
          <Text>Found {data.results.length} plan(s).</Text>
          <Button title="Approve first plan" onPress={async () => {
            try {
              const plan = data.results[0];
              setSelectedPlanId(plan.id);
              const r = await approveMealPlan(plan.id);
              console.log('approve result', r);
            } catch (e) { console.log('approve error', e); }
          }} />
        </>
      ) : (
        <Text>No meal plans yet.</Text>
      )}
      <Button title="Reload" onPress={load} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 22, fontWeight: '600', marginBottom: 8 },
});


