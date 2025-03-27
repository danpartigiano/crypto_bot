import React, { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";

const CoinbaseCallback = () => {
  const [username, setUsername] = useState("");
  const location = useLocation(); // Hook to access the current URL

  useEffect(() => {
    // Get the username from the URL query parameter
    const urlParams = new URLSearchParams(location.search);
    const username = urlParams.get("username");
    // const code = params.get('code');
    // const state = params.get('state');

    if (username) {
      setUsername(username); // Set the username in the state
    }
  }, [location]);

  return (
    <div>
      <h1>Welcome to Coinbase, {username}!</h1>
      <p>Your Coinbase account is now connected.</p>
    </div>
  );
};

export default CoinbaseCallback;
