// Utility functions for LLM Credentials management

export const maskKey = (key) => {
  if (!key) return '';
  // Keep UI compact: fixed mask length regardless of actual key length
  const visible = 3; // show first/last 3 chars
  if (key.length <= visible * 2) return '••••••';
  const start = key.slice(0, visible);
  const end = key.slice(-visible);
  return `${start}••••••••••••••••••••••••••••••••••••${end}`; // fixed 6 bullets for compact display
};

export const truncateText = (text, maxLength) => {
  if (!text) return '';
  return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
};

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

export const formatDate = (dateString) => {
  if (!dateString) return '';
  
  const date = new Date(dateString);
  
  // Convert to IST (Indian Standard Time)
  return date.toLocaleString('en-IN', {
    timeZone: 'Asia/Kolkata',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true
  });
};

export const buildQueryParams = (filters) => {
  const params = new URLSearchParams();
  
  Object.entries(filters).forEach(([key, value]) => {
    if (value) {
      params.set(key, value);
    }
  });
  
  return params.toString();
};

export const getStatusBadgeClass = (isActive) => {
  return `badge ${isActive ? 'bg-success' : 'bg-secondary'}`;
};

export const getStatusText = (isActive) => {
  return isActive ? 'Active' : 'Inactive';
};
