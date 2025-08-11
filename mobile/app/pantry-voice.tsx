import { useState } from 'react';
import { View, Text, Button, StyleSheet, Platform } from 'react-native';
import * as DocumentPicker from 'expo-document-picker';
import Constants from 'expo-constants';

export default function PantryVoiceScreen() {
  const [status, setStatus] = useState<string>('');

  const pickAndUpload = async () => {
    setStatus('');
    const result = await DocumentPicker.getDocumentAsync({ type: 'audio/*', copyToCacheDirectory: true });
    if (result.canceled || !result.assets?.length) return;
    const asset = result.assets[0];
    try {
      const backend = (Constants?.expoConfig?.extra as any)?.DJANGO_URL || process.env.EXPO_PUBLIC_DJANGO_URL;
      const form = new FormData();
      // @ts-ignore FormData for RN accepts uri/name/type
      form.append('audio_file', { uri: asset.uri, name: asset.name || 'audio.wav', type: asset.mimeType || 'audio/wav' });

      const resp = await fetch(`${backend}/meals/api/pantry-items/from-audio/`, {
        method: 'POST',
        body: form,
        headers: { 'Accept': 'application/json' },
        credentials: 'include',
      });
      const text = await resp.text();
      setStatus(`HTTP ${resp.status}: ${text.slice(0, 500)}`);
      console.log('from-audio response:', resp.status, text);
    } catch (e: any) {
      setStatus(`Error: ${e?.message}`);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Pantry Voice Upload</Text>
      <Button title="Pick audio and upload" onPress={pickAndUpload} />
      {status ? <Text style={{ marginTop: 12 }}>{status}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 12 },
  title: { fontSize: 22, fontWeight: '600', marginBottom: 8 },
});


