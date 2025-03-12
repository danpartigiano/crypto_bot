import React, { useState } from 'react';

function TradeExecution() {
    const [cryptoPair, setCryptoPair] = useState('');
    const [amount, setAmount] = useState('');

    const tradeOutPut = (e) => {
        e.preventDefault();
        //Mock tade output
        alert(`Trading for ${cryptoPair} with amount ${amount}`);
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
                        placeholder="e.g. USD"
                    />
                </div>
                <div>
                    <label>Amount: </label>
                    <input
                        type="number"
                        value={amount}
                        onChange={(e) => setAmount(e.target.value)}
                        placeholder="Amount being traded"
                    />
                </div>
                <button type="submit">Execute Trade</button>
            </form>
        </div>
    );
}

export default TradeExecution;