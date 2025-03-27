import React, { useState } from 'react';
import axios from 'axios';

function App() {
  const [tradeResult, setTradeResult] = useState(null);
  const [error, setError] = useState('');

  // For this example, assume you have a valid JWT access token stored in localStorage.
  // If not, replace the below line with a valid token string for testing.
  const token = localStorage.getItem('access_token') || 'YOUR_TEST_ACCESS_TOKEN';

  const getTradeDecision = async () => {
    try {
      // Call the /trade endpoint on your FastAPI backend.
      const response = await axios.post('http://127.0.0.1:8000/trade', {}, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      setTradeResult(response.data);
      setError('');
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'An error occurred.');
    }
  };

  return (
    <div style={{ padding: '20px', textAlign: 'center' }}>
      <h1>Crypto Bot Trade Decision</h1>
      <button onClick={getTradeDecision}>Get Trade Decision</button>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {tradeResult && (
        <div style={{ marginTop: '20px' }}>
          <h2>Decision: {tradeResult.decision}</h2>
          <p>Predicted Return: {tradeResult.predicted_return}</p>
          <p>Current Price: {tradeResult.current_price}</p>
          {tradeResult.trade_response && (
            <div>
              <h3>Trade Response:</h3>
              <pre>{JSON.stringify(tradeResult.trade_response, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;