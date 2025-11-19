// Shared utility functions for common operations

/**
 * Format date string to a readable format
 * @param {string} dateString - ISO date string
 * @param {object} options - Formatting options
 * @returns {string} Formatted date string
 */
export const formatDate = (dateString, options = {}) => {
  if (!dateString) return 'N/A';
  
  try {
    const date = new Date(dateString);
    const defaultOptions = {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      ...options
    };
    
    return date.toLocaleDateString('en-US', defaultOptions);
  } catch (error) {
    console.error('Error formatting date:', error);
    return 'Invalid Date';
  }
};

/**
 * Show alert with auto-dismiss
 * @param {function} setAlertMessage - State setter for alert message
 * @param {function} setAlertType - State setter for alert type
 * @param {string} message - Alert message
 * @param {string} type - Alert type (success, danger, warning, info)
 * @param {number} duration - Auto-dismiss duration in milliseconds
 */
export const showAlert = (setAlertMessage, setAlertType, message, type = 'success', duration = 3000) => {
  setAlertMessage(message);
  setAlertType(type);
  setTimeout(() => setAlertMessage(''), duration);
};

/**
 * Extract error message from API response
 * @param {object} error - Error object from API call
 * @param {string} defaultMessage - Default message if no specific error found
 * @returns {string} Error message
 */
export const extractErrorMessage = (error, defaultMessage = 'An error occurred') => {
  if (error.response?.data) {
    // Check for backend error message structure
    if (error.response.data.message) {
      return error.response.data.message;
    } else if (error.response.data.detail) {
      return error.response.data.detail;
    } else if (typeof error.response.data === 'string') {
      return error.response.data;
    }
  } else if (error.message) {
    return error.message;
  }
  return defaultMessage;
};

/**
 * Truncate text to specified length
 * @param {string} text - Text to truncate
 * @param {number} maxLength - Maximum length
 * @returns {string} Truncated text
 */
export const truncateText = (text, maxLength) => {
  if (!text) return '';
  return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
};

/**
 * Mask sensitive data (like API keys)
 * @param {string} key - Key to mask
 * @param {number} visibleChars - Number of characters to show
 * @returns {string} Masked key
 */
export const maskKey = (key, visibleChars = 8) => {
  if (!key) return '';
  return key.length > visibleChars ? key.substring(0, visibleChars) + '...' : key;
};

/**
 * Copy text to clipboard
 * @param {string} text - Text to copy
 * @param {function} onSuccess - Success callback
 * @param {function} onError - Error callback
 * @returns {Promise<boolean>} Success status
 */
export const copyToClipboard = async (text, onSuccess, onError) => {
  try {
    await navigator.clipboard.writeText(text);
    onSuccess && onSuccess();
    return true;
  } catch (err) {
    console.error('Failed to copy text: ', err);
    onError && onError(err);
    return false;
  }
};
