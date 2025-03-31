import { useState, useEffect, useCallback } from "react";
import Footer from "./Footer";

const LinkCoinbase = () => {
  const [loading, setLoading] = useState(false);
  const [isLinked, setIsLinked] = useState(false);
  const [balances, setBalances] = useState([]);
  const [error, setError] = useState(null);
  //Get token from local storage
  const token = localStorage.getItem("token");

  //Get the users balance from their coinbase accounr
  const fetchBalances = useCallback(async () => {
    try {
      const response = await fetch("http://localhost:8000/coinbase/accounts", {
        method: "GET",
        credentials: "include",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) throw new Error("Failed to fetch balances");
      setBalances(await response.json());
    } catch (error) {
      setError("Error fetching balances, please try again.");
    }
  }, [token]);

  //Check to make sure their coinbase account is linked
  const checkCoinbaseLinkStatus = useCallback(async () => {
    try {
      const response = await fetch("http://localhost:8000/coinbase/info", {
        method: "GET",
        credentials: "include",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      });

      if (!response.ok) throw new Error("Failed to check link status");
      const data = await response.json();
      setIsLinked(!!data);
      if (data) fetchBalances();
    } catch (error) {
      setError("Error checking Coinbase link status, please try again.");
    }
  }, [fetchBalances, token]);

  
  useEffect(() => { checkCoinbaseLinkStatus(); }, [checkCoinbaseLinkStatus]);

  //Coinbase account linking
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
      else setError("Failed to open Coinbase link.");
    } catch (error) {
      setError("Error linking Coinbase account, please try again.");
    } finally {
      setLoading(false);
    }
  };

  //The OAuth callback from coinbase
  const handleCoinbaseCallback = useCallback(async () => {
    const urlParams = new URLSearchParams(window.location.search);
    const state = urlParams.get("state");
    const code = urlParams.get("code");

    if (state && code) {
      try {
        const response = await fetch("http://localhost:8000/coinbase/callback", {
          method: "GET",
          credentials: "include",
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!response.ok) throw new Error("Error completing OAuth flow");
      } catch (error) {
        setError("Error completing Coinbase OAuth flow.");
      }
    }
  }, [token]);

  useEffect(() => { handleCoinbaseCallback(); }, [handleCoinbaseCallback]);

  return (
    <div className="full-page">
      <h2>Coinbase Integration</h2>
      {error && <p className="error">{error}</p>}
      {isLinked ? (
        <>
          <h3>Your Coinbase Balances</h3>
          <ul>{balances.map((b, i) => (<li key={i}>{b.currency}: {b.balance}</li>))}</ul>
        </>
      ) : (
        <div>
          <p>You are not linked to Coinbase yet.</p>
          <button onClick={handleLinkCoinbase} disabled={loading}>{loading ? "Linking..." : "Link Coinbase Account"}</button>
        </div>
      )}
      <Footer />
    </div>
  );
};

export default LinkCoinbase;