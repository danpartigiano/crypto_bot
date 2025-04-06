import { useState } from "react";
import Footer from './Footer';

const LinkCoinbase = () => {
  const [loading, setLoading] = useState(false);

  const handleLinkCoinbase = async () => {
    setLoading(true);
    try {
      const response = await fetch("http://127.0.0.1:8000/coinbase/oauth-redirect-url", {
        method: "GET",
        credentials: "include",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      });

      const data = await response.json();
      if (data.coinbase_url) {
        window.open(data.coinbase_url, "_blank", "width=600,height=600");
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
    <div className="full-page">
      <h2>Link Your Coinbase Account</h2>
      <button onClick={handleLinkCoinbase} disabled={loading}>
        {loading ? "Connecting..." : "Link Coinbase Account"}
      </button>
      <Footer />
    </div>
  );
};

export default LinkCoinbase;
