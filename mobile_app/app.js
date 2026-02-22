// ─────────────────────────────────────────────────────────
// App.js — Beside Her Mobile
// Root component with navigation
// ─────────────────────────────────────────────────────────

import React from 'react';
import { StatusBar, ActivityIndicator, View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';

import { AuthProvider, useAuth } from './src/context/AuthContext';
import { colors } from './src/theme';

// Screens
import LoginScreen from './src/screens/LoginScreen';
import SignupScreen from './src/screens/SignupScreen';
import MomCheckinScreen from './src/screens/MomCheckinScreen';
import MomHistoryScreen from './src/screens/MomHistoryScreen';
import PartnerDashboardScreen from './src/screens/PartnerDashboardScreen';
import PartnerChatScreen from './src/screens/PartnerChatScreen';
import WeeklyReportScreen from './src/screens/WeeklyReportScreen';

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

// ── Header with Logout ───────────────────────────────────
function LogoutButton() {
  const { logout } = useAuth();
  return (
    <TouchableOpacity onPress={logout} style={{ paddingHorizontal: 12 }}>
      <Text style={{ color: colors.plum, fontSize: 14, fontWeight: '500' }}>Logout</Text>
    </TouchableOpacity>
  );
}

const screenOptions = {
  headerStyle: { backgroundColor: colors.background },
  headerTintColor: colors.textPrimary,
  headerTitleStyle: { fontWeight: '600' },
  headerShadowVisible: false,
  headerRight: () => <LogoutButton />,
};

// ── Mom Tab Navigator ────────────────────────────────────
function MomTabs() {
  return (
    <Tab.Navigator
      screenOptions={{
        ...screenOptions,
        tabBarStyle: {
          backgroundColor: colors.surface,
          borderTopColor: colors.border,
          paddingBottom: 4,
          height: 56,
        },
        tabBarActiveTintColor: colors.plum,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarLabelStyle: { fontSize: 12, fontWeight: '500' },
      }}
    >
      <Tab.Screen
        name="Check In"
        component={MomCheckinScreen}
        options={{
          headerTitle: 'Beside Her',
          tabBarIcon: ({ color }) => <Text style={{ fontSize: 20 }}>🌸</Text>,
        }}
      />
      <Tab.Screen
        name="My Journey"
        component={MomHistoryScreen}
        options={{
          tabBarIcon: ({ color }) => <Text style={{ fontSize: 20 }}>📊</Text>,
        }}
      />
    </Tab.Navigator>
  );
}

// ── Partner Tab Navigator ────────────────────────────────
function PartnerTabs() {
  return (
    <Tab.Navigator
      screenOptions={{
        ...screenOptions,
        tabBarStyle: {
          backgroundColor: colors.surface,
          borderTopColor: colors.border,
          paddingBottom: 4,
          height: 56,
        },
        tabBarActiveTintColor: colors.plum,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarLabelStyle: { fontSize: 12, fontWeight: '500' },
      }}
    >
      <Tab.Screen
        name="Dashboard"
        component={PartnerDashboardScreen}
        options={{
          headerTitle: 'Beside Her',
          tabBarIcon: () => <Text style={{ fontSize: 20 }}>🏠</Text>,
        }}
      />
      <Tab.Screen
        name="Ask AI"
        component={PartnerChatScreen}
        options={{
          tabBarIcon: () => <Text style={{ fontSize: 20 }}>💬</Text>,
        }}
      />
      <Tab.Screen
        name="Weekly"
        component={WeeklyReportScreen}
        options={{
          tabBarIcon: () => <Text style={{ fontSize: 20 }}>📋</Text>,
        }}
      />
    </Tab.Navigator>
  );
}

// ── Auth Stack ───────────────────────────────────────────
function AuthStack() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: colors.background },
        headerTintColor: colors.textPrimary,
        headerShadowVisible: false,
        headerTitle: '',
      }}
    >
      <Stack.Screen name="Login" component={LoginScreen} options={{ headerShown: false }} />
      <Stack.Screen name="Signup" component={SignupScreen} />
    </Stack.Navigator>
  );
}

// ── Root Navigator ───────────────────────────────────────
function RootNavigator() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <View style={styles.loading}>
        <Text style={styles.loadingLogo}>Beside Her</Text>
        <ActivityIndicator size="large" color={colors.plum} />
      </View>
    );
  }

  if (!user) return <AuthStack />;
  if (user.role === 'mom') return <MomTabs />;
  return <PartnerTabs />;
}

// ── App Entry Point ──────────────────────────────────────
export default function App() {
  return (
    <AuthProvider>
      <NavigationContainer>
        <StatusBar barStyle="dark-content" backgroundColor={colors.background} />
        <RootNavigator />
      </NavigationContainer>
    </AuthProvider>
  );
}

const styles = StyleSheet.create({
  loading: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.background,
  },
  loadingLogo: {
    fontSize: 28,
    fontWeight: '800',
    color: colors.plum,
    marginBottom: 24,
  },
});
