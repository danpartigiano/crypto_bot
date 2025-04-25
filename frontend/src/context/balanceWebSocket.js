import { useEffect, useRef, useState } from "react";

export default function useBalanceWebSocket() {
  const [balance, setBalance] = useState(null);
  const ws = useRef(null);
  const reconnectInterval = useRef(null);

  const connect = () => {
    // const token = localStorage.getItem("access_token");
    ws.current = new WebSocket(`ws://localhost:8000/coin/ws/balance`);

    ws.current.onopen = () => {
      console.log("WebSocket connected");
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setBalance(data.balance);
      console.log(data.balance);
    };

    ws.current.onerror = (err) => {
      console.error("WebSocket error:", err);
    };

    ws.current.onclose = () => {
      console.log("WebSocket closed. Reconnecting...");
      reconnectInterval.current = setTimeout(connect, 3000);
    };
  };

  useEffect(() => {
    connect();
    return () => {
      if (ws.current) ws.current.close();
      if (reconnectInterval.current) clearTimeout(reconnectInterval.current);
    };
  }, []);

  return balance;
}
