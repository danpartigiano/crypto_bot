import React, { useState, useEffect } from 'react';
import Footer from './Footer';

function TradeExecution() {

    const [cryptoPair, setCryptoPair] = useState('');
    const [amount, setAmount] = useState('');
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [availablePairs, setAvailablePairs] = useState([]);

    
    useEffect(() => {
        const fetchPairs = async () => {
            try {
                const response = await fetch("http://localhost:8000/api/pairs");
                if (!response.ok) throw new Error("Backend not available");
                
                const data = await response.json();
                setAvailablePairs(data.pairs); //waiting for backend
            } catch (error) {
                console.error("Error fetching pairs:", error);
                //sample values until backend is done
                setAvailablePairs(["USD"]);
            }
        };

        fetchPairs();
    }, []);

    const tradeOutPut = async (e) => {
        e.preventDefault();
        setLoading(true);
        setMessage('');

        try {
            const response = await fetch("http://localhost:8000/api/trade", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ cryptoPair, amount })
            });

            const result = await response.json();

            if (response.ok) {
                setMessage(`Trade status: ${result.status}`);
            } else {
                setMessage(`Error: ${result.detail || 'Error'}`);
            }
        } catch (error) {
            setMessage(`Error: ${error.message}`);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="full-page">
            <h2>Trade Execution</h2>
            <form onSubmit={tradeOutPut}>
                <div>
                    <label htmlFor="cryptoPair">Crypto Pair:</label>
                    <select
                        id="cryptoPair"
                        value={cryptoPair}
                        onChange={(e) => setCryptoPair(e.target.value)}
                        required
                    >
                        <option value="">Select a Pair</option>
                        {availablePairs.map((pair) => (
                            <option key={pair} value={pair}>{pair}</option>
                        ))}
                    </select>
                </div>
                <div>
                    <label htmlFor="amount">Amount:</label>
                    <input
                        type="number"
                        id="amount"
                        value={amount}
                        onChange={(e) => setAmount(e.target.value)}
                        required
                        min="0.01"
                        step="0.01"
                    />
                </div>
                <button type="submit" disabled={loading}>
                    {loading ? 'Processing...' : 'Execute Trade'}
                </button>
            </form>
            {message && <p>{message}</p>}
            <Footer />
        </div>
    );
}

export default TradeExecution;