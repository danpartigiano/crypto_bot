/* eslint-disable */
import { useAuth } from "context/AuthContext";
import { Navigate } from "react-router-dom";
import { useEffect, useRef, useState } from "react";

// @mui material components
import Grid from "@mui/material/Grid";
import Card from "@mui/material/Card";
import Button from "@mui/material/Button";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import InputLabel from "@mui/material/InputLabel";
import FormControl from "@mui/material/FormControl";
import CircularProgress from "@mui/material/CircularProgress";

// Material Dashboard 2 React components
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";

// Material Dashboard 2 React examples
import DashboardLayout from "examples/LayoutContainers/DashboardLayout";
import DashboardNavbar from "examples/Navbars/DashboardNavbar";
import Footer from "examples/Footer";

function Trade() {
  const { isAuthenticated, user, isLoading: authLoading, checked } = useAuth();
  const [isCoinbaseLinked, setIsCoinbaseLinked] = useState(null);
  const [balance, setBalance] = useState({});
  const [isLoading, setIsLoading] = useState(true);

  const [bots, setBots] = useState([]);
  const [subscribedBots, setSubscribedBots] = useState([]);
  const [portfolios, setPortfolios] = useState([]);
  const [selectedPortfolio, setSelectedPortfolio] = useState("");
  const [selectedBot, setSelectedBot] = useState("");

  const userId = user?.id;
  const socketRef = useRef(null);

  useEffect(() => {
    if (isCoinbaseLinked === true && isAuthenticated && user?.id) {
      console.log("Coinbase linked and ready. Proceeding without reload.");
    }
  }, [isCoinbaseLinked, isAuthenticated, user]);

  useEffect(() => {
    if (!isAuthenticated) return;

    const checkCoinbaseLink = async () => {
      try {
        const res = await fetch("http://localhost:8000/coin/linked", {
          credentials: "include",
        });
        const data = await res.json();
        setIsCoinbaseLinked(data?.linked ?? false);
      } catch (err) {
        console.error("Failed to check Coinbase link:", err);
        setIsCoinbaseLinked(false);
      }
    };

    checkCoinbaseLink();
  }, [isAuthenticated]);

  useEffect(() => {
    if (!user || !user.id || !isAuthenticated) return;

    const connectWebSocket = () => {
      if (socketRef.current) return;

      const socket = new WebSocket("ws://localhost:8000/coin/ws/balance");
      socketRef.current = socket;

      socket.onopen = () => {
        socket.send(JSON.stringify({ userId: user.id }));
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data && typeof data === "object") {
            setBalance(data);
          }
        } catch (e) {
          console.error("Invalid WebSocket message format:", e);
        }
      };

      socket.onerror = (err) => console.error("WebSocket error:", err);
      socket.onclose = () => {
        console.log("WebSocket closed");
        socketRef.current = null;
      };
    };

    const checkAccountsAndConnect = async () => {
      try {
        const res = await fetch("http://localhost:8000/coin/accounts", {
          credentials: "include",
        });
        const data = await res.json();

        if (Array.isArray(data.data) && data.data.length > 0) {
          connectWebSocket();
        } else {
          console.warn("No accounts found");
          setIsLoading(false);
        }
      } catch (err) {
        console.error("Error checking accounts:", err);
        setIsLoading(false);
      }
    };

    checkAccountsAndConnect();
  }, [isAuthenticated, user]);

  useEffect(() => {
    if (userId && balance[userId]) {
      setIsLoading(false);
    }

    const timeout = setTimeout(() => {
      if (userId && !balance[userId]) {
        console.warn("Timeout: forcing balance loading fallback");
        setIsLoading(false);
      }
    }, 5000);

    return () => clearTimeout(timeout);
  }, [userId, balance]);

  useEffect(() => {
    if (!isAuthenticated || isCoinbaseLinked !== true) return;

    const fetchData = async () => {
      try {
        const options = {
          credentials: "include",
          headers: { Accept: "application/json" },
        };

        const [botsRes, subsRes, portfoliosRes] = await Promise.all([
          fetch("http://localhost:8000/bots", options),
          fetch("http://localhost:8000/user/subscriptions", options),
          fetch("http://localhost:8000/coin/portfolios", options),
        ]);

        if (!portfoliosRes.ok) {
          throw new Error(`Error fetching portfolios: ${portfoliosRes.statusText}`);
        }

        const [botsData, subsData, portfoliosData] = await Promise.all([
          botsRes.json(),
          subsRes.json(),
          portfoliosRes.json(),
        ]);

        setBots(Array.isArray(botsData) ? botsData : []);
        setSubscribedBots(Array.isArray(subsData) ? subsData : []);
        setPortfolios(Array.isArray(portfoliosData?.portfolios) ? portfoliosData.portfolios : []);
      } catch (error) {
        console.error("Error loading bots/subscriptions/portfolios", error);
      }
    };

    fetchData();
  }, [isAuthenticated, isCoinbaseLinked]);

  const handleSubscribe = async () => {
    if (!selectedPortfolio || !selectedBot) return;

    try {
      const res = await fetch("http://localhost:8000/bots/subscribe", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          bot_id: Number(selectedBot),
          portfolio_uuid: selectedPortfolio,
        }),
      });

      if (!res.ok) {
        const errorText = await res.text();
        console.error("Backend error:", errorText);
        throw new Error("Failed to subscribe: " + errorText);
      }

      alert("Subscribed successfully!");

      const updated = await fetch("http://localhost:8000/user/subscriptions", {
        credentials: "include",
      });

      const updatedData = await updated.json();
      setSubscribedBots(Array.isArray(updatedData) ? updatedData : []);
    } catch (err) {
      console.error("Subscription failed", err);
      alert("Failed to subscribe.");
    }
  };

  const handleUnsubscribe = async (botId, portfolioUuid) => {
    try {
      const res = await fetch("http://localhost:8000/bots/unsubscribe", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          bot_id: Number(botId),
          portfolio_uuid: portfolioUuid,
        }),
      });

      if (!res.ok) {
        const errorText = await res.text();
        console.error("Unsubscribe error:", errorText);
        throw new Error("Failed to unsubscribe: " + errorText);
      }

      alert("Unsubscribed successfully!");

      const updated = await fetch("http://localhost:8000/user/subscriptions", {
        credentials: "include",
      });

      const updatedData = await updated.json();
      setSubscribedBots(Array.isArray(updatedData) ? updatedData : []);
    } catch (err) {
      console.error("Unsubscription failed", err);
      alert("Failed to unsubscribe.");
    }
  };

  if (!checked || authLoading) return <div>Loading...</div>;
  if (!isAuthenticated) return <Navigate to="/authentication/sign-in" />;
  if (isCoinbaseLinked === null) return <div>Checking Coinbase link...</div>;
  if (isCoinbaseLinked === false) return <Navigate to="/link-coinbase" />;
  if (isLoading) return <CircularProgress sx={{ m: 5 }} />;

  const usdBalance = parseFloat(balance[userId]?.USD || 0).toFixed(2);

  return (
    <DashboardLayout>
      <DashboardNavbar absolute isMini />
      <MDBox py={3}>
        <Grid container spacing={3}>
          <Grid item xs={12} sm={6} lg={4}>
            <Card sx={{ backgroundColor: "#1a1a1a", p: 3, mt: 3 }}>
              <MDTypography variant="h5" color="white" gutterBottom>
                Coinbase Balance
              </MDTypography>
              <MDBox mb={2} mt={5}>
                <MDTypography color="white">
                  <strong>Balance:</strong> ${usdBalance}
                </MDTypography>
              </MDBox>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} lg={4}>
            <Card sx={{ backgroundColor: "#1a1a1a", p: 3, mt: 3 }}>
              <MDTypography variant="h5" color="white" gutterBottom>
                Your Subscribed Bots
              </MDTypography>
              {subscribedBots.length === 0 ? (
                <MDTypography color="white">No subscriptions yet.</MDTypography>
              ) : (
                subscribedBots.map((sub) => (
                  <MDBox key={`${sub.bot_id}-${sub.portfolio_uuid}`} mt={1}>
                    <MDTypography variant="body1" color="white">
                      Bot ID: {sub.bot_id}, Portfolio: {sub.portfolio_uuid}
                    </MDTypography>
                    <Button
                      variant="contained"
                      color="error"
                      sx={{ mt: 2 }}
                      onClick={() => handleUnsubscribe(sub.bot_id, sub.portfolio_uuid)}
                    >
                      Unsubscribe
                    </Button>
                  </MDBox>
                ))
              )}
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} lg={4}>
            <Card sx={{ backgroundColor: "#1a1a1a", p: 3, mt: 3 }}>
              <MDTypography variant="h5" color="white" gutterBottom>
                Subscribe to a Bot
              </MDTypography>

              <MDBox mb={2}>
                <FormControl fullWidth>
                  <InputLabel sx={{ color: "white" }}>Select Portfolio</InputLabel>
                  <Select
                    value={selectedPortfolio || ""}
                    onChange={(e) => setSelectedPortfolio(e.target.value)}
                    disabled={portfolios.length === 0}
                    sx={{ color: "white", borderColor: "white" }}
                  >
                    {portfolios.length === 0 ? (
                      <MenuItem disabled>No portfolios available</MenuItem>
                    ) : (
                      portfolios.map((p, i) => (
                        <MenuItem key={p.portfolio?.uuid || i} value={p.portfolio?.uuid}>
                          {p.portfolio?.name || `Portfolio ${i + 1}`}
                        </MenuItem>
                      ))
                    )}
                  </Select>
                </FormControl>
              </MDBox>

              <MDBox mb={2}>
                <FormControl fullWidth>
                  <InputLabel sx={{ color: "white" }}>Select Bot</InputLabel>
                  <Select
                    value={selectedBot || ""}
                    onChange={(e) => setSelectedBot(e.target.value)}
                    disabled={bots.length === 0}
                    sx={{ color: "white", borderColor: "white" }}
                  >
                    {bots.length === 0 ? (
                      <MenuItem disabled>No bots available</MenuItem>
                    ) : (
                      bots.map((bot) => (
                        <MenuItem key={bot.id.toString()} value={bot.id.toString()}>
                          {bot.name}
                        </MenuItem>
                      ))
                    )}
                  </Select>
                </FormControl>
              </MDBox>

              <Button variant="contained" color="primary" onClick={handleSubscribe}>
                Subscribe
              </Button>
            </Card>
          </Grid>
        </Grid>
      </MDBox>
      <Footer />
    </DashboardLayout>
  );
}

export default Trade;
