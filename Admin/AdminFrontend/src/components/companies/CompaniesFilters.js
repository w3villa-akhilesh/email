import React from 'react';
import {
  CButton,
  CButtonGroup,
  CBadge
} from '@coreui/react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faPlus,
  faFilter,
  faFilterCircleXmark
} from '@fortawesome/free-solid-svg-icons';
import { useButtonHover } from '../../hooks/useButtonHover';

const CompaniesFilters = ({
  isFilterActive,
  onClearFilters,
  onAddCompany,
  totalCount,
  loading,
  hasData
}) => {
  // Modern button styles
  const buttonStyle = {
    borderRadius: '10px',
    fontWeight: '600',
    padding: '8px 16px',
    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
    position: 'relative',
    overflow: 'hidden'
  };

  const primaryButtonStyle = {
    ...buttonStyle,
    border: '2px solid #40518a',
    color: 'white',
    background: 'linear-gradient(135deg, #40518a 0%, #2d3a61 100%)',
    boxShadow: '0 3px 10px rgba(64, 81, 138, 0.25)'
  };

  const clearButtonStyle = {
    ...buttonStyle,
    border: '2px solid #6c757d',
    color: '#6c757d',
    backgroundColor: 'rgba(108, 117, 125, 0.08)',
    boxShadow: '0 3px 10px rgba(108, 117, 125, 0.15)'
  };

  // Color configurations for hover effects
  const primaryColors = {
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
  };

  const primaryHover = useButtonHover(primaryColors);

  return (
    <div className="d-flex align-items-center">
      <CButton
        variant="outline"
        onClick={onAddCompany}
        className="me-3 d-flex align-items-center"
        style={primaryButtonStyle}
        onMouseEnter={primaryHover.onMouseEnter}
        onMouseLeave={primaryHover.onMouseLeave}
        disabled={loading}
      >
        <FontAwesomeIcon icon={faPlus} className="me-2" />
        Add Company
      </CButton>
      
      {isFilterActive && (
        <CButton
          variant="outline"
          onClick={onClearFilters}
          className="me-3 d-flex align-items-center"
          style={clearButtonStyle}
        >
          <FontAwesomeIcon icon={faFilterCircleXmark} className="me-2" />
          Clear Filters
        </CButton>
      )}

      {!loading && hasData && (
        <span className="record-badge">
          {totalCount} {totalCount === 1 ? 'Company' : 'Companies'}
        </span>
      )}
    </div>
  );
};

export default CompaniesFilters;
