import React from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { NavProvider } from './context/NavContext';
import { Layout } from './components/Layout';
import { Login } from './pages/Login';

const AppShell: React.FC = () => {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-navy-900 text-slate-400">
        Loading...
      </div>
    );
  }

  if (!user) {
    return <Login />;
  }

  return (
    <NavProvider>
      <Layout />
    </NavProvider>
  );
};

function App() {
  return (
    <AuthProvider>
      <AppShell />
    </AuthProvider>
  );
}

export default App;
