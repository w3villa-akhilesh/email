import React, { useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faCheck, faExclamationTriangle, faTimes } from '@fortawesome/free-solid-svg-icons';

const Toast = ({ message, type, onClose, duration = 3000 }) => {
  useEffect(() => {
    if (message) {
      const timer = setTimeout(() => {
        onClose();
      }, duration);
      
      return () => clearTimeout(timer);
    }
  }, [message, duration, onClose]);

  if (!message) return null;

  const getToastStyles = () => {
    const baseStyles = {
      position: 'fixed',
      top: '20px',
      right: '20px',
      minWidth: '300px',
      maxWidth: '600px',
      padding: '12px 16px',
      borderRadius: '8px',
      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
      zIndex: 9999,
      display: 'flex',
      alignItems: 'flex-start',
      gap: '10px',
      fontSize: '14px',
      fontWeight: '500',
      animation: 'slideInRight 0.3s ease-out',
      border: '1px solid',
      backdropFilter: 'blur(10px)'
    };

    switch (type) {
      case 'success':
        return {
          ...baseStyles,
          backgroundColor: 'rgba(212, 237, 218, 0.95)',
          borderColor: '#c3e6cb',
          color: '#155724'
        };
      case 'danger':
      case 'error':
        return {
          ...baseStyles,
          backgroundColor: 'rgba(248, 215, 218, 0.95)',
          borderColor: '#f5c6cb',
          color: '#721c24'
        };
      case 'warning':
        return {
          ...baseStyles,
          backgroundColor: 'rgba(255, 243, 205, 0.95)',
          borderColor: '#ffeaa7',
          color: '#856404'
        };
      default:
        return {
          ...baseStyles,
          backgroundColor: 'rgba(209, 236, 241, 0.95)',
          borderColor: '#b8daff',
          color: '#004085'
        };
    }
  };

  const getIcon = () => {
    switch (type) {
      case 'success':
        return <FontAwesomeIcon icon={faCheck} />;
      case 'danger':
      case 'error':
        return <FontAwesomeIcon icon={faTimes} />;
      case 'warning':
        return <FontAwesomeIcon icon={faExclamationTriangle} />;
      default:
        return <FontAwesomeIcon icon={faCheck} />;
    }
  };

  return (
    <>
      <style>
        {`
          @keyframes slideInRight {
            from {
              transform: translateX(100%);
              opacity: 0;
            }
            to {
              transform: translateX(0);
              opacity: 1;
            }
          }
          
          @keyframes slideOutRight {
            from {
              transform: translateX(0);
              opacity: 1;
            }
            to {
              transform: translateX(100%);
              opacity: 0;
            }
          }
        `}
      </style>
      <div style={getToastStyles()}>
        <div style={{ flexShrink: 0, marginTop: '2px' }}>
          {getIcon()}
        </div>
        <div style={{ flex: 1, whiteSpace: 'pre-line', lineHeight: '1.5' }}>
          {message}
        </div>
        <button
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            padding: '4px',
            borderRadius: '4px',
            color: 'inherit',
            opacity: 0.7,
            transition: 'opacity 0.2s',
            flexShrink: 0,
            marginTop: '2px'
          }}
          onMouseEnter={(e) => e.target.style.opacity = 1}
          onMouseLeave={(e) => e.target.style.opacity = 0.7}
        >
          <FontAwesomeIcon icon={faTimes} size="sm" />
        </button>
      </div>
    </>
  );
};

export default Toast;
