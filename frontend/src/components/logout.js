export async function logoutUser() {
  try {
    const response = await fetch('/user/logout', {
      method: 'POST',
      credentials: 'include', // Ensure cookies are sent with the request.
      headers: {
        'Content-Type': 'application/json',
      },
    });
    if (!response.ok) {
      console.error('Logout failed with status:', response.status);
    }
    return response;
  } catch (error) {
    console.error('Error during logout:', error);
  }
}

