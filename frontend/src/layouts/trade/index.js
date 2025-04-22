import { useAuth } from "context/AuthContext";
import { Navigate } from "react-router-dom";
import { useEffect, useState } from "react";

// @mui material components
import Grid from "@mui/material/Grid";
import Card from "@mui/material/Card";

// Material Dashboard 2 React components
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";

// Material Dashboard 2 React examples
import DashboardLayout from "examples/LayoutContainers/DashboardLayout";
import DashboardNavbar from "examples/Navbars/DashboardNavbar";
import Footer from "examples/Footer";

function Trade() {
  const { isAuthenticated, user } = useAuth();
  const [isCoinbaseLinked, setIsCoinbaseLinked] = useState(null);
  const [balance, setBalance] = useState({});
  const [isLoading, setIsLoading] = useState(true);

  const userId = user?.id;

  useEffect(() => {
    const checkCoinbaseLink = async () => {
      try {
        const res = await fetch("http://localhost:8000/coin/linked", {
          method: "GET",
          credentials: "include",
          headers: {
            Authorization: `Bearer ${localStorage.getItem("token")}`,
          },
        });

        const data = await res.json();
        setIsCoinbaseLinked(data.linked);
      } catch (err) {
        console.error("Failed to check Coinbase link:", err);
        setIsCoinbaseLinked(false);
      }
    };

    if (isAuthenticated) {
      checkCoinbaseLink();
    }
  }, [isAuthenticated]);

  useEffect(() => {
    if (!userId) return;

    const socket = new WebSocket("ws://localhost:8000/coin/ws/balance");

    socket.onopen = () => {
      console.log("WebSocket connected");
      socket.send(JSON.stringify({ userId }));
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("WebSocket received:", data);
      setBalance((prev) => ({
        ...prev,
        [userId]: data,
      }));
    };

    socket.onerror = (err) => {
      console.error("WebSocket error:", err);
    };

    socket.onclose = () => {
      console.log("WebSocket closed");
    };

    return () => {
      socket.close();
    };
  }, [userId]);

  useEffect(() => {
    if (userId && balance?.[userId] !== undefined) {
      setIsLoading(false);
    }
  }, [userId, balance]);

  if (!user) return <div>Loading user...</div>;
  if (!isAuthenticated) return <Navigate to="/authentication/sign-in" />;
  if (isCoinbaseLinked === null) return <div>Checking Coinbase link...</div>;

  if (isCoinbaseLinked === false) return <Navigate to="/link-coinbase" />;

  if (isLoading) return <div>Loading balance...</div>;

  const usdBalance = balance?.[userId]?.USD || "0.00";

  return (
    <DashboardLayout>
      <DashboardNavbar absolute isMini />
      <MDBox py={3}>
        <Grid container spacing={3}>
          <Grid item xs={12} sm={6} lg={4}>
            <Card sx={{ backgroundColor: "#1a1a1a", p: 3, marginTop: "30px" }}>
              <MDTypography variant="h5" color="white" gutterBottom>
                Coinbase Balance
              </MDTypography>
              <MDBox mb={2} mt={5}>
                <strong>Balance:</strong> ${parseFloat(usdBalance).toFixed(2)}
              </MDBox>
            </Card>
          </Grid>
        </Grid>
      </MDBox>
      <Footer />
    </DashboardLayout>
  );
}

export default Trade;
