import React, { useEffect } from 'react'
import { Navigate, Outlet } from 'react-router-dom'

const ProtectedRoute = () => {
  // Get access token from URL query parameters
  const urlParams = new URLSearchParams(window.location.search)
  const accessTokenFromUrl = urlParams.get('access_token')

  // Check if access_token is in localStorage
  const accessTokenFromLocalStorage = localStorage.getItem('access_token')

  useEffect(() => {
    // If access_token is in the URL, save it to localStorage
    if (accessTokenFromUrl) {
      localStorage.setItem('access_token', accessTokenFromUrl)
    }
  }, [accessTokenFromUrl])

  // If there is no access token in either location, redirect to login page
  if (!accessTokenFromUrl && !accessTokenFromLocalStorage) {
    return <Navigate to="/login" replace />
  }

  // If the token is found, render the protected route
  return <Outlet />
}

export default ProtectedRoute
