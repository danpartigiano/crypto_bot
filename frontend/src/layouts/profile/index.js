/* eslint-disable */

import { useAuth } from "context/AuthContext";
import { Navigate, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import axios from "axios";

// @mui components
import CircularProgress from "@mui/material/CircularProgress";
import Button from "@mui/material/Button";
import Grid from "@mui/material/Grid";

// Material Dashboard components
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import DashboardLayout from "examples/LayoutContainers/DashboardLayout";
import DashboardNavbar from "examples/Navbars/DashboardNavbar";
import Footer from "examples/Footer";
import ProfileInfoCard from "examples/Cards/InfoCards/ProfileInfoCard";

function Profile() {
  const { isAuthenticated, isLoading, checked, user } = useAuth();
  const [localUser, setLocalUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [linking, setLinking] = useState(false);
  const [isLinked, setIsLinked] = useState(false);
  const [coinbaseInfo, setCoinbaseInfo] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [userRes, linkRes] = await Promise.all([
          axios.get("http://localhost:8000/user/info", { withCredentials: true }),
          axios.get("http://localhost:8000/coin/linked", { withCredentials: true }),
        ]);

        setLocalUser(userRes.data);
        const linked = linkRes.data?.linked === true;
        setIsLinked(linked);

        if (linked) {
          const coinbaseRes = await axios.get("http://localhost:8000/coin/info", { withCredentials: true });
          setCoinbaseInfo(coinbaseRes.data);
        }
      } catch (error) {
        console.error("Failed to fetch data:", error);
      } finally {
        setLoading(false);
      }
    };

    if (checked) {
      fetchAll();
    }
  }, [checked]);

  const handleLinkCoinbase = async () => {
    setLinking(true);
    try {
      const response = await fetch("http://localhost:8000/coin/oauth-redirect-url", {
        method: "GET",
        credentials: "include",
      });
      const data = await response.json();

      if (data.coinbase_url) {
        const popup = window.open(data.coinbase_url, "_blank", "width=600,height=600");

        const pollInterval = setInterval(async () => {
          try {
            const res = await fetch("http://localhost:8000/coin/linked", {
              method: "GET",
              credentials: "include",
            });
            const linkStatus = await res.json();

            if (linkStatus.linked) {
              clearInterval(pollInterval);
              popup?.close();
              setIsLinked(true);
              try {
                const coinbaseRes = await axios.get("http://localhost:8000/coin/info", { withCredentials: true });
                setCoinbaseInfo(coinbaseRes.data);
              } catch (error) {
                console.error("Failed to fetch coinbase info after linking:", error);
              }
              navigate("/profile");
            }
          } catch (err) {
            console.error("Polling failed:", err);
          }
        }, 2000);
      } else {
        console.error("No Coinbase URL returned.");
      }
    } catch (error) {
      console.error("Error fetching Coinbase URL:", error);
    } finally {
      setLinking(false);
    }
  };

  if (!checked || isLoading || loading) {
    return (
      <DashboardLayout>
        <DashboardNavbar />
        <MDBox display="flex" justifyContent="center" alignItems="center" minHeight="30vh">
          <CircularProgress />
        </MDBox>
        <Footer />
      </DashboardLayout>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/authentication/sign-in" />;
  }

  return (
    <DashboardLayout>
      <DashboardNavbar />
      <MDBox py={3}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <ProfileInfoCard
              title="Profile Information"
              description="User information from your account"
              info={{
                username: localUser?.username,
                first_name: localUser?.first_name,
                last_name: localUser?.last_name,
                email: localUser?.email,
              }}
              action={{ route: "", tooltip: "Edit Profile" }}
            />
          </Grid>

          {isLinked && coinbaseInfo && (
            <Grid item xs={12} md={6}>
              <ProfileInfoCard
                title="Coinbase Information"
                description="Linked Coinbase account details"
                info={{
                  name: coinbaseInfo.name,
                  email: coinbaseInfo.email,
                  time_zone: coinbaseInfo.time_zone,
                  native_currency: coinbaseInfo.native_currency,
                  country: coinbaseInfo.country?.name,
                  created_at: coinbaseInfo.created_at,
                }}
                action={{ route: "", tooltip: "Coinbase Info" }}
              />
            </Grid>
          )}
        </Grid>

        <MDBox display="flex" justifyContent="center" mt={4}>
          <Button
            variant="contained"
            color={isLinked ? "success" : "info"}
            onClick={handleLinkCoinbase}
            disabled={linking || isLinked}
          >
            {isLinked ? "Coinbase Linked" : linking ? "Connecting..." : "Link Coinbase Account"}
          </Button>
        </MDBox>
      </MDBox>
      <Footer />
    </DashboardLayout>
  );
}

export default Profile;
