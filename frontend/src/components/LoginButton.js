import React from 'react';
import { useNavigate } from 'react-router-dom';

const LoginButton = () => {
  const navigate = useNavigate();

  const handleLoginClick = () => {
    navigate('/login'); // Navigate to the login page
  };

  return (
    <button onClick={handleLoginClick} className="login-btn">
      Login
    </button>
  );
};

export default LoginButton;
