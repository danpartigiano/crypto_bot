import './App.css';
import { NavLink } from 'react-router-dom';

import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link} from 'react-router-dom';
import Dashboard from './components/Dashboard';
import TradeExecution from './components/TradeExecution';
import TradeHistory from './components/TradeHistory';
import LinkCoinbase from './components/LinkCoinbase';

function App() {
  return (
    <Router>
      <div className="App">
        <header className="App-header">
          <h1>Crypto Bot</h1>
          <nav>
            <ul>
            <li><NavLink to="/" activeClassName="active">Dashboard</NavLink></li>
            <li><NavLink to="/trade" activeClassName="active">Trade Execution</NavLink></li>
            <li><NavLink to="/history" activeClassName="active">Trade History</NavLink></li>
            <li>
            <NavLink to="/link-coinbase" className={({ isActive }) => (isActive ? "active" : "")}>
              Link Coinbase
            </NavLink>
          </li>
            </ul>
          </nav>
        </header>

        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/trade" element={<TradeExecution />} />
          <Route path="/history" element={<TradeHistory />} />
          <Route path="/link-coinbase" element={<LinkCoinbase />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
