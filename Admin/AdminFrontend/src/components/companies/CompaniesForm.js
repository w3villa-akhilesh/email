import React from 'react';
import {
  CForm,
  CFormInput,
  CFormLabel,
  CFormTextarea,
  CFormSwitch,
  CRow,
  CCol,
  CFormFeedback
} from '@coreui/react';

const CompaniesForm = ({
  formData,
  formErrors,
  onFieldChange,
  isEditMode = false
}) => {
  return (
    <CForm>
      <CRow className="mb-3">
        <CCol md={6}>
          <CFormLabel htmlFor="id">
            Company ID <span className="text-danger">*</span>
          </CFormLabel>
          <CFormInput
            type="number"
            id="id"
            placeholder="Enter company ID"
            value={formData.id}
            onChange={(e) => onFieldChange('id', e.target.value)}
            invalid={!!formErrors.id}
            disabled={isEditMode}
          />
          {formErrors.id && (
            <CFormFeedback invalid>{formErrors.id}</CFormFeedback>
          )}
          <small className="form-text text-muted">
            {isEditMode ? 'Company ID cannot be changed' : 'Unique numeric identifier for the company'}
          </small>
        </CCol>
        
        <CCol md={6}>
          <CFormLabel htmlFor="name">
            Company Name <span className="text-danger">*</span>
          </CFormLabel>
          <CFormInput
            type="text"
            id="name"
            placeholder="Enter company name"
            value={formData.name}
            onChange={(e) => onFieldChange('name', e.target.value)}
            invalid={!!formErrors.name}
            maxLength={255}
          />
          {formErrors.name && (
            <CFormFeedback invalid>{formErrors.name}</CFormFeedback>
          )}
        </CCol>
      </CRow>

      <CRow className="mb-3">
        <CCol md={6}>
          <CFormLabel htmlFor="origin">
            Origin <span className="text-danger">*</span>
          </CFormLabel>
          <CFormInput
            type="text"
            id="origin"
            placeholder="e.g., company.com"
            value={formData.origin}
            onChange={(e) => onFieldChange('origin', e.target.value)}
            invalid={!!formErrors.origin}
            maxLength={255}
          />
          {formErrors.origin && (
            <CFormFeedback invalid>{formErrors.origin}</CFormFeedback>
          )}
          <small className="form-text text-muted">
            Domain or identifier for the company
          </small>
        </CCol>
      </CRow>

      <CRow className="mb-3">
        <CCol md={6}>
          <CFormLabel htmlFor="company_id">
            External Company ID
          </CFormLabel>
          <CFormInput
            type="text"
            id="company_id"
            placeholder="Enter external company ID (optional)"
            value={formData.company_id}
            onChange={(e) => onFieldChange('company_id', e.target.value)}
            invalid={!!formErrors.company_id}
            maxLength={100}
          />
          {formErrors.company_id && (
            <CFormFeedback invalid>{formErrors.company_id}</CFormFeedback>
          )}
          <small className="form-text text-muted">
            External company identifier (optional)
          </small>
        </CCol>
        
        <CCol md={6} className="d-flex align-items-end">
          <div className="mb-2">
            <CFormSwitch
              id="is_active"
              label="Active Status"
              checked={formData.is_active}
              onChange={(e) => onFieldChange('is_active', e.target.checked)}
            />
            <small className="form-text text-muted">
              {formData.is_active ? 'Company is active' : 'Company is inactive'}
            </small>
          </div>
        </CCol>
      </CRow>

      <CRow className="mb-3">
        <CCol md={12}>
          <CFormLabel htmlFor="description">
            Description
          </CFormLabel>
          <CFormTextarea
            id="description"
            rows={4}
            placeholder="Enter company description (optional)"
            value={formData.description}
            onChange={(e) => onFieldChange('description', e.target.value)}
            invalid={!!formErrors.description}
            maxLength={1000}
          />
          {formErrors.description && (
            <CFormFeedback invalid>{formErrors.description}</CFormFeedback>
          )}
          <small className="form-text text-muted">
            {formData.description.length}/1000 characters
          </small>
        </CCol>
      </CRow>

      {isEditMode && (
        <div className="alert alert-info">
          <small>
            <strong>Note:</strong> Changes to the origin field should be made carefully 
            as it may affect existing integrations.
          </small>
        </div>
      )}
    </CForm>
  );
};

export default CompaniesForm;
