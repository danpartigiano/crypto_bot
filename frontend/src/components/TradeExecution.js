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
                body: JSON.stringify({ cryptoPair, amount: parseFloat(amount) }),
            });

            const data = await response.json();
            setMessage(`Trade Status: ${data.status}`);
        } catch (error) {
            setMessage("Try again, error trying to execute trade.");
        } finally {
            setLoading(false);
        }
    };


    return (
        <div>
            <h2>Trade Execution</h2>
            <form onSubmit={tradeOutPut}>
                <div>
                    <label>Crypto Pair: </label>
                    <input
                        type="text"
                        value={cryptoPair}
                        onChange={ (e) => setCryptoPair(e.target.value)}
                        placeholder="e.g. SOL/USD"
                        required
                    />
                </div>
                <div>
                    <label>Amount: </label>
                    <input
                        type="number"
                        value={amount}
                        onChange={(e) => setAmount(e.target.value)}
                        placeholder="Amount being traded"
                        required
                    />
                </div>
                <button type="Submit" disabled={loading}>
                    {loading ? "Executing..." : "Execute Trade"}
                </button>
            </form>
            {message && <p>{message}</p>}
        </div>
    );
}

export default TradeExecution;