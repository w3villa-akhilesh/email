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
import { faSave, faTrash } from "@fortawesome/free-solid-svg-icons";
import { useButtonHover } from '../../hooks/useButtonHover';
import CompaniesForm from './CompaniesForm';

const CompaniesModals = ({
  modals,
  onCloseModals,
  selectedCompany,
  formData,
  formErrors,
  submitLoading,
  onFieldChange,
  onCreateSubmit,
  onEditSubmit,
  onDeleteSubmit
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

  const secondaryButtonStyle = {
    ...buttonStyle,
    border: '2px solid #6c757d',
    color: '#6c757d',
    backgroundColor: 'rgba(108, 117, 125, 0.08)',
    boxShadow: '0 3px 10px rgba(108, 117, 125, 0.15)'
  };

  const dangerButtonStyle = {
    ...buttonStyle,
    border: '2px solid #dc3545',
    color: 'white',
    background: 'linear-gradient(135deg, #dc3545 0%, #b02a37 100%)',
    boxShadow: '0 3px 10px rgba(220, 53, 69, 0.25)'
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

  const primaryHover = useButtonHover(primaryColors);
  const secondaryHover = useButtonHover(secondaryColors);
  const dangerHover = useButtonHover(dangerColors);

  return (
    <>
      {/* Create Company Modal */}
      <CModal
        visible={modals.showCreateModal}
        onClose={() => onCloseModals('create')}
        size="lg"
        backdrop="static"
      >
        <CModalHeader>
          <CModalTitle>Add New Company</CModalTitle>
        </CModalHeader>
        <CModalBody>
          <CompaniesForm
            formData={formData}
            formErrors={formErrors}
            onFieldChange={onFieldChange}
            isEditMode={false}
          />
        </CModalBody>
        <CModalFooter>
          <CButton
            variant="outline"
            onClick={() => onCloseModals('create')}
            disabled={submitLoading}
            style={secondaryButtonStyle}
            onMouseEnter={secondaryHover.onMouseEnter}
            onMouseLeave={secondaryHover.onMouseLeave}
          >
            Cancel
          </CButton>
          <CButton
            variant="outline"
            onClick={onCreateSubmit}
            disabled={submitLoading}
            style={primaryButtonStyle}
            onMouseEnter={primaryHover.onMouseEnter}
            onMouseLeave={primaryHover.onMouseLeave}
          >
            {submitLoading ? (
              <>
                <CSpinner size="sm" className="me-2" />
                Creating...
              </>
            ) : (
              <>
                <FontAwesomeIcon icon={faSave} className="me-2" />
                Create Company
              </>
            )}
          </CButton>
        </CModalFooter>
      </CModal>

      {/* Edit Company Modal */}
      <CModal
        visible={modals.showEditModal}
        onClose={() => onCloseModals('edit')}
        size="lg"
        backdrop="static"
      >
        <CModalHeader>
          <CModalTitle>Edit Company</CModalTitle>
        </CModalHeader>
        <CModalBody>
          <CompaniesForm
            formData={formData}
            formErrors={formErrors}
            onFieldChange={onFieldChange}
            isEditMode={true}
          />
        </CModalBody>
        <CModalFooter>
          <CButton
            variant="outline"
            onClick={() => onCloseModals('edit')}
            disabled={submitLoading}
            style={secondaryButtonStyle}
            onMouseEnter={secondaryHover.onMouseEnter}
            onMouseLeave={secondaryHover.onMouseLeave}
          >
            Cancel
          </CButton>
          <CButton
            variant="outline"
            onClick={onEditSubmit}
            disabled={submitLoading}
            style={primaryButtonStyle}
            onMouseEnter={primaryHover.onMouseEnter}
            onMouseLeave={primaryHover.onMouseLeave}
          >
            {submitLoading ? (
              <>
                <CSpinner size="sm" className="me-2" />
                Updating...
              </>
            ) : (
              <>
                <FontAwesomeIcon icon={faSave} className="me-2" />
                Update Company
              </>
            )}
          </CButton>
        </CModalFooter>
      </CModal>

      {/* Delete Company Modal */}
      <CModal
        visible={modals.showDeleteModal}
        onClose={() => onCloseModals('delete')}
        size="md"
      >
        <CModalHeader>
          <CModalTitle>Delete Company</CModalTitle>
        </CModalHeader>
        <CModalBody>
          <div className="text-center">
            <div className="mb-3">
              <i className="fas fa-exclamation-triangle text-warning" style={{ fontSize: '3rem' }}></i>
            </div>
            <h5>Are you sure?</h5>
            <p className="text-muted">
              You are about to delete the company <strong>"{selectedCompany?.name}"</strong>.
              This action cannot be undone.
            </p>
            {selectedCompany && (
              <div className="alert alert-warning">
                <small>
                  <strong>Warning:</strong> This will also affect any related LLM credentials 
                  and agent mappings associated with this company.
                </small>
              </div>
            )}
          </div>
        </CModalBody>
        <CModalFooter>
          <CButton
            variant="outline"
            onClick={() => onCloseModals('delete')}
            disabled={submitLoading}
            style={secondaryButtonStyle}
            onMouseEnter={secondaryHover.onMouseEnter}
            onMouseLeave={secondaryHover.onMouseLeave}
          >
            Cancel
          </CButton>
          <CButton
            variant="outline"
            onClick={onDeleteSubmit}
            disabled={submitLoading}
            style={dangerButtonStyle}
            onMouseEnter={dangerHover.onMouseEnter}
            onMouseLeave={dangerHover.onMouseLeave}
          >
            {submitLoading ? (
              <>
                <CSpinner size="sm" className="me-2" />
                Deleting...
              </>
            ) : (
              <>
                <FontAwesomeIcon icon={faTrash} className="me-2" />
                Delete Company
              </>
            )}
          </CButton>
        </CModalFooter>
      </CModal>
    </>
  );
};

export default CompaniesModals;
