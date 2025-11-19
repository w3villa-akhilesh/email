import React, { useState, useEffect } from 'react';
import {
  CModal,
  CModalHeader,
  CModalTitle,
  CModalBody,
  CModalFooter,
  CButton,
  CSpinner,
  CForm,
  CFormLabel,
  CFormSelect,
  CFormTextarea,
  CRow,
  CCol,
  CAlert,
  CBadge
} from '@coreui/react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faSave,
  faTrash,
  faPlus,
  faToggleOn,
  faToggleOff
} from '@fortawesome/free-solid-svg-icons';
import { useButtonHover } from '../../hooks/useButtonHover';

const AgentConfigModal = ({
  visible,
  onClose,
  selectedAgent,
  availableCredentials,
  onSave,
  onDelete,
  onToggleStatus,
  onCreate,
  loading
}) => {
  const [formData, setFormData] = useState({
    llm_credentials_id: '',
    selected_model: '',
    preferred_model: '',
    custom_system_prompt: '',
    priority: 1
  });

  const [availableModels, setAvailableModels] = useState([]);
  const [saveLoading, setSaveLoading] = useState(false);

  // Button styles matching CompaniesModals
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

  const deactivateButtonStyle = {
    ...buttonStyle,
    border: '2px solid #6c757d',
    color: 'white',
    background: 'linear-gradient(135deg, #6c757d 0%, #545b62 100%)',
    boxShadow: '0 3px 10px rgba(108, 117, 125, 0.25)'
  };

  const successButtonStyle = {
    ...buttonStyle,
    border: '2px solid #28a745',
    color: 'white',
    background: 'linear-gradient(135deg, #28a745 0%, #218838 100%)',
    boxShadow: '0 3px 10px rgba(40, 167, 69, 0.25)'
  };

  // Hover colors
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

  const deactivateColors = {
    normal: {
      background: 'linear-gradient(135deg, #6c757d 0%, #545b62 100%)',
      color: 'white',
      borderColor: '#6c757d',
      boxShadow: '0 3px 10px rgba(108, 117, 125, 0.25)'
    },
    hover: {
      background: 'linear-gradient(135deg, #545b62 0%, #3d4349 100%)',
      color: 'white',
      borderColor: '#3d4349',
      boxShadow: '0 6px 20px rgba(108, 117, 125, 0.4)'
    }
  };

  const successColors = {
    normal: {
      background: 'linear-gradient(135deg, #28a745 0%, #218838 100%)',
      color: 'white',
      borderColor: '#28a745',
      boxShadow: '0 3px 10px rgba(40, 167, 69, 0.25)'
    },
    hover: {
      background: 'linear-gradient(135deg, #218838 0%, #1e7e34 100%)',
      color: 'white',
      borderColor: '#1e7e34',
      boxShadow: '0 6px 20px rgba(40, 167, 69, 0.4)'
    }
  };

  const primaryHover = useButtonHover(primaryColors);
  const secondaryHover = useButtonHover(secondaryColors);
  const dangerHover = useButtonHover(dangerColors);
  const deactivateHover = useButtonHover(deactivateColors);
  const successHover = useButtonHover(successColors);

  useEffect(() => {
    if (selectedAgent?.mapping_info) {
      setFormData({
        llm_credentials_id: selectedAgent.mapping_info.llm_credentials_id || '',
        selected_model: selectedAgent.mapping_info.selected_model || '',
        preferred_model: selectedAgent.mapping_info.preferred_model || '',
        custom_system_prompt: selectedAgent.mapping_info.custom_system_prompt || '',
        priority: selectedAgent.mapping_info.priority || 1
      });

      if (selectedAgent.mapping_info.llm_credentials) {
        setAvailableModels(selectedAgent.mapping_info.llm_credentials.available_models || []);
      }
    } else {
      setFormData({
        llm_credentials_id: '',
        selected_model: '',
        preferred_model: '',
        custom_system_prompt: '',
        priority: 1
      });
      setAvailableModels([]);
    }
  }, [selectedAgent]);

  const handleCredentialChange = (e) => {
    const credentialId = parseInt(e.target.value);
    setFormData({ ...formData, llm_credentials_id: credentialId, selected_model: '', preferred_model: '' });

    const credential = availableCredentials.find(c => c.id === credentialId);
    setAvailableModels(credential?.available_models || []);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaveLoading(true);

    try {
      if (selectedAgent.is_mapped) {
        await onSave(selectedAgent.mapping_info.mapping_id, formData);
      } else {
        await onCreate({
          agent_id: selectedAgent.agent_id,
          ...formData
        });
      }
      onClose();
    } finally {
      setSaveLoading(false);
    }
  };

  const handleToggle = async () => {
    if (selectedAgent.mapping_info?.mapping_id) {
      await onToggleStatus(selectedAgent.mapping_info.mapping_id);
      onClose();
    }
  };

  const handleDelete = async () => {
    if (window.confirm(`Are you sure you want to clear the agent mapping for "${selectedAgent.agent_display_name || selectedAgent.agent_name}"? This will remove all configuration settings for this agent.`)) {
      await onDelete(selectedAgent.mapping_info.mapping_id);
      onClose();
    }
  };

  // Format date function (matching LLM Credential Details)
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return 'Invalid Date';
    }
  };

  if (!selectedAgent) return null;

  const isNew = !selectedAgent.is_mapped;

  return (
    <CModal
      visible={visible}
      onClose={onClose}
      size="lg"
      backdrop="static"
    >
      <CModalHeader>
        <CModalTitle>
          {isNew ? 'Create' : 'Configure'} Agent Mapping
        </CModalTitle>
      </CModalHeader>
      <CModalBody>
        <div className="mb-3">
          <h5 className="mb-1">{selectedAgent.agent_display_name || selectedAgent.agent_name}</h5>
          <div className="d-flex align-items-center gap-2">
            <CBadge color="info">{selectedAgent.agent_type}</CBadge>
            {selectedAgent.is_mapped && (
              <CBadge color={selectedAgent.mapping_info?.is_active ? 'success' : 'danger'}>
                {selectedAgent.mapping_info?.is_active ? 'Active' : 'Inactive'}
              </CBadge>
            )}
            {!selectedAgent.is_mapped && (
              <CBadge color="secondary">Not Mapped</CBadge>
            )}
          </div>
          {selectedAgent.agent_description && (
            <p className="text-muted mt-2 mb-0">
              <small>{selectedAgent.agent_description}</small>
            </p>
          )}
        </div>

        {/* Warning when mapped credential is inactive */}
        {selectedAgent.is_mapped && selectedAgent.mapping_info?.llm_credentials && 
         !selectedAgent.mapping_info.llm_credentials.is_active && (
          <CAlert color="warning" className="mb-3">
            <strong>⚠️ Warning:</strong> The currently mapped LLM credential 
            <strong> "{selectedAgent.mapping_info.llm_credentials.provider}" </strong>
            is currently <strong>INACTIVE</strong>. 
            This agent will not function properly until the credential is activated or you select a different active credential.
          </CAlert>
        )}

        <CForm onSubmit={handleSubmit}>
          <CRow className="mb-3">
            <CCol md={12}>
              <CFormLabel htmlFor="llm_credentials">
                LLM Credentials <span className="text-danger">*</span>
              </CFormLabel>
              <CFormSelect
                id="llm_credentials"
                value={formData.llm_credentials_id}
                onChange={handleCredentialChange}
                required
                disabled={loading}
              >
                <option value="">Select LLM Credentials</option>
                {availableCredentials.map((cred) => (
                  <option 
                    key={cred.id} 
                    value={cred.id}
                    style={!cred.is_active ? { color: '#dc3545', fontStyle: 'italic' } : {}}
                  >
                    {cred.provider} - {cred.base_url}
                    {cred.is_default && ' (Default)'}
                    {!cred.is_active && ' [INACTIVE]'}
                  </option>
                ))}
              </CFormSelect>
              <small className="text-muted">
                {availableCredentials.some(c => !c.is_active) && (
                  <span className="text-danger">Note: Credentials marked as [INACTIVE] are currently disabled</span>
                )}
              </small>
            </CCol>
          </CRow>

          {formData.llm_credentials_id && availableModels.length > 0 && (
            <CRow className="mb-3">
              <CCol md={6}>
                <CFormLabel htmlFor="selected_model">Selected Model</CFormLabel>
                <CFormSelect
                  id="selected_model"
                  value={formData.selected_model}
                  onChange={(e) => setFormData({ ...formData, selected_model: e.target.value })}
                  disabled={loading}
                >
                  <option value="">Select Model</option>
                  {availableModels.map((model, idx) => (
                    <option key={idx} value={model}>
                      {model}
                    </option>
                  ))}
                </CFormSelect>
              </CCol>

              <CCol md={6}>
                <CFormLabel htmlFor="preferred_model">Preferred Model</CFormLabel>
                <CFormSelect
                  id="preferred_model"
                  value={formData.preferred_model}
                  onChange={(e) => setFormData({ ...formData, preferred_model: e.target.value })}
                  disabled={loading}
                >
                  <option value="">Select Model</option>
                  {availableModels.map((model, idx) => (
                    <option key={idx} value={model}>
                      {model}
                    </option>
                  ))}
                </CFormSelect>
              </CCol>
            </CRow>
          )}

          <CRow className="mb-3">
            <CCol md={12}>
              <CFormLabel htmlFor="custom_system_prompt">Custom System Prompt</CFormLabel>
              <CFormTextarea
                id="custom_system_prompt"
                rows={4}
                value={formData.custom_system_prompt}
                onChange={(e) => setFormData({ ...formData, custom_system_prompt: e.target.value })}
                placeholder="Enter custom system prompt for this agent..."
                disabled={loading}
              />
              <small className="text-muted">
                Optional: Override the default system prompt for this company
              </small>
            </CCol>
          </CRow>

          {selectedAgent.is_mapped && selectedAgent.mapping_info && (
            <CAlert color="info">
              <small>
                <strong>Created:</strong> {formatDate(selectedAgent.mapping_info.created_at)}<br/>
                <strong>Created By:</strong> {selectedAgent.mapping_info.created_by || 'N/A'}<br/>
                <strong>Updated:</strong> {formatDate(selectedAgent.mapping_info.updated_at)}<br/>
                <strong>Updated By:</strong> {selectedAgent.mapping_info.updated_by || 'N/A'}
              </small>
            </CAlert>
          )}
        </CForm>
      </CModalBody>
      <CModalFooter className="d-flex justify-content-between">
        <div>
          {selectedAgent.is_mapped && (
            <>
              <CButton
                variant="outline"
                onClick={handleToggle}
                disabled={loading || saveLoading}
                style={selectedAgent.mapping_info?.is_active ? deactivateButtonStyle : successButtonStyle}
                onMouseEnter={selectedAgent.mapping_info?.is_active ? deactivateHover.onMouseEnter : successHover.onMouseEnter}
                onMouseLeave={selectedAgent.mapping_info?.is_active ? deactivateHover.onMouseLeave : successHover.onMouseLeave}
                className="me-2"
              >
                <FontAwesomeIcon 
                  icon={selectedAgent.mapping_info?.is_active ? faToggleOff : faToggleOn} 
                  className="me-2"
                />
                {selectedAgent.mapping_info?.is_active ? 'Deactivate' : 'Activate'}
              </CButton>
              <CButton
                variant="outline"
                onClick={handleDelete}
                disabled={loading || saveLoading}
                style={dangerButtonStyle}
                onMouseEnter={dangerHover.onMouseEnter}
                onMouseLeave={dangerHover.onMouseLeave}
              >
                <FontAwesomeIcon icon={faTrash} className="me-2" />
                Clear Mapping
              </CButton>
            </>
          )}
        </div>
        <div>
          <CButton
            variant="outline"
            onClick={onClose}
            disabled={loading || saveLoading}
            style={secondaryButtonStyle}
            onMouseEnter={secondaryHover.onMouseEnter}
            onMouseLeave={secondaryHover.onMouseLeave}
            className="me-2"
          >
            Cancel
          </CButton>
          <CButton
            variant="outline"
            onClick={handleSubmit}
            disabled={!formData.llm_credentials_id || loading || saveLoading}
            style={primaryButtonStyle}
            onMouseEnter={primaryHover.onMouseEnter}
            onMouseLeave={primaryHover.onMouseLeave}
          >
            {saveLoading ? (
              <>
                <CSpinner size="sm" className="me-2" />
                Saving...
              </>
            ) : (
              <>
                <FontAwesomeIcon icon={isNew ? faPlus : faSave} className="me-2" />
                {isNew ? 'Create Mapping' : 'Save Changes'}
              </>
            )}
          </CButton>
        </div>
      </CModalFooter>
    </CModal>
  );
};

export default AgentConfigModal;

