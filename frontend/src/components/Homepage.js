import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

function Homepage() {
  const navigate = useNavigate();
  const { isAuthenticated, logout } = useAuth();

  return (
    <div className="full-page">
      <h1>Crypto Bot</h1>

      {/* Authenticated User Buttons */}
      {isAuthenticated ? (
        <>
          <button className="nav-button" onClick={() => navigate('/link-coinbase')}>
            Coinbase
          </button>
          <button className="nav-button" onClick={() => navigate('/dashboard')}>
            Real Time Data
          </button>
          <button className="nav-button" onClick={() => navigate('/trade')}>
            Trade Execution
          </button>
          <button className="nav-button" onClick={() => navigate('/history')}>
            Trade History
          </button>
          <button className="nav-button logout-btn" onClick={logout}>
            Logout
          </button>
        </>
      ) : (
        // Unauthenticated User Buttons
        <>
          <button className="nav-button" onClick={() => navigate('/login')}>
            Login
          </button>
        </>
      )}
    </div>
  );
}

export default Homepage;
