import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';

const Signup = () => {
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    username: '',
    password: '',
  });
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const { setIsAuthenticated } = useAuth();

  // Handle input changes
  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  // Handle form submission for user creation
  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      // Sending signup data as JSON to the /user/create endpoint.
      const response = await axios.post(
        'http://127.0.0.1:8000/user/create',
        formData,
        {
          headers: {
            'Content-Type': 'application/json',
          },
          withCredentials: true, // so cookies are handled properly
        }
      );

      // If user creation and login (via the create endpoint) are successful,
      // the backend will return a success response.
      if (response.status === 200) {
        setIsAuthenticated(true);
        navigate('/dashboard');
      }
    } catch (err) {
      setError('Signup failed. Please check your information and try again.');
    }
  };

  return (
    <div className="signup-container">
      <h2>Sign Up</h2>
      {error && <p className="error">{error}</p>}
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="first_name">First Name:</label>
          <input
            type="text"
            id="first_name"
            name="first_name"
            value={formData.first_name}
            onChange={handleChange}
            required
          />
        </div>

        <div>
          <label htmlFor="last_name">Last Name:</label>
          <input
            type="text"
            id="last_name"
            name="last_name"
            value={formData.last_name}
            onChange={handleChange}
            required
          />
        </div>

        <div>
          <label htmlFor="email">Email:</label>
          <input
            type="email"
            id="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            required
          />
        </div>

        <div>
          <label htmlFor="username">Username:</label>
          <input
            type="text"
            id="username"
            name="username"
            value={formData.username}
            onChange={handleChange}
            required
          />
        </div>

        <div>
          <label htmlFor="password">Password:</label>
          <input
            type="password"
            id="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            required
          />
        </div>

        <button type="submit" className="signup-btn">
          Sign Up
        </button>
      </form>
      <p>
        Already have an account?{' '}
        <button onClick={() => navigate('/login')} className="link-btn">
          Login
        </button>
      </p>
    </div>
  );
};

export default Signup;

