import React, { useState } from 'react';
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
  CFormTextarea,
  CFormCheck,
  CFormSelect,
  CRow,
  CCol,
  CSpinner,
  CAlert
} from '@coreui/react';
import { buttonStyles, hoverColors } from '../../utils/commonStyles';
import { useButtonHover } from '../../hooks/useButtonHover';

const AddCredentialModal = ({ 
  visible, 
  onClose, 
  onSubmit, 
  companyId,
  loading = false 
}) => {
  // Button hover effects
  const primaryHover = useButtonHover(hoverColors.primary);
  const secondaryHover = useButtonHover(hoverColors.secondary);
  const [formData, setFormData] = useState({
    provider: '',
    base_url: '',
    api_key: '',
    available_models: '',
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

  const [errors, setErrors] = useState({});

  // Handle input changes
  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
    
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({
        ...prev,
        [field]: ''
      }));
    }
  };

  // Validate form
  const validateForm = () => {
    const newErrors = {};

    if (!formData.provider.trim()) {
      newErrors.provider = 'Provider is required';
    }

    if (!formData.base_url.trim()) {
      newErrors.base_url = 'Base URL is required';
    } else {
      try {
        new URL(formData.base_url);
      } catch {
        newErrors.base_url = 'Please enter a valid URL';
      }
    }

    if (!formData.api_key.trim()) {
      newErrors.api_key = 'API Key is required';
    }

    if (!formData.available_models.trim()) {
      newErrors.available_models = 'At least one model is required';
    }

    if (formData.max_tokens && (isNaN(formData.max_tokens) || parseInt(formData.max_tokens) < 1)) {
      newErrors.max_tokens = 'Max tokens must be a positive number';
    }

    if (formData.temperature && (isNaN(formData.temperature) || parseFloat(formData.temperature) < 0 || parseFloat(formData.temperature) > 2)) {
      newErrors.temperature = 'Temperature must be between 0 and 2';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    // Prepare data for API
    const submitData = {
      company_id: companyId,
      provider: formData.provider.trim(),
      base_url: formData.base_url.trim(),
      api_key: formData.api_key.trim(),
      available_models: formData.available_models.split(',').map(model => model.trim()).filter(model => model),
      is_default: formData.is_default,
      max_tokens: formData.max_tokens ? parseInt(formData.max_tokens) : null,
      temperature: formData.temperature ? formData.temperature.toString() : null, // Convert to string
      tts_service: formData.tts_service && formData.tts_service.trim() !== '' ? formData.tts_service.trim() : null,
      cartesia_api_key: formData.cartesia_api_key.trim() || null,
      deepgram_api_key: formData.deepgram_api_key.trim() || null,
      openai_api_key: formData.openai_api_key.trim() || null,
      is_active: true, // New credentials are active by default
      is_crm_flow_active: formData.is_crm_flow_active,
      crm_accounts_ids: formData.crm_accounts_ids.trim() || null,
      tags: formData.tags.trim() || null
    };

    try {
      await onSubmit(submitData);
      handleClose();
    } catch (error) {
      console.error('Error submitting form:', error);
    }
  };

  // Handle modal close
  const handleClose = () => {
    setFormData({
      provider: '',
      base_url: '',
      api_key: '',
      available_models: '',
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
    setErrors({});
    onClose();
  };

  return (
    <CModal visible={visible} onClose={handleClose} size="lg" className="add-credential-modal">
      <CModalHeader>
        <CModalTitle>Add New LLM Credential</CModalTitle>
      </CModalHeader>
      
      <CForm onSubmit={handleSubmit}>
        <CModalBody>
          <CRow>
            <CCol md={6}>
              <div className="mb-3">
                <CFormLabel>Provider <span className="text-danger">*</span></CFormLabel>
                <CFormInput
                  type="text"
                  value={formData.provider}
                  onChange={(e) => handleInputChange('provider', e.target.value)}
                  placeholder="e.g., OpenAI, Anthropic, Google"
                  invalid={!!errors.provider}
                />
                {errors.provider && (
                  <div className="invalid-feedback d-block">{errors.provider}</div>
                )}
              </div>
            </CCol>
            <CCol md={6}>
              <div className="mb-3">
                <CFormLabel>Base URL <span className="text-danger">*</span></CFormLabel>
                <CFormInput
                  type="url"
                  value={formData.base_url}
                  onChange={(e) => handleInputChange('base_url', e.target.value)}
                  placeholder="https://api.openai.com/v1"
                  invalid={!!errors.base_url}
                />
                {errors.base_url && (
                  <div className="invalid-feedback d-block">{errors.base_url}</div>
                )}
              </div>
            </CCol>
          </CRow>

          <div className="mb-3">
            <CFormLabel>API Key <span className="text-danger">*</span></CFormLabel>
            <CFormInput
              type="password"
              value={formData.api_key}
              onChange={(e) => handleInputChange('api_key', e.target.value)}
              placeholder="Enter your API key"
              invalid={!!errors.api_key}
            />
            {errors.api_key && (
              <div className="invalid-feedback d-block">{errors.api_key}</div>
            )}
          </div>

          <div className="mb-3">
            <CFormLabel>Available Models <span className="text-danger">*</span></CFormLabel>
            <CFormInput
              type="text"
              value={formData.available_models}
              onChange={(e) => handleInputChange('available_models', e.target.value)}
              placeholder="gpt-4o, gpt-4o-mini, claude-3-sonnet (comma-separated)"
              invalid={!!errors.available_models}
            />
            {errors.available_models && (
              <div className="invalid-feedback d-block">{errors.available_models}</div>
            )}
            <small className="text-muted">Enter model names separated by commas</small>
          </div>

          <CRow>
            <CCol md={6}>
              <div className="mb-3">
                <CFormLabel>Max Tokens</CFormLabel>
                <CFormInput
                  type="number"
                  value={formData.max_tokens}
                  onChange={(e) => handleInputChange('max_tokens', e.target.value)}
                  placeholder="e.g., 4096"
                  min="1"
                  invalid={!!errors.max_tokens}
                />
                {errors.max_tokens && (
                  <div className="invalid-feedback d-block">{errors.max_tokens}</div>
                )}
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
                  placeholder="e.g., 0.7"
                  invalid={!!errors.temperature}
                />
                {errors.temperature && (
                  <div className="invalid-feedback d-block">{errors.temperature}</div>
                )}
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
            <small className="text-muted">Optional: Text-to-Speech service provider</small>
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
              placeholder="account1,account2,account3 (comma-separated)"
            />
            <small className="text-muted">Optional: Enter CRM account IDs separated by commas</small>
          </div>

          <div className="mb-3">
            <CFormLabel>Tags</CFormLabel>
            <CFormInput
              type="text"
              value={formData.tags}
              onChange={(e) => handleInputChange('tags', e.target.value)}
              placeholder="production, primary, backup (comma-separated)"
            />
            <small className="text-muted">Optional: Enter tags separated by commas</small>
          </div>

          <CRow>
            <CCol md={6}>
              <CFormCheck
                id="isDefault"
                label="Set as Default Credential"
                checked={formData.is_default}
                onChange={(e) => handleInputChange('is_default', e.target.checked)}
              />
            </CCol>
            <CCol md={6}>
              <CFormCheck
                id="isCrmFlowActive"
                label="Enable CRM Flow"
                checked={formData.is_crm_flow_active}
                onChange={(e) => handleInputChange('is_crm_flow_active', e.target.checked)}
              />
            </CCol>
          </CRow>
        </CModalBody>
        
        <CModalFooter>
          <CButton 
            variant="outline"
            onClick={handleClose} 
            disabled={loading}
            style={buttonStyles.secondary}
            onMouseEnter={secondaryHover.onMouseEnter}
            onMouseLeave={secondaryHover.onMouseLeave}
          >
            Cancel
          </CButton>
          <CButton 
            variant="outline"
            type="submit" 
            disabled={loading}
            style={buttonStyles.primary}
            onMouseEnter={primaryHover.onMouseEnter}
            onMouseLeave={primaryHover.onMouseLeave}
          >
            {loading ? (
              <>
                <CSpinner size="sm" className="me-2" />
                Creating...
              </>
            ) : (
              'Create Credential'
            )}
          </CButton>
        </CModalFooter>
      </CForm>
    </CModal>
  );
};

export default AddCredentialModal;
