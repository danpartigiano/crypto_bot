import React from 'react';
import { useNavigate } from 'react-router-dom';

function Homepage() {
  const navigate = useNavigate();

  return (
    <div className="full-page">
      <h1>Crypto Bot</h1>
      <button className="nav-button" onClick={() => navigate('/dashboard')}>Dashboard</button>
      <button className="nav-button" onClick={() => navigate('/trade')}>Trade Execution</button>
      <button className="nav-button" onClick={() => navigate('/history')}>Trade History</button>
      <button className="nav-button" onClick={() => navigate('/link-coinbase')}>Link Coinbase</button>
    </div>
  );
}

export default Homepage;