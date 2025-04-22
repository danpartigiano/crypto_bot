/* eslint-disable */

import React, { createContext, useState, useEffect, useContext } from 'react';
import axios from 'axios';

// Create Auth Context
const AuthContext = createContext();

// Auth Provider Component
export const AuthProvider = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);

  // Check if user is authenticated on app load
  useEffect(() => {
    const checkAuthStatus = async () => {
      try {
        const response = await axios.get('http://localhost:8000/user/info', {
          withCredentials: true,
        });
        if (response.status === 200) {
          setIsAuthenticated(true);
          setUser(response.data);
        }
      } catch (error) {
        setIsAuthenticated(false);
        setUser(null);
      }
    };

    checkAuthStatus();
  }, []);

  // Refresh token periodically (every 10 min)
  useEffect(() => {
    const interval = setInterval(() => {
      fetch("http://localhost:8000/user/refresh-token", {
        method: "GET",
        credentials: "include",
      }).then((res) => {
        if (!res.ok) {
          console.warn("Token refresh failed");
          setIsAuthenticated(false);
        }
      });
    }, 10 * 60 * 1000);

    return () => clearInterval(interval);
  }, []);

  // Logout function to clear cookies and update state
  const logout = async () => {
    try {
      await axios.post('http://localhost:8000/user/logout', {}, { withCredentials: true });
      setIsAuthenticated(false);
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, setIsAuthenticated, user, setUser, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

// Custom hook to use Auth Context
export const useAuth = () => useContext(AuthContext);
