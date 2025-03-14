import './App.css';

import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link} from 'react-router-dom';
import Dashboard from './components/Dashboard';
import TradeExecution from './components/TradeExecution';
import TradeHistory from './components/TradeHistory';

function App() {
  return (
    <Router>
      <div className="App">
        <header className="App-header">
          <h1>Crypto Bot</h1>
          <nav>
            <ul>
              <li><Link to ="/">Dashboard</Link></li>
              <li><Link to ="/trade">Trade Execution</Link></li>
              <li><Link to ="/history">Trade History</Link></li>
            </ul>
          </nav>
        </header>

        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/trade" element={<TradeExecution />} />
          <Route path="/history" element={<TradeHistory />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
