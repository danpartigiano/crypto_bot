/* eslint-disable */

/**
=========================================================
* Material Dashboard 2 React - v2.2.0
=========================================================

* Product Page: https://www.creative-tim.com/product/material-dashboard-react
* Copyright 2023 Creative Tim (https://www.creative-tim.com)

Coded by www.creative-tim.com

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

// @mui material components
import Grid from "@mui/material/Grid";
import Divider from "@mui/material/Divider";
import Button from "@mui/material/Button";

// Material Dashboard 2 React components
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";

// Material Dashboard 2 React example components
import DashboardLayout from "examples/LayoutContainers/DashboardLayout";
import DashboardNavbar from "examples/Navbars/DashboardNavbar";
import Footer from "examples/Footer";

import { useState } from "react";
import { useNavigate } from "react-router-dom";

function LinkCoinbase() {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLinkCoinbase = async () => {
    setLoading(true);
    try {
      const response = await fetch("http://localhost:8000/coin/oauth-redirect-url", {
        method: "GET",
        credentials: "include",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
      });

      const data = await response.json();
      if (data.coinbase_url) {
        window.open(data.coinbase_url, "_blank", "width=600,height=600");
        navigate("/trade");
      } else {
        console.error("No Coinbase URL returned.");
      }
    } catch (error) {
      console.error("Error fetching Coinbase URL:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <DashboardLayout>
      <DashboardNavbar />
      <MDBox py={8} px={2}>
        <MDBox
          display="flex"
          flexDirection="column"
          alignItems="center"
          justifyContent="center"
          textAlign="center"
        >
          <MDTypography variant="h4" color="text" mb={2}>
            Link Your Coinbase Account
          </MDTypography>
          <Button
            variant="contained"
            color="info"
            onClick={handleLinkCoinbase}
            disabled={loading}
          >
            {loading ? "Connecting..." : "Link Coinbase Account"}
          </Button>
        </MDBox>
      </MDBox>
      <Footer />
    </DashboardLayout>
  );
}

export default LinkCoinbase;
