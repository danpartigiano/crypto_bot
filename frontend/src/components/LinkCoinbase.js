import { useState, useEffect, useCallback } from "react";
import Footer from "./Footer";

const LinkCoinbase = () => {
  const [loading, setLoading] = useState(false);
  const [isLinked, setIsLinked] = useState(false);
  const [error, setError] = useState(null);
  const token = localStorage.getItem("token");

  // Check if Coinbase is linked
  const checkCoinbaseLinkStatus = useCallback(async () => {
    try {
      const response = await fetch("http://localhost:8000/coinbase/info", {
        method: "GET",
        credentials: "include",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      });

      if (!response.ok) throw new Error("Failed to check coinbase status");
      setIsLinked(await response.json());
    } catch (error) {
      setError("Error did not link Coinbase.");
    }
  }, [token]);

  useEffect(() => { checkCoinbaseLinkStatus(); }, [checkCoinbaseLinkStatus]);

  //Link Coinbase account
  const handleLinkCoinbase = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("http://localhost:8000/coinbase/oauth-redirect-url", {
        method: "GET",
        credentials: "include",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      });

      if (!response.ok) throw new Error("Failed to fetch Coinbase OAuth URL");
      const data = await response.json();
      if (data.coinbase_url) window.open(data.coinbase_url, "_blank", "width=600,height=600");
      else setError("Failed to open Coinbase.");
    } catch (error) {
      setError("Error Coinbase account not linked.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="full-page">
      <h2>Coinbase Integration</h2>
      {error && <p className="error">{error}</p>}
      {!isLinked && (
        <button onClick={handleLinkCoinbase} disabled={loading}>
          {loading ? "Linking..." : "Link Coinbase Account"}
        </button>
      )}
      <Footer />
    </div>
  );
};

export default LinkCoinbase;