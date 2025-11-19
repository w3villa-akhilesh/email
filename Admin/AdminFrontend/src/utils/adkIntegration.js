/**
 * ADK Web UI Integration Utilities
 * 
 * Helper functions to deep-link from AdminFrontend to ADK Web UI
 */

// Get configurable ADK UI URL from environment variable
const getADKUIUrl = () => import.meta.env.VITE_ADK_UI_URL || 'http://localhost:4200';

/**
 * Opens a specific session in the ADK Web UI
 * @param {string} appName - The app/agent name (e.g., 'triage_agent')
 * @param {string} userId - The user ID
 * @param {string} sessionId - The session ID to open
 */
export const openSessionInADK = (appName, userId, sessionId) => {
  // Get ADK UI URL from environment variable
  const baseUrl = getADKUIUrl();
  
  // Get access token from localStorage
  const accessToken = localStorage.getItem('access_token');
  
  if (!accessToken) {
    console.error('[ADK Integration] No access token found. User may need to login again.');
    alert('Authentication required. Please refresh the page and try again.');
    return;
  }
  
  // Construct ADK UI URL with query parameters including token
  const url = `${baseUrl}?app=${encodeURIComponent(appName)}&user=${encodeURIComponent(userId)}&session=${encodeURIComponent(sessionId)}&token=${encodeURIComponent(accessToken)}`;
  
  // Open in new tab
  window.open(url, '_blank');
};

export default {
  openSessionInADK
};

