import { useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { threadDetail } from '../../src/api';

export default function HistoryDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [messages, setMessages] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!id) return;
    (async () => {
      try {
        setLoading(true);
        setError(null);
        const res = await threadDetail(String(id));
        console.log('thread_detail', res);
        const history = res.chat_history || [];
        history.sort((a: any, b: any) => (a.created_at < b.created_at ? -1 : 1));
        setMessages(history);
      } catch (e: any) {
        setError(e?.message || 'Failed to load');
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Thread {id}</Text>
      {loading && <Text>Loading…</Text>}
      {error && <Text style={{ color: 'red' }}>{error}</Text>}
      <ScrollView contentContainerStyle={{ paddingVertical: 8 }}>
        {messages.map((m, i) => (
          <View key={i} style={[styles.bubble, m.role === 'user' ? styles.user : styles.assistant]}>
            <Text>{m.content}</Text>
          </View>
        ))}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 12 },
  title: { fontSize: 22, fontWeight: '600', marginBottom: 8 },
  bubble: { padding: 10, borderRadius: 8, marginBottom: 8, maxWidth: '90%' },
  user: { alignSelf: 'flex-end', backgroundColor: '#e8f5e9' },
  assistant: { alignSelf: 'flex-start', backgroundColor: '#f5f5f5' },
});


