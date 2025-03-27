import './App.css';
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Homepage from './components/Homepage';
import Dashboard from './components/Dashboard';
import TradeExecution from './components/TradeExecution';
import TradeHistory from './components/TradeHistory';
import LinkCoinbase from './components/LinkCoinbase';

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<Homepage />} />  
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/trade" element={<TradeExecution />} />
          <Route path="/history" element={<TradeHistory />} />
          <Route path="/link-coinbase" element={<LinkCoinbase />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;