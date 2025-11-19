// Shared button styles and configurations for consistent UI across components

export const baseButtonStyle = {
  borderRadius: '10px',
  fontWeight: '600',
  padding: '8px 16px',
  transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
  position: 'relative',
  overflow: 'hidden'
};

export const buttonStyles = {
  primary: {
    ...baseButtonStyle,
    border: '2px solid #40518a',
    color: 'white',
    background: 'linear-gradient(135deg, #40518a 0%, #2d3a61 100%)',
    boxShadow: '0 3px 10px rgba(64, 81, 138, 0.25)'
  },
  
  secondary: {
    ...baseButtonStyle,
    border: '2px solid #6c757d',
    color: '#6c757d',
    backgroundColor: 'rgba(108, 117, 125, 0.08)',
    boxShadow: '0 3px 10px rgba(108, 117, 125, 0.15)'
  },
  
  edit: {
    ...baseButtonStyle,
    border: '2px solid #40518a',
    color: '#40518a',
    backgroundColor: 'rgba(64, 81, 138, 0.08)',
    boxShadow: '0 3px 10px rgba(64, 81, 138, 0.15)'
  },
  
  success: {
    ...baseButtonStyle,
    border: '2px solid #28a745',
    color: '#28a745',
    backgroundColor: 'rgba(40, 167, 69, 0.08)',
    boxShadow: '0 3px 10px rgba(40, 167, 69, 0.15)'
  },
  
  danger: {
    ...baseButtonStyle,
    border: '2px solid #dc3545',
    color: '#dc3545',
    backgroundColor: 'rgba(220, 53, 69, 0.08)',
    boxShadow: '0 3px 10px rgba(220, 53, 69, 0.15)'
  },
  
  info: {
    ...baseButtonStyle,
    border: '2px solid #17a2b8',
    color: '#17a2b8',
    backgroundColor: 'rgba(23, 162, 184, 0.08)',
    boxShadow: '0 3px 10px rgba(23, 162, 184, 0.15)'
  }
};

// Hover color configurations for useButtonHover hook
export const hoverColors = {
  primary: {
    normal: {
      background: 'linear-gradient(135deg, #40518a 0%, #2d3a61 100%)',
      color: 'white',
      borderColor: '#40518a',
      boxShadow: '0 3px 10px rgba(64, 81, 138, 0.25)'
    },
    hover: {
      background: 'linear-gradient(135deg, #2d3a61 0%, #1e2a45 100%)',
      color: 'white',
      borderColor: '#1e2a45',
      boxShadow: '0 6px 20px rgba(64, 81, 138, 0.4)'
    }
  },
  
  secondary: {
    normal: {
      background: 'rgba(108, 117, 125, 0.08)',
      color: '#6c757d',
      borderColor: '#6c757d',
      boxShadow: '0 3px 10px rgba(108, 117, 125, 0.15)'
    },
    hover: {
      background: 'linear-gradient(135deg, #6c757d 0%, #545b62 100%)',
      color: 'white',
      borderColor: '#545b62',
      boxShadow: '0 6px 20px rgba(108, 117, 125, 0.35)'
    }
  },
  
  edit: {
    normal: {
      background: 'rgba(64, 81, 138, 0.08)',
      color: '#40518a',
      borderColor: '#40518a',
      boxShadow: '0 3px 10px rgba(64, 81, 138, 0.15)'
    },
    hover: {
      background: 'linear-gradient(135deg, #40518a 0%, #2d3a61 100%)',
      color: 'white',
      borderColor: '#2d3a61',
      boxShadow: '0 6px 20px rgba(64, 81, 138, 0.35)'
    }
  },
  
  success: {
    normal: {
      background: 'rgba(40, 167, 69, 0.08)',
      color: '#28a745',
      borderColor: '#28a745',
      boxShadow: '0 3px 10px rgba(40, 167, 69, 0.15)'
    },
    hover: {
      background: 'linear-gradient(135deg, #28a745 0%, #1e7e34 100%)',
      color: 'white',
      borderColor: '#1e7e34',
      boxShadow: '0 6px 20px rgba(40, 167, 69, 0.35)'
    }
  },
  
  danger: {
    normal: {
      background: 'rgba(220, 53, 69, 0.08)',
      color: '#dc3545',
      borderColor: '#dc3545',
      boxShadow: '0 3px 10px rgba(220, 53, 69, 0.15)'
    },
    hover: {
      background: 'linear-gradient(135deg, #dc3545 0%, #b02a37 100%)',
      color: 'white',
      borderColor: '#b02a37',
      boxShadow: '0 6px 20px rgba(220, 53, 69, 0.35)'
    }
  },
  
  info: {
    normal: {
      background: 'rgba(23, 162, 184, 0.08)',
      color: '#17a2b8',
      borderColor: '#17a2b8',
      boxShadow: '0 3px 10px rgba(23, 162, 184, 0.15)'
    },
    hover: {
      background: 'linear-gradient(135deg, #17a2b8 0%, #117a8b 100%)',
      color: 'white',
      borderColor: '#117a8b',
      boxShadow: '0 6px 20px rgba(23, 162, 184, 0.35)'
    }
  }
};
