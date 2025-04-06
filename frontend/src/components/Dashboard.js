import React, { useEffect, useState } from 'react';
import { CategoryScale, Legend, LinearScale, LineElement, PointElement, Title, Tooltip, Filler } from 'chart.js';
import { Line } from 'react-chartjs-2';
import { Chart as ChartJS} from 'chart.js';
import Footer from './Footer';

ChartJS.register(Filler, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

function Dashboard() {
    const [priceData, setPriceData] = useState([]);
    const [labels, setLabels] = useState([]);
    const [userChoice, setuserChoice] = useState("BTC-USD");
    const [ws, setWs] = useState(null);

    const userOptions = [
        { label: "BTC-USD (Bitcoin)", value: "BTC-USD" },
        { label: "ETH-USD (Ethereum)", value: "ETH-USD" },
        { label: "LTC-USD (Litecoin)", value: "LTC-USD" },
        { label: "XRP-USD (Ripple)", value: "XRP-USD" },
        { label: "SOL-USD (Solana)", value: "SOL-USD" },
        { label: "MATIC-USD (Polygon)", value: "MATIC-USD" },
        { label: "DOGE-USD (Dogecoin)", value: "DOGE-USD" }
    ];

    useEffect(() => {
        const newWs = new WebSocket("wss://ws-feed.exchange.coinbase.com");
        setWs(newWs);

        newWs.onopen = () => {
            console.log("WebSocket Connected");

            const subscribeMessage = {
                type: "subscribe",
                channels: [
                    {
                        name: "ticker",
                        product_ids: [userChoice]
                    }
                ]
            };
            newWs.send(JSON.stringify(subscribeMessage));
        };

        return () => {
            if (newWs) newWs.close();
        };
    }, [userChoice]);

    useEffect(() => {
        if (!ws) return;

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.type === "ticker" && data.product_id === userChoice) {
                const newPrice = parseFloat(data.price);
                if (isNaN(newPrice)) {
                    console.error("Invalid price:", data.price);
                    return;
                }

                const timestamp = new Date().toLocaleTimeString();


                setPriceData(prevData => {
                    const updatedData = [...prevData, newPrice].slice(-20);
                    return updatedData;
                });

                setLabels(prevLabels => {

                    if (prevLabels[prevLabels.length - 1] !== timestamp) {
                        const updatedLabels = [...prevLabels, timestamp].slice(-10);
                        return updatedLabels;
                    }
                    return prevLabels;
                });
            }
        };

    }, [ws, userChoice]);

    const chartData = React.useMemo(() => ({
        labels: labels.length ? labels : ['Waiting for data...'],
        datasets: [
            {
                label: `${userChoice} Price `,
                data: priceData,
                borderColor: 'rgb(247, 241, 241)',
                backgroundColor: 'rgba(255, 251, 251, 0.2)',
                fill: true,
                pointBackgroundColor: 'white',
                pointBorderColor: 'black',
            }
        ]
    }), [labels, priceData, userChoice]);

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: {
                    color: 'white',
                }
            }
        },
        scales: {
            x: {
                title: { display: true, text: 'Time', color: 'white' },
                ticks: { color: 'white' },
                grid: { color: 'rgba(255, 255, 255, 0.2)' }
            },
            y: {
                title: { display: true, text: 'Price', color: 'white' },
                ticks: { color: 'white' },
                grid: { color: 'rgba(235, 232, 232, 0.2)' }
            }
        }
    };

    const userChange = (event) => {
        setuserChoice(event.target.value);
    };

    return (
        <div className="full-page">
            <h2>Real-time {userChoice} Price</h2>

            <select value={userChoice} onChange={userChange} style={{ marginBottom: '20px' }}>
                {userOptions.map(option => (
                    <option key={option.value} value={option.value}>
                        {option.label}
                    </option>
                ))}
            </select>

            <div style={{ width: '600px', height: '400px', backgroundColor: 'black', padding: '10px', borderRadius: '8px' }}>
                <Line key={priceData.length} data={chartData} options={chartOptions} />
            </div>

            <Footer />
        </div>
    );
}

export default Dashboard;