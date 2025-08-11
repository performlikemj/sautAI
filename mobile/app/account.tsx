import { useState } from 'react';
import { View, StyleSheet } from 'react-native';
import { Text, TextInput, Button, Card } from 'react-native-paper';
import { login as apiLogin, UserInfo } from '../src/api';
import { setTokens } from './_state';

export default function AccountScreen() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [user, setUser] = useState<UserInfo | null>(null);

  const handleLogin = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiLogin(username, password);
      await setTokens({ access: res.access, refresh: res.refresh });
      setUser(res);
    } catch (e: any) {
      setError(e?.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Card>
        <Card.Title title="Account" subtitle={user ? 'Signed in' : 'Sign in to continue'} />
        <Card.Content>
          {user ? (
            <Text>Welcome, {user.username}</Text>
          ) : (
            <View style={{ gap: 12 }}>
              <TextInput label="Username" value={username} onChangeText={setUsername} autoCapitalize="none" />
              <TextInput label="Password" value={password} onChangeText={setPassword} secureTextEntry />
              {error && <Text style={{ color: 'red' }}>{error}</Text>}
              <Button mode="contained" onPress={handleLogin} loading={loading} disabled={loading}>Sign in</Button>
            </View>
          )}
        </Card.Content>
      </Card>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 12 },
  title: { fontSize: 22, fontWeight: '600', marginBottom: 8 },
});


