/* eslint-disable */

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

const SignUp = () => {
  const [formData, setFormData] = useState({
    first_name: "",
    last_name: "",
    email: "",
    username: "",
    password: "",
  });
  const [error, setError] = useState("");
  const { setIsAuthenticated } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post("http://localhost:8000/user/create", formData, {
        headers: { "Content-Type": "application/json" },
        withCredentials: true,
      });

      if (response.status === 200) {
        setIsAuthenticated(true);
        navigate("/sign-in");
      }
    } catch (err) {
      setError("Signup failed. Please check your information and try again.");
    }
  };

  return (
    <BasicLayout>
      <Card>
        <MDBox pt={4} pb={3} px={3}>
          <MDTypography variant="h4" fontWeight="medium" textAlign="center">
            Sign Up
          </MDTypography>
          {error && (
            <MDTypography color="error" fontSize="sm" mt={1}>
              {error}
            </MDTypography>
          )}
          <MDBox component="form" role="form" onSubmit={handleSubmit}>
            <MDBox mb={2}>
              <MDInput label="First Name" name="first_name" value={formData.first_name} onChange={handleChange} fullWidth required />
            </MDBox>
            <MDBox mb={2}>
              <MDInput label="Last Name" name="last_name" value={formData.last_name} onChange={handleChange} fullWidth required />
            </MDBox>
            <MDBox mb={2}>
              <MDInput type="email" label="Email" name="email" value={formData.email} onChange={handleChange} fullWidth required />
            </MDBox>
            <MDBox mb={2}>
              <MDInput label="Username" name="username" value={formData.username} onChange={handleChange} fullWidth required />
            </MDBox>
            <MDBox mb={2}>
              <MDInput type="password" label="Password" name="password" value={formData.password} onChange={handleChange} fullWidth required />
            </MDBox>
            <MDBox mt={4} mb={1}>
              <MDButton type="submit" variant="gradient" color="info" fullWidth>
                Sign Up
              </MDButton>
            </MDBox>
            <MDBox mt={2} textAlign="center">
              <MDTypography variant="button" color="text">
                Already have an account?{" "}
                <MDTypography
                  variant="button"
                  color="info"
                  fontWeight="medium"
                  sx={{ cursor: "pointer" }}
                  onClick={() => navigate("/authentication/sign-in")}
                >
                  Login
                </MDTypography>
              </MDTypography>
            </MDBox>
          </MDBox>
        </MDBox>
      </Card>
    </BasicLayout>
  );
};

export default SignUp;
