import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants from 'expo-constants';
import { setBaseUrl, wireTokenStorage, Tokens } from '../src/api';

const BASE_URL = (Constants?.expoConfig?.extra as any)?.DJANGO_URL || process.env.DJANGO_URL || process.env.EXPO_PUBLIC_DJANGO_URL || '';
setBaseUrl(BASE_URL);

const TOKENS_KEY = 'auth_tokens_v1';

export async function getTokens(): Promise<Tokens | null> {
  const raw = await AsyncStorage.getItem(TOKENS_KEY);
  return raw ? (JSON.parse(raw) as Tokens) : null;
}

export async function setTokens(tokens: Tokens | null) {
  if (!tokens) return AsyncStorage.removeItem(TOKENS_KEY);
  return AsyncStorage.setItem(TOKENS_KEY, JSON.stringify(tokens));
}

wireTokenStorage(getTokens, setTokens);


