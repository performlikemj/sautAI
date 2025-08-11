import { Tabs } from 'expo-router';
import { Provider as PaperProvider, MD3LightTheme } from 'react-native-paper';

export default function RootLayout() {
  return (
    <PaperProvider theme={MD3LightTheme}>
      <Tabs
        screenOptions={{
          headerShown: false,
          tabBarActiveTintColor: '#2e7d32',
        }}
      >
        <Tabs.Screen name="assistant" options={{ title: 'Assistant', href: '/assistant' }} />
        <Tabs.Screen name="meal-plans" options={{ title: 'Meal Plans', href: '/meal-plans' }} />
        <Tabs.Screen name="pantry" options={{ title: 'Pantry', href: '/pantry' }} />
        <Tabs.Screen name="pantry-voice" options={{ title: 'Voice', href: '/pantry-voice' }} />
        <Tabs.Screen name="history" options={{ title: 'History', href: '/history' }} />
        <Tabs.Screen name="profile" options={{ title: 'Profile', href: '/profile' }} />
        <Tabs.Screen name="account" options={{ title: 'Account', href: '/account' }} />
        <Tabs.Screen name="chef" options={{ title: 'Chef', href: '/chef' }} />
        <Tabs.Screen name="summary" options={{ title: 'Summary', href: '/summary' }} />
      </Tabs>
    </PaperProvider>
  );
}


