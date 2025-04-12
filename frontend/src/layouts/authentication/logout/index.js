/* eslint-disable */

import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "context/AuthContext";

function Logout() {
  const navigate = useNavigate();
  const { setIsAuthenticated } = useAuth();

  useEffect(() => {
    const doLogout = async () => {
      try {
        const response = await fetch("http://localhost:8000/user/logout", {
          method: "POST",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
          },
        });

        if (!response.ok) {
          console.error("Logout failed with status:", response.status);
        }

        setIsAuthenticated(false);
        navigate("/authentication/sign-in");
      } catch (error) {
        console.error("Error during logout:", error);
      }
    };

    doLogout();
  }, [navigate, setIsAuthenticated]);

  return null;
}

export default Logout;

