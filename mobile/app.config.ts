import type { ExpoConfig } from '@expo/config';
import { config as loadEnv } from 'dotenv';
import path from 'path';

// Load the repo root .env so we can use DJANGO_URL and STREAMLIT_URL
loadEnv({ path: path.resolve(__dirname, '../.env') });

const base = require('./app.json');

const expoConfig: ExpoConfig = {
  ...base.expo,
  extra: {
    ...(base.expo?.extra || {}),
    // Prefer .env values; fallback to any existing values
    DJANGO_URL: process.env.DJANGO_URL || base.expo?.extra?.DJANGO_URL,
    STREAMLIT_URL: process.env.STREAMLIT_URL || base.expo?.extra?.STREAMLIT_URL,
  },
};

export default expoConfig;


