import { useEffect, useState } from 'react';
import { View, Text, StyleSheet, Button, ScrollView } from 'react-native';
import { streamUserSummary } from './_api';

export default function SummaryScreen() {
  const [events, setEvents] = useState<any[]>([]);
  const [stopper, setStopper] = useState<(() => void) | null>(null);

  const start = async () => {
    if (stopper) stopper();
    const stop = await streamUserSummary({
      onEvent: (e) => {
        console.log('summary event', e);
        setEvents((prev) => [...prev, e]);
      },
      onError: (err) => console.log('summary error', err),
    });
    setStopper(() => stop);
  };

  useEffect(() => {
    start();
    return () => { if (stopper) stopper(); };
  }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Daily Summary</Text>
      <Button title="Restart Stream" onPress={start} />
      <ScrollView style={{ marginTop: 12 }}>
        {events.map((e, i) => (
          <Text key={i} style={{ marginBottom: 6 }}>{JSON.stringify(e)}</Text>
        ))}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 12 },
  title: { fontSize: 22, fontWeight: '600', marginBottom: 8 },
});


