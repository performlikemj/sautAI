import { View, StyleSheet, ScrollView } from 'react-native';
import { Text, TextInput, Button, Card } from 'react-native-paper';
import { useRef, useState } from 'react';
import { streamAssistant } from '../src/api';

export default function AssistantScreen() {
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant'; content: string }[]>([]);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [input, setInput] = useState('');

  const handleSend = () => {
    if (!input.trim()) return;
    const msg = input;
    setMessages((m) => [...m, { role: 'user', content: msg }]);
    setInput('');
    // For now, call guest stream. We'll add auth hookup shortly.
    streamAssistant({
      message: msg,
      threadId,
      isGuest: true,
      onEvent: (data) => {
        // Debug log raw events
        console.log('assistant event', data);
        const type = data.type;
        if (type === 'response.created' && data.id) {
          setThreadId(data.id as string);
        }
        if (type === 'response.output_text.delta' || type === 'text') {
          const delta = data.delta?.text || data.content || '';
          if (!delta) return;
          setMessages((m) => {
            const last = m[m.length - 1];
            if (last?.role === 'assistant') {
              const merged = [...m];
              merged[merged.length - 1] = { role: 'assistant', content: last.content + delta };
              return merged;
            }
            return [...m, { role: 'assistant', content: delta }];
          });
        }
      },
    });
  };

  return (
    <View style={styles.container}>
      <Card style={{ flex: 1 }}>
        <Card.Title title="Assistant" subtitle={threadId ? `Thread: ${threadId}` : undefined} />
        <Card.Content style={{ flex: 1 }}>
          <ScrollView style={styles.messages} contentContainerStyle={{ padding: 12 }}>
            {messages.map((m, i) => (
              <View key={i} style={[styles.bubble, m.role === 'user' ? styles.user : styles.assistant]}>
                <Text>{m.content}</Text>
              </View>
            ))}
          </ScrollView>
        </Card.Content>
        <Card.Actions style={styles.inputRow}>
          <TextInput style={{ flex: 1 }} mode="outlined" value={input} onChangeText={setInput} placeholder="Type a message" />
          <Button mode="contained" onPress={handleSend} style={{ marginLeft: 8 }}>Send</Button>
        </Card.Actions>
      </Card>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  title: { fontSize: 22, fontWeight: '600', margin: 12 },
  messages: { flex: 1 },
  bubble: { padding: 10, borderRadius: 8, marginBottom: 8, maxWidth: '90%' },
  user: { alignSelf: 'flex-end', backgroundColor: '#e8f5e9' },
  assistant: { alignSelf: 'flex-start', backgroundColor: '#f5f5f5' },
  inputRow: { flexDirection: 'row', padding: 8, gap: 8, alignItems: 'center', borderTopWidth: StyleSheet.hairlineWidth, borderColor: '#ddd' },
  input: { flex: 1, borderWidth: StyleSheet.hairlineWidth, borderColor: '#ccc', borderRadius: 6, paddingHorizontal: 10, height: 40 },
});


