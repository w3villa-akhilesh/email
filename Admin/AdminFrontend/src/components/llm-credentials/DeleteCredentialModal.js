import React from 'react';
import {
  CModal,
  CModalHeader,
  CModalTitle,
  CModalBody,
  CModalFooter,
  CButton,
  CSpinner
} from '@coreui/react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faTrash } from '@fortawesome/free-solid-svg-icons';
import { useButtonHover } from '../../hooks/useButtonHover';

const DeleteCredentialModal = ({ 
  visible, 
  onClose, 
  onConfirm, 
  credential,
  loading = false 
}) => {
  // Modern button styles (matching Company modals)
  const buttonStyle = {
    borderRadius: '10px',
    fontWeight: '600',
    padding: '8px 16px',
    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
    position: 'relative',
    overflow: 'hidden'
  };

  const dangerButtonStyle = {
    ...buttonStyle,
    border: '2px solid #dc3545',
    color: 'white',
    background: 'linear-gradient(135deg, #dc3545 0%, #b02a37 100%)',
    boxShadow: '0 3px 10px rgba(220, 53, 69, 0.25)'
  };

  const secondaryButtonStyle = {
    ...buttonStyle,
    border: '2px solid #6c757d',
    color: '#6c757d',
    backgroundColor: 'rgba(108, 117, 125, 0.08)',
    boxShadow: '0 3px 10px rgba(108, 117, 125, 0.15)'
  };

  // Color configurations for hover effects
  const dangerColors = {
    normal: {
      background: 'linear-gradient(135deg, #dc3545 0%, #b02a37 100%)',
      color: 'white',
      borderColor: '#dc3545',
      boxShadow: '0 3px 10px rgba(220, 53, 69, 0.25)'
    },
    hover: {
      background: 'linear-gradient(135deg, #b02a37 0%, #8b1e2b 100%)',
      color: 'white',
      borderColor: '#8b1e2b',
      boxShadow: '0 6px 20px rgba(220, 53, 69, 0.4)'
    }
  };

  const secondaryColors = {
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
  };

  const dangerHover = useButtonHover(dangerColors);
  const secondaryHover = useButtonHover(secondaryColors);

  return (
    <CModal visible={visible} onClose={onClose}>
      <CModalHeader>
        <CModalTitle>Delete LLM Credential</CModalTitle>
      </CModalHeader>
      <CModalBody>
        <p>Are you sure you want to delete the following credential?</p>
        {credential && (
          <div className="alert alert-warning">
            <strong>Provider:</strong> {credential.provider}<br />
            <strong>Base URL:</strong> {credential.base_url}<br />
            <strong>Models:</strong> {Array.isArray(credential.available_models) 
              ? credential.available_models.join(', ') 
              : credential.available_models || 'None'}
          </div>
        )}
        <p className="text-danger mb-0">
          <strong>Warning:</strong> This action cannot be undone.
        </p>
      </CModalBody>
      <CModalFooter>
        <CButton 
          variant="outline"
          onClick={onClose} 
          disabled={loading}
          style={secondaryButtonStyle}
          onMouseEnter={secondaryHover.onMouseEnter}
          onMouseLeave={secondaryHover.onMouseLeave}
        >
          Cancel
        </CButton>
        <CButton 
          variant="outline"
          onClick={onConfirm} 
          disabled={loading}
          style={dangerButtonStyle}
          onMouseEnter={dangerHover.onMouseEnter}
          onMouseLeave={dangerHover.onMouseLeave}
        >
          {loading ? (
            <>
              <CSpinner size="sm" className="me-2" />
              Deleting...
            </>
          ) : (
            <>
              <FontAwesomeIcon icon={faTrash} className="me-2" />
              Delete Credential
            </>
          )}
        </CButton>
      </CModalFooter>
    </CModal>
  );
};

export default DeleteCredentialModal;

