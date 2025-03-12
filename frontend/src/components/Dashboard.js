import { CategoryScale, Legend, LinearScale, LineElement, PointElement, Title, Tooltip } from 'chart.js';
import React from 'react';
//Use charts to show real time data
import { Line } from 'react-chartjs-2';
import { Chart as ChartJS} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

function Dashboard() {
    //Replace with real data later
    const mockData = {
        labels: ['2024-01-01', '2024-01-05', '2024-01-20'],
        datasets: [
            {
                label: 'Real Time MockData',
                data: [2000, 2030, 2040],
                //line color
                borderColor: 'rgba(75, 192, 192, 1)',
                //background color
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                fill: true,
            }
        ]
    }
    const labelValues = {
        scales: {
            x: {
                title: {
                    display: true,
                    text: 'Date',
                }
            },
            y: {
                title: {
                    display: true,
                    text: 'Price',
                }
            }
        }

    };


    return (
        <div>
            <h2>Dashboard</h2>
            <p>This is the Dashboard.</p>

            <div style={{ width: '600px', height: '400px'}}>
                <Line data={mockData} options={labelValues} />
            </div>
        </div>
    );
}

export default Dashboard;