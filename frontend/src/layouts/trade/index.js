import { useAuth } from "context/AuthContext";
import { Navigate } from "react-router-dom";
import { useEffect, useState } from "react";

// @mui material components
import Grid from "@mui/material/Grid";

// Material Dashboard 2 React components
import MDBox from "components/MDBox";

// Material Dashboard 2 React examples
import DashboardLayout from "examples/LayoutContainers/DashboardLayout";
import DashboardNavbar from "examples/Navbars/DashboardNavbar";
import Footer from "examples/Footer";
import MasterCard from "examples/Cards/MasterCard";
import DefaultInfoCard from "examples/Cards/InfoCards/DefaultInfoCard";

function Trade() {
  const { isAuthenticated } = useAuth();
  const [isCoinbaseLinked, setIsCoinbaseLinked] = useState(null);

  useEffect(() => {
    const checkCoinbaseLink = async () => {
      try {
        const res = await fetch("http://localhost:8000/coinbase/linked", {
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

  if (!isAuthenticated) return <Navigate to="/authentication/sign-in" />;
  if (isCoinbaseLinked === false) return <Navigate to="/link-coinbase" />;
  if (isCoinbaseLinked === null) return <div>Loading...</div>;

  return (
    <DashboardLayout>
      <DashboardNavbar absolute isMini />
      <Footer />
    </DashboardLayout>
  );
}
export default Trade;
