import React, { useState } from 'react';

function TradeExecution() {
    const [cryptoPair, setCryptoPair] = useState('');
    const [amount, setAmount] = useState('');

    const tradeOutput = (e) => {
        e.preventDefault();
        //Mock tade output
        if (!cryptoPair || !amount || parseFloat(amount) <= 0) {
            alert("Please enter a valid crypto pair and amount.");
            return;
        }
        alert(`Trading for ${cryptoPair} with amount ${amount}`);
    };


    return (
        <div>
            <h2>Trade Execution</h2>
            <form onSubmit={tradeOutput}>
                <div>
                    <label>Crypto Pair: </label>
                    <input
                        type="text"
                        value={cryptoPair}
                        onChange={ (e) => setCryptoPair(e.target.value)}
                        placeholder="e.g. USD"
                    />
                </div>
                <div>
                    <label>Amount: </label>
                    <input
                        type="text"
                        value={cryptoPair}
                        onChange={(e) => setCryptoPair(e.target.value.toUpperCase())}
                        placeholder="e.g. BTC/USD"
                    />
                </div>
                <button type="submit">Execute Trade</button>
            </form>
        </div>
    );
}

export default TradeExecution;