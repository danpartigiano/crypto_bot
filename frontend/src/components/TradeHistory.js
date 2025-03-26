import React from 'react';

function TradeHistory() {
    const mockTrades = [
        { id: 1, cryptoPair: 'USD', amount: 1.2, results: 'Failed', date: '2024-01-01'},
        { id: 12, cryptoPair: 'USD', amount: 1.2, results: 'Failed', date: '2024-01-01'},
        { id: 2, cryptoPair: 'USD', amount: 1.2, results: 'Failed', date: '2024-01-01'},
    ];


    return (
        <div>
            <h2>Trade History</h2>
            <p>Find past trades here.</p>
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
                    {mockTrades.map((trade) => (
                        <tr key={trade.id}>
                            <td>{trade.cryptoPair}</td>
                            <td>{trade.amount}</td>
                            <td>{trade.results}</td>
                            <td>{trade.date}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

export default TradeHistory;