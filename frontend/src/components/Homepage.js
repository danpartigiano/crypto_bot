import React from 'react';
import { useNavigate } from 'react-router-dom';

function Homepage() {
  const navigate = useNavigate();

  return (
    <div className="full-page">
      <h1>Crypto Bot</h1>
      <button className="nav-button" onClick={() => navigate('/link-coinbase')}>Coinbase</button>
      <button className="nav-button" onClick={() => navigate('/dashboard')}>Real Time Data</button>
      <button className="nav-button" onClick={() => navigate('/trade')}>Trade Execution</button>
      <button className="nav-button" onClick={() => navigate('/history')}>Trade History</button>
      <button className="nav-button" onClick={() => navigate('/callback')}>Callback</button>
    </div>
  );
}

export default Homepage;