import React, { useEffect, useState } from 'react';
import { CategoryScale, Legend, LinearScale, LineElement, PointElement, Title, Tooltip, Filler } from 'chart.js';
//Use charts to show real time data
import { Line } from 'react-chartjs-2';
import { Chart as ChartJS} from 'chart.js';
import Footer from './Footer';

ChartJS.register(Filler, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

function Dashboard() {
    const [priceData, setPriceData] = useState([]);
    const [labels, setLabels] = useState([]);

    useEffect(() => {
        const ws = new WebSocket("ws://localhost:8000/ws/solana");

        ws.onopen = () => console.log("WebSocket Connected");
        ws.onerror = (error) => console.error("WebSocket Error:", error);
        ws.onclose = () => console.warn("WebSocket Disconnected");

        ws.onmessage = (event) => {
            console.log("Received data:", event.data);
            const newPrice = parseFloat(event.data);
            if (isNaN(newPrice)) {
                console.error("Invalid price:", event.data);
                return;
            }

            const timestamp = new Date().toLocaleTimeString();

            setPriceData(prevData => {
                const updatedData = [...prevData, newPrice].slice(-20);
                console.log("Updated priceData:", updatedData);
                return updatedData;
            });

            setLabels(prevLabels => {
                const updatedLabels = [...prevLabels, timestamp].slice(-20);
                console.log("Updated labels:", updatedLabels);
                return updatedLabels;
            });
        };

        return () => ws.close();
    }, []);

    const chartData = React.useMemo(() => ({
        labels: labels.length ? labels : ['Waiting for data...'],
        datasets: [
            {
                label: 'Solana Price (USD)',
                data: priceData,
                borderColor: 'rgb(247, 241, 241)',
                backgroundColor: 'rgba(255, 251, 251, 0.2)',
                fill: true,
                pointBackgroundColor: 'white',
                pointBorderColor: 'black',
            }
        ]
    }), [labels, priceData]);

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
                title: { display: true, text: 'Price (USD)', color: 'white' },
                ticks: { color: 'white' },
                grid: { color: 'rgba(235, 232, 232, 0.2)' }
            }
        }
    };

    return (
        <div className="full-page">
            <h2>Dashboard</h2>
            <p>Real-time Solana Price.</p>

            <div style={{ width: '600px', height: '400px', backgroundColor: 'black', padding: '10px', borderRadius: '8px' }}>
                <Line key={priceData.length} data={chartData} options={chartOptions} />
            </div>

            <Footer />
        </div>
    );
}

export default Dashboard;