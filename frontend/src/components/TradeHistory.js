import React, { useEffect, useState } from 'react';

function TradeHistory() {
    const [trades, setTrades] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch("http://localhost:8000/api/trades")
            .then(res => res.json())
            .then(data => {
                setTrades(data);
                setLoading(false);
            })
            .catch(error => {
                console.error("Error trying to get trade history:", error);
                setLoading(false);
            });
    }, []);

    return (
        <div>
            <h2>Trade History</h2>
            {loading ? <p>Loading...</p> : (
            <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '10px '}}>
                <thead>
                    <tr>
                        <th>Crypto Pair</th>
                        <th>Amount</th>
                        <th>Results</th>
                        <th>Date</th>
                    </tr>
                </thead>
                <tbody>
                    {trades.map((trade, index) => (
                        <tr key={trade.id}>
                            <td>{trade.cryptoPair}</td>
                            <td>{trade.amount}</td>
                            <td>{trade.results}</td>
                            <td>{trade.date}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
            )}
        </div>
    );
}

export default TradeHistory;