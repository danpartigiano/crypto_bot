import React, { useState } from 'react';

function TradeExecution() {
    const [cryptoPair, setCryptoPair] = useState('');
    const [amount, setAmount] = useState('');
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState('');

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
                setMessage(`Error: ${result.detail || 'Something went wrong'}`);
            }
        } catch (error) {
            setMessage(`Error: ${error.message}`);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div>
            <h2>Trade Execution</h2>
            <form onSubmit={tradeOutPut}>
                <div>
                    <label htmlFor="cryptoPair">Crypto Pair:</label>
                    <input
                        type="text"
                        id="cryptoPair"
                        value={cryptoPair}
                        onChange={(e) => setCryptoPair(e.target.value)}
                        required
                    />
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
        </div>
    );
}

export default TradeExecution;