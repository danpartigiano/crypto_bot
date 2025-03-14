import React, { useEffect, useState } from 'react';
import { CategoryScale, Legend, LinearScale, LineElement, PointElement, Title, Tooltip } from 'chart.js';
//Use charts to show real time data
import { Line } from 'react-chartjs-2';
import { Chart as ChartJS} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

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
            const timestamp = new Date().toLocaleTimeString();

            setPriceData(prevData => [...prevData.slice(-20), newPrice]);
            setLabels(prevLabels => [...prevLabels.slice(-20), timestamp]);

            
        };

        

        return () => ws.close();
    }, []);

    
    const chartData = {
        labels: labels,
        datasets: [
            {
                label: 'Solana Price (USD)',
                data: priceData,
                borderColor: 'rgba(75, 192, 192, 1)',
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                fill: true,
            }
        ]
    };

    const chartOptions = {
        scales: {
            x: {
                title: {display: true, text: 'Time' },
            },
            y: {
                title: { display: true, text: 'Price (USD)' },
            }
        }
    };


    return (
        <div>
            <h2>Dashboard</h2>
            <p>Real-time Solana Price.</p>

            <div style={{ width: '600px', height: '400px'}}>
                <Line data={chartData} options={chartOptions} />
            </div>
        </div>
    );
}

export default Dashboard;