/* eslint-disable */

// src/layouts/authentication/sign-in/index.js
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";

import Card from "@mui/material/Card";
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";
import MDButton from "components/MDButton";

import BasicLayout from "layouts/authentication/components/BasicLayout";
import { useAuth } from "context/AuthContext";

const SignIn = () => {
  const [formData, setFormData] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const { setIsAuthenticated } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      const formDataToSend = new URLSearchParams();
      formDataToSend.append("username", formData.username);
      formDataToSend.append("password", formData.password);

      const response = await axios.post(
        "http://localhost:8000/user/login",
        formDataToSend,
        {
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          withCredentials: true,
        }
      );

      if (response.status === 200) {
        setIsAuthenticated(true);
        navigate("/dashboard");
      }
    } catch (err) {
      setError("Invalid username or password. Please try again.");
    }
  };

  return (
    <BasicLayout>
      <Card>
        <MDBox pt={4} pb={3} px={3}>
          <MDTypography variant="h4" fontWeight="medium" textAlign="center">
            Sign In
          </MDTypography>
          {error && (
            <MDTypography color="error" fontSize="sm" mt={1}>
              {error}
            </MDTypography>
          )}
          <MDBox component="form" role="form" onSubmit={handleSubmit}>
            <MDBox mb={2}>
              <MDInput
                type="text"
                label="Username"
                name="username"
                value={formData.username}
                onChange={handleChange}
                fullWidth
                required
              />
            </MDBox>
            <MDBox mb={2}>
              <MDInput
                type="password"
                label="Password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                fullWidth
                required
              />
            </MDBox>
            <MDBox mt={4} mb={1}>
              <MDButton type="submit" variant="gradient" color="info" fullWidth>
                Sign In
              </MDButton>
            </MDBox>
            <MDBox mt={2} textAlign="center">
              <MDTypography variant="button" color="text">
                Don't have an account?{" "}
                <MDTypography
                  variant="button"
                  color="info"
                  fontWeight="medium"
                  sx={{ cursor: "pointer" }}
                  onClick={() => navigate("/authentication/sign-up")}
                >
                  Sign Up
                </MDTypography>
              </MDTypography>
            </MDBox>
          </MDBox>
        </MDBox>
      </Card>
    </BasicLayout>
  );
};

export default SignIn;

