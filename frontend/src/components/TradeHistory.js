import React, { useEffect, useState } from 'react';
import Footer from './Footer';

function TradeHistory() {
    const [trades, setTrades] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch("http://localhost:8000/api/trades")
            .then(res => res.json())
            .then(data => {
                console.log("Received trade data:", data);
                if (Array.isArray(data)) {
                    setTrades(data);
                } else {
                    console.error("Expected an array, but got:", data);
                    setTrades([]);
                }
                setLoading(false);
            })
            .catch(error => {
                console.error("Error trying to get trade history:", error);
                setLoading(false);
            });
    }, []);

    return (
        <div className="full-page">
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
                        {trades.length > 0 ? (
                            trades.map((trade) => (
                                <tr key={trade.id}>
                                    <td>{trade.cryptoPair}</td>
                                    <td>{trade.amount}</td>
                                    <td>{trade.results}</td>
                                    <td>{trade.date}</td>
                                </tr>
                            ))
                        ) : (
                            <tr><td colSpan="4">No trade history available.</td></tr>
                        )}
                    </tbody>
                </table>
            )}
            <Footer />
        </div>
    );
}

export default TradeHistory;