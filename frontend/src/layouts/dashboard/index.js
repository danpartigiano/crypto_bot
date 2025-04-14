/* eslint-disable */
import React, { useEffect, useState } from "react";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  BarElement,
} from "chart.js";

import Grid from "@mui/material/Grid";
import Card from "@mui/material/Card";
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import DashboardLayout from "examples/LayoutContainers/DashboardLayout";
import DashboardNavbar from "examples/Navbars/DashboardNavbar";
import Footer from "examples/Footer";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  BarElement
);

const granularityOptions = [
  { label: "1 min", value: 60 },
  { label: "5 min", value: 300 },
  { label: "15 min", value: 900 },
  { label: "1 hour", value: 3600 },
  { label: "1 day", value: 86400 },
];

function Dashboard() {
  const [coinOptions, setCoinOptions] = useState([]);
  const [selectedCoin, setSelectedCoin] = useState("");
  const [granularity, setGranularity] = useState(60);
  const [chartData, setChartData] = useState({ labels: [], datasets: [] });

  const fetchCoinOptions = async () => {
    try {
      const res = await fetch("https://api.exchange.coinbase.com/products");
      const data = await res.json();
      const usdPairs = data
        .filter((item) => item.quote_currency === "USD")
        .map((item) => ({ label: item.base_currency, id: item.id }));
      setCoinOptions(usdPairs);
      if (usdPairs.length > 0) setSelectedCoin(usdPairs[0].id);
    } catch (err) {
      console.error("Failed to fetch coin options:", err);
    }
  };

  const fetchCandleData = async (coinId, granularity) => {
    try {
      const response = await fetch(
        `https://api.exchange.coinbase.com/products/${coinId}/candles?granularity=${granularity}`
      );
      const data = await response.json();

      if (!Array.isArray(data)) throw new Error("Invalid response from Coinbase");

      const sorted = data.sort((a, b) => a[0] - b[0]);

      const labels = [];
      const closes = [];
      const volumes = [];
      const highs = [];
      const lows = [];

      sorted.forEach(([timestamp, low, high, , close, volume]) => {
        const date = new Date(timestamp * 1000);
        const label =
          granularity >= 86400
            ? `${date.getFullYear()}-${date.getMonth() + 1}-${date.getDate()}`
            : `${date.getHours()}:${String(date.getMinutes()).padStart(2, "0")}`;
        labels.push(label);
        closes.push(close);
        volumes.push(volume);
        highs.push(high);
        lows.push(low);
      });

      const sma = closes.map((_, i, arr) => {
        if (i < 9) return null;
        const slice = arr.slice(i - 9, i + 1);
        const avg = slice.reduce((a, b) => a + b, 0) / slice.length;
        return avg;
      });

      const maxPrice = Math.max(...highs);
      const minPrice = Math.min(...lows);

      setChartData({
        labels,
        datasets: [
          {
            type: "line",
            label: `${coinId} Price`,
            data: closes,
            borderColor: "rgba(255,255,255,0.9)",
            backgroundColor: "rgba(255,255,255,0.2)",
            fill: true,
            tension: 0.4,
            pointRadius: 0,
            yAxisID: "y",
          },
          {
            type: "line",
            label: "SMA (10)",
            data: sma,
            borderColor: "#00ffcc",
            borderDash: [5, 5],
            fill: false,
            tension: 0.2,
            pointRadius: 0,
            yAxisID: "y",
          },
          {
            type: "bar",
            label: "Volume",
            data: volumes,
            backgroundColor: "rgba(0, 123, 255, 0.4)",
            yAxisID: "y1",
          },
          {
            type: "line",
            label: `High (${maxPrice.toFixed(2)})`,
            data: Array(labels.length).fill(maxPrice),
            borderColor: "rgba(255,0,0,0.5)",
            borderWidth: 1,
            borderDash: [4, 4],
            pointRadius: 0,
            fill: false,
            yAxisID: "y",
          },
          {
            type: "line",
            label: `Low (${minPrice.toFixed(2)})`,
            data: Array(labels.length).fill(minPrice),
            borderColor: "rgba(0,255,0,0.5)",
            borderWidth: 1,
            borderDash: [4, 4],
            pointRadius: 0,
            fill: false,
            yAxisID: "y",
          },
        ],
      });
    } catch (err) {
      console.error("Fetch error:", err);
    }
  };

  useEffect(() => {
    fetchCoinOptions();
  }, []);

  useEffect(() => {
    if (!selectedCoin) return;

    fetchCandleData(selectedCoin, granularity);

    const refreshMap = {
      60: 10000,
      300: 30000,
      900: 60000,
      3600: 5 * 60000,
      86400: 15 * 60000,
    };

    const interval = setInterval(() => {
      fetchCandleData(selectedCoin, granularity);
    }, refreshMap[granularity]);

    return () => clearInterval(interval);
  }, [selectedCoin, granularity]);

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { labels: { color: "white" } },
      tooltip: {
        enabled: true,
        mode: "index",
        intersect: false,
        backgroundColor: "#222",
        titleColor: "#fff",
        bodyColor: "#ddd",
        borderColor: "#555",
        borderWidth: 1,
        titleFont: { weight: "bold" },
        callbacks: {
          label: function (context) {
            const val = context.parsed.y;
            return `${context.dataset.label}: $${val?.toFixed(2)}`;
          },
        },
      },
    },
    scales: {
      x: {
        title: { display: true, text: "Time", color: "white" },
        ticks: { color: "white", maxTicksLimit: 12 },
        grid: { color: "rgba(255,255,255,0.2)" },
      },
      y: {
        position: "left",
        title: { display: true, text: "Price (USD)", color: "white" },
        ticks: { color: "white" },
        grid: { color: "rgba(255,255,255,0.2)" },
      },
      y1: {
        position: "right",
        title: { display: true, text: "Volume", color: "white" },
        ticks: { color: "white" },
        grid: { drawOnChartArea: false },
      },
    },
  };

  return (
    <DashboardLayout>
      <DashboardNavbar />
      <MDBox py={3}>
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Card sx={{ backgroundColor: "#1a1a1a", p: 3 }}>
              <MDTypography variant="h5" color="white" gutterBottom>
                Coinbase Candle Chart (Price + SMA + Volume)
              </MDTypography>

              <MDBox mb={2} display="flex" gap={2}>
                <select
                  value={selectedCoin}
                  onChange={(e) => setSelectedCoin(e.target.value)}
                  style={{
                    backgroundColor: "#2e2e2e",
                    color: "white",
                    padding: "8px 12px",
                    borderRadius: "6px",
                    border: "1px solid #444",
                  }}
                >
                  {coinOptions.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label}
                    </option>
                  ))}
                </select>

                <select
                  value={granularity}
                  onChange={(e) => setGranularity(Number(e.target.value))}
                  style={{
                    backgroundColor: "#2e2e2e",
                    color: "white",
                    padding: "8px 12px",
                    borderRadius: "6px",
                    border: "1px solid #444",
                  }}
                >
                  {granularityOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </MDBox>

              <MDBox height="400px">
                <Line data={chartData} options={chartOptions} />
              </MDBox>
            </Card>
          </Grid>
        </Grid>
      </MDBox>
      <Footer />
    </DashboardLayout>
  );
}

export default Dashboard;
