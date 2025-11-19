import React, { useState, useEffect } from 'react';
import {
  CCard,
  CCardBody,
  CCardHeader,
  CForm,
  CFormLabel,
  CFormSelect,
  CFormTextarea,
  CButton,
  CSpinner,
  CBadge,
  CRow,
  CCol,
  CAlert
} from '@coreui/react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faSave,
  faTrash,
  faToggleOn,
  faToggleOff,
  faPlus,
  faInfoCircle
} from '@fortawesome/free-solid-svg-icons';
import './AgentConfigPanel.scss';

const AgentConfigPanel = ({
  selectedNode,
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

  useEffect(() => {
    if (selectedNode?.mapping_info) {
      // Populate form with existing mapping data
      setFormData({
        llm_credentials_id: selectedNode.mapping_info.llm_credentials_id || '',
        selected_model: selectedNode.mapping_info.selected_model || '',
        preferred_model: selectedNode.mapping_info.preferred_model || '',
        custom_system_prompt: selectedNode.mapping_info.custom_system_prompt || '',
        priority: selectedNode.mapping_info.priority || 1
      });

      // Set available models for current credential
      if (selectedNode.mapping_info.llm_credentials) {
        setAvailableModels(selectedNode.mapping_info.llm_credentials.available_models || []);
      }
    } else {
      // Reset form for unmapped agent
      setFormData({
        llm_credentials_id: '',
        selected_model: '',
        preferred_model: '',
        custom_system_prompt: '',
        priority: 1
      });
      setAvailableModels([]);
    }
  }, [selectedNode]);

  const handleCredentialChange = (e) => {
    const credentialId = parseInt(e.target.value);
    setFormData({ ...formData, llm_credentials_id: credentialId, selected_model: '', preferred_model: '' });

    // Update available models based on selected credential
    const credential = availableCredentials.find(c => c.id === credentialId);
    setAvailableModels(credential?.available_models || []);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaveLoading(true);

    try {
      if (selectedNode.is_mapped) {
        // Update existing mapping
        await onSave(selectedNode.mapping_info.mapping_id, formData);
      } else {
        // Create new mapping
        await onCreate({
          agent_id: selectedNode.agent_id,
          ...formData
        });
      }
    } finally {
      setSaveLoading(false);
    }
  };

  const handleToggle = async () => {
    if (selectedNode.mapping_info?.mapping_id) {
      await onToggleStatus(selectedNode.mapping_info.mapping_id);
    }
  };

  const handleDelete = async () => {
    if (window.confirm('Are you sure you want to delete this agent mapping?')) {
      await onDelete(selectedNode.mapping_info.mapping_id);
    }
  };

  if (!selectedNode) {
    return (
      <CCard className="agent-config-panel">
        <CCardBody className="text-center text-muted py-5">
          <FontAwesomeIcon icon={faInfoCircle} size="3x" className="mb-3" />
          <p>Select an agent from the tree to view or configure its settings</p>
        </CCardBody>
      </CCard>
    );
  }

  return (
    <CCard className="agent-config-panel">
      <CCardHeader className="d-flex justify-content-between align-items-center">
        <div>
          <h5 className="mb-0">{selectedNode.agent_display_name || selectedNode.agent_name}</h5>
          <small className="text-muted">{selectedNode.agent_type}</small>
        </div>
        <div className="d-flex gap-2">
          {selectedNode.is_mapped && (
            <>
              <CBadge 
                color={selectedNode.mapping_info?.is_active ? 'success' : 'danger'}
                className="badge-large"
              >
                {selectedNode.mapping_info?.is_active ? 'Active' : 'Inactive'}
              </CBadge>
            </>
          )}
          {!selectedNode.is_mapped && (
            <CBadge color="secondary" className="badge-large">
              Not Mapped
            </CBadge>
          )}
        </div>
      </CCardHeader>

      <CCardBody>
        {selectedNode.agent_description && (
          <CAlert color="info" className="mb-3">
            <small>{selectedNode.agent_description}</small>
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
                  <option key={cred.id} value={cred.id}>
                    {cred.provider} - {cred.base_url}
                    {cred.is_default && ' (Default)'}
                  </option>
                ))}
              </CFormSelect>
            </CCol>
          </CRow>

          {formData.llm_credentials_id && availableModels.length > 0 && (
            <>
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
            </>
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

          <div className="d-flex justify-content-between align-items-center">
            <div className="d-flex gap-2">
              <CButton
                type="submit"
                color="primary"
                disabled={!formData.llm_credentials_id || saveLoading || loading}
                className="d-flex align-items-center"
              >
                {saveLoading ? (
                  <>
                    <CSpinner size="sm" className="me-2" />
                    Saving...
                  </>
                ) : (
                  <>
                    <FontAwesomeIcon icon={selectedNode.is_mapped ? faSave : faPlus} className="me-2" />
                    {selectedNode.is_mapped ? 'Save Changes' : 'Create Mapping'}
                  </>
                )}
              </CButton>

              {selectedNode.is_mapped && (
                <CButton
                  type="button"
                  color={selectedNode.mapping_info?.is_active ? 'warning' : 'success'}
                  onClick={handleToggle}
                  disabled={loading}
                  className="d-flex align-items-center"
                >
                  <FontAwesomeIcon 
                    icon={selectedNode.mapping_info?.is_active ? faToggleOff : faToggleOn} 
                    className="me-2"
                  />
                  {selectedNode.mapping_info?.is_active ? 'Deactivate' : 'Activate'}
                </CButton>
              )}
            </div>

            {selectedNode.is_mapped && (
              <CButton
                type="button"
                color="danger"
                onClick={handleDelete}
                disabled={loading}
                className="d-flex align-items-center"
              >
                <FontAwesomeIcon icon={faTrash} className="me-2" />
                Delete Mapping
              </CButton>
            )}
          </div>
        </CForm>

        {selectedNode.is_mapped && selectedNode.mapping_info && (
          <div className="mt-4 pt-3 border-top">
            <h6 className="mb-2">Mapping Information</h6>
            <CRow>
              <CCol md={6}>
                <small className="text-muted d-block">Created At</small>
                <small>{formatDate(selectedNode.mapping_info.created_at)}</small>
              </CCol>
              <CCol md={6}>
                <small className="text-muted d-block">Updated At</small>
                <small>{formatDate(selectedNode.mapping_info.updated_at)}</small>
              </CCol>
            </CRow>
            <CRow className="mt-2">
              <CCol md={6}>
                <small className="text-muted d-block">Created By</small>
                <small>{selectedNode.mapping_info.created_by || 'N/A'}</small>
              </CCol>
              <CCol md={6}>
                <small className="text-muted d-block">Updated By</small>
                <small>{selectedNode.mapping_info.updated_by || 'N/A'}</small>
              </CCol>
            </CRow>
          </div>
        )}
      </CCardBody>
    </CCard>
  );
};

export default AgentConfigPanel;

