// src/App.js
import './App.css';
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Homepage from './components/Homepage';
import Dashboard from './components/Dashboard';
import TradeExecution from './components/TradeExecution';
import TradeHistory from './components/TradeHistory';
import LinkCoinbase from './components/LinkCoinbase';
import Login from './components/Login';
import SignUp from './components/Signup';
import { useAuth } from './context/AuthContext';

function App() {
  const { isAuthenticated } = useAuth();

  return (
    <Router>
      <div className="App">
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<Homepage />} />
          <Route path="/login" element={isAuthenticated ? <Navigate to="/" /> : <Login />} />
          <Route path="/signup" element={isAuthenticated ? <Navigate to="/dashboard" /> : <SignUp />} />

          {/* Protected Routes */}
          <Route
            path="/dashboard"
            element={isAuthenticated ? <Dashboard /> : <Navigate to="/login" />}
          />
          <Route
            path="/trade"
            element={isAuthenticated ? <TradeExecution /> : <Navigate to="/login" />}
          />
          <Route
            path="/history"
            element={isAuthenticated ? <TradeHistory /> : <Navigate to="/login" />}
          />
          <Route
            path="/link-coinbase"
            element={isAuthenticated ? <LinkCoinbase /> : <Navigate to="/login" />}
          />
        </Routes>
      </div>
    </Router>
  );
}

export default App;

