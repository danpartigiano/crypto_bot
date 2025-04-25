/* eslint-disable */
import React, { createContext, useState, useEffect, useContext } from 'react';
import axios from 'axios';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const checkAuthStatus = async () => {
      try {
        const response = await axios.get('http://localhost:8000/user/info', {
          withCredentials: true,
        });
        if (response.status === 200) {
          setIsAuthenticated(true);
          setUser(response.data);
        } else {
          setIsAuthenticated(false);
          setUser(null);
        }
      } catch (error) {
        setIsAuthenticated(false);
        setUser(null);
      } finally {
        setIsLoading(false);
        setChecked(true);
      }
    };

    checkAuthStatus();
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      fetch("http://localhost:8000/user/refresh-token", {
        method: "GET",
        credentials: "include",
      })
        .then((res) => {
          if (!res.ok) {
            console.warn("Token refresh failed (bad response)");
            setIsAuthenticated(false);
            setUser(null);
          }
        })
        .catch((err) => {
          console.error("Server unreachable:", err);
          setIsAuthenticated(false);
          setUser(null);
        });
    }, 1 * 60 * 1000);

    return () => clearInterval(interval);
  }, []);

  const logout = async () => {
    try {
      await axios.post('http://localhost:8000/user/logout', {}, { withCredentials: true });
      setIsAuthenticated(false);
      setUser(null);
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        setIsAuthenticated,
        user,
        setUser,
        isLoading,
        checked,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
