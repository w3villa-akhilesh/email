import React, { useState, useEffect } from 'react';
import {
  CModal,
  CModalHeader,
  CModalTitle,
  CModalBody,
  CModalFooter,
  CButton,
  CForm,
  CFormInput,
  CFormLabel,
  CFormSwitch,
  CFormSelect,
  CRow,
  CCol,
  CSpinner
} from '@coreui/react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faSave } from '@fortawesome/free-solid-svg-icons';
import { useButtonHover } from '../../hooks/useButtonHover';

const LLMCredentialEditModal = ({ 
  visible, 
  onClose, 
  onSubmit, 
  credential,
  loading = false 
}) => {
  // Form data state
  const [formData, setFormData] = useState({
    provider: '',
    base_url: '',
    api_key: '',
    available_models: [],
    is_default: false,
    max_tokens: '',
    temperature: '',
    tts_service: '',
    cartesia_api_key: '',
    deepgram_api_key: '',
    openai_api_key: '',
    is_crm_flow_active: false,
    crm_accounts_ids: '',
    tags: ''
  });

  // Populate form when credential changes
  useEffect(() => {
    if (credential) {
      setFormData({
        provider: credential.provider || '',
        base_url: credential.base_url || '',
        api_key: credential.api_key || '',
        available_models: credential.available_models || [],
        is_default: credential.is_default || false,
        max_tokens: credential.max_tokens || '',
        temperature: credential.temperature || '',
        tts_service: credential.tts_service || '',
        cartesia_api_key: credential.cartesia_api_key || '',
        deepgram_api_key: credential.deepgram_api_key || '',
        openai_api_key: credential.openai_api_key || '',
        is_crm_flow_active: credential.is_crm_flow_active || false,
        crm_accounts_ids: credential.crm_accounts_ids || '',
        tags: credential.tags || ''
      });
    }
  }, [credential]);

  // Modern button styles (matching Company modals)
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

  // Color configurations for hover effects (matching Company modals)
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

  // Button hover hooks
  const primaryHover = useButtonHover(primaryColors);
  const secondaryHover = useButtonHover(secondaryColors);

  // Handle form input changes
  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // Handle models input (comma-separated)
  const handleModelsChange = (value) => {
    const models = value.split(',').map(model => model.trim()).filter(model => model);
    setFormData(prev => ({
      ...prev,
      available_models: models
    }));
  };

  // Handle form submission
  const handleEditSubmit = async (e) => {
    e.preventDefault();
    
    try {
      // Prepare data for API
      const updateData = {
        ...formData,
        max_tokens: formData.max_tokens ? parseInt(formData.max_tokens) : null,
        temperature: formData.temperature ? formData.temperature.toString() : null,
        tts_service: formData.tts_service && formData.tts_service.trim() !== '' ? formData.tts_service.trim() : null,
        cartesia_api_key: formData.cartesia_api_key && formData.cartesia_api_key.trim() !== '' ? formData.cartesia_api_key.trim() : null,
        deepgram_api_key: formData.deepgram_api_key && formData.deepgram_api_key.trim() !== '' ? formData.deepgram_api_key.trim() : null,
        openai_api_key: formData.openai_api_key && formData.openai_api_key.trim() !== '' ? formData.openai_api_key.trim() : null
      };
      
      await onSubmit(updateData);
    } catch (error) {
      console.error('Error updating credential:', error);
      throw error; // Re-throw to let parent handle
    }
  };

  return (
    <CModal visible={visible} onClose={onClose} size="lg">
      <CModalHeader>
        <CModalTitle>Edit LLM Credential</CModalTitle>
      </CModalHeader>
      <CForm onSubmit={handleEditSubmit}>
        <CModalBody>
          <CRow>
            <CCol md={6}>
              <div className="mb-3">
                <CFormLabel>Provider <span className="text-danger">*</span></CFormLabel>
                <CFormInput
                  type="text"
                  value={formData.provider}
                  onChange={(e) => handleInputChange('provider', e.target.value)}
                  required
                />
              </div>
            </CCol>
            <CCol md={6}>
              <div className="mb-3">
                <CFormLabel>Base URL <span className="text-danger">*</span></CFormLabel>
                <CFormInput
                  type="url"
                  value={formData.base_url}
                  onChange={(e) => handleInputChange('base_url', e.target.value)}
                  required
                />
              </div>
            </CCol>
          </CRow>

          <div className="mb-3">
            <CFormLabel>API Key <span className="text-danger">*</span></CFormLabel>
            <CFormInput
              type="password"
              value={formData.api_key}
              onChange={(e) => handleInputChange('api_key', e.target.value)}
              required
            />
          </div>

          <div className="mb-3">
            <CFormLabel>Available Models (comma-separated)</CFormLabel>
            <CFormInput
              type="text"
              value={formData.available_models.join(', ')}
              onChange={(e) => handleModelsChange(e.target.value)}
              placeholder="gpt-4o, gpt-4o-mini, claude-3-sonnet"
            />
          </div>

          <CRow>
            <CCol md={6}>
              <div className="mb-3">
                <CFormLabel>Max Tokens</CFormLabel>
                <CFormInput
                  type="number"
                  value={formData.max_tokens}
                  onChange={(e) => handleInputChange('max_tokens', e.target.value)}
                  min="1"
                />
              </div>
            </CCol>
            <CCol md={6}>
              <div className="mb-3">
                <CFormLabel>Temperature</CFormLabel>
                <CFormInput
                  type="number"
                  step="0.1"
                  min="0"
                  max="2"
                  value={formData.temperature}
                  onChange={(e) => handleInputChange('temperature', e.target.value)}
                />
              </div>
            </CCol>
          </CRow>

          <div className="mb-3">
            <CFormLabel>TTS Service</CFormLabel>
            <CFormSelect
              value={formData.tts_service}
              onChange={(e) => handleInputChange('tts_service', e.target.value)}
            >
              <option value="">Select TTS Service (Optional)</option>
              <option value="tts_openai_key">TTS OpenAI Key</option>
              <option value="tts_cartesia_key">TTS Cartesia Key</option>
            </CFormSelect>
            <small className="text-muted">Text-to-Speech service provider</small>
          </div>

          <CRow>
            <CCol md={4}>
              <div className="mb-3">
                <CFormLabel>Cartesia API Key</CFormLabel>
                <CFormInput
                  type="password"
                  value={formData.cartesia_api_key}
                  onChange={(e) => handleInputChange('cartesia_api_key', e.target.value)}
                  placeholder="Enter Cartesia API key"
                />
              </div>
            </CCol>
            <CCol md={4}>
              <div className="mb-3">
                <CFormLabel>Deepgram API Key</CFormLabel>
                <CFormInput
                  type="password"
                  value={formData.deepgram_api_key}
                  onChange={(e) => handleInputChange('deepgram_api_key', e.target.value)}
                  placeholder="Enter Deepgram API key"
                />
              </div>
            </CCol>
            <CCol md={4}>
              <div className="mb-3">
                <CFormLabel>OpenAI API Key</CFormLabel>
                <CFormInput
                  type="password"
                  value={formData.openai_api_key}
                  onChange={(e) => handleInputChange('openai_api_key', e.target.value)}
                  placeholder="Enter OpenAI API key"
                />
              </div>
            </CCol>
          </CRow>

          <div className="mb-3">
            <CFormLabel>CRM Account IDs</CFormLabel>
            <CFormInput
              type="text"
              value={formData.crm_accounts_ids}
              onChange={(e) => handleInputChange('crm_accounts_ids', e.target.value)}
              placeholder="account1,account2,account3"
            />
          </div>

          <div className="mb-3">
            <CFormLabel>Tags</CFormLabel>
            <CFormInput
              type="text"
              value={formData.tags}
              onChange={(e) => handleInputChange('tags', e.target.value)}
              placeholder="production, primary, backup"
            />
          </div>

          <CRow>
            <CCol md={6}>
              <div className="mb-3">
                <CFormSwitch
                  id="isDefault"
                  label="Default Credential"
                  checked={formData.is_default}
                  onChange={(e) => handleInputChange('is_default', e.target.checked)}
                />
                <small className="form-text text-muted">
                  {formData.is_default ? 'This is the default credential' : 'Not the default credential'}
                </small>
              </div>
            </CCol>
            <CCol md={6}>
              <div className="mb-3">
                <CFormSwitch
                  id="isCrmFlowActive"
                  label="CRM Flow Active"
                  checked={formData.is_crm_flow_active}
                  onChange={(e) => handleInputChange('is_crm_flow_active', e.target.checked)}
                />
                <small className="form-text text-muted">
                  {formData.is_crm_flow_active ? 'CRM flow is enabled' : 'CRM flow is disabled'}
                </small>
              </div>
            </CCol>
          </CRow>
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
            type="submit"
            disabled={loading}
            style={primaryButtonStyle}
            onMouseEnter={primaryHover.onMouseEnter}
            onMouseLeave={primaryHover.onMouseLeave}
          >
            {loading ? (
              <>
                <CSpinner size="sm" className="me-2" />
                Updating...
              </>
            ) : (
              <>
                <FontAwesomeIcon icon={faSave} className="me-2" />
                Update Credential
              </>
            )}
          </CButton>
        </CModalFooter>
      </CForm>
    </CModal>
  );
};

export default LLMCredentialEditModal;
