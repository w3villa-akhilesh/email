import React from 'react';
import {
  CForm,
  CFormInput,
  CFormLabel,
  CFormTextarea,
  CFormSwitch,
  CFormSelect,
  CRow,
  CCol,
  CFormFeedback
} from '@coreui/react';

const AgentsForm = ({
  formData,
  formErrors,
  onFieldChange,
  isEditMode = false,
  availableAgents = [],
  currentAgentId = null
}) => {
  // Filter out current agent from parent options to prevent circular reference
  const filteredAgents = availableAgents.filter(agent => 
    !currentAgentId || agent.id !== currentAgentId
  );

  console.log('AgentsForm - availableAgents:', availableAgents);
  console.log('AgentsForm - filteredAgents:', filteredAgents);
  console.log('AgentsForm - currentAgentId:', currentAgentId);

  return (
    <CForm>
      <CRow className="mb-3">
        <CCol md={6}>
          <CFormLabel htmlFor="name">
            Agent Name <span className="text-danger">*</span>
          </CFormLabel>
          <CFormInput
            type="text"
            id="name"
            placeholder="e.g., booking_agent"
            value={formData.name}
            onChange={(e) => onFieldChange('name', e.target.value)}
            invalid={!!formErrors.name}
            disabled={isEditMode}
          />
          {formErrors.name && (
            <CFormFeedback invalid>{formErrors.name}</CFormFeedback>
          )}
          <small className="form-text text-muted">
            {isEditMode ? 'Agent name cannot be changed' : 'Unique identifier (lowercase, numbers, hyphens, underscores only)'}
          </small>
        </CCol>
        
        <CCol md={6}>
          <CFormLabel htmlFor="display_name">
            Display Name <span className="text-danger">*</span>
          </CFormLabel>
          <CFormInput
            type="text"
            id="display_name"
            placeholder="e.g., Booking Agent"
            value={formData.display_name}
            onChange={(e) => onFieldChange('display_name', e.target.value)}
            invalid={!!formErrors.display_name}
            maxLength={255}
          />
          {formErrors.display_name && (
            <CFormFeedback invalid>{formErrors.display_name}</CFormFeedback>
          )}
          <small className="form-text text-muted">
            Human-readable name for the agent
          </small>
        </CCol>
      </CRow>

      <CRow className="mb-3">
        <CCol md={6}>
          <CFormLabel htmlFor="agent_type">
            Agent Type <span className="text-danger">*</span>
          </CFormLabel>
          <CFormSelect
            id="agent_type"
            value={formData.agent_type}
            onChange={(e) => onFieldChange('agent_type', e.target.value)}
            invalid={!!formErrors.agent_type}
          >
            <option value="primary">Primary</option>
            <option value="sub_agent">Sub Agent</option>
            <option value="tool">Tool</option>
          </CFormSelect>
          {formErrors.agent_type && (
            <CFormFeedback invalid>{formErrors.agent_type}</CFormFeedback>
          )}
          <small className="form-text text-muted">
            Type of agent (primary, sub_agent, or tool)
          </small>
        </CCol>
        
        {/* Show Parent Agent dropdown only for sub_agent or tool */}
        {(formData.agent_type === 'sub_agent' || formData.agent_type === 'tool') && (
          <CCol md={6}>
            <CFormLabel htmlFor="parent_agent_id">
              Parent Agent {(formData.agent_type === 'sub_agent' || formData.agent_type === 'tool') && <span className="text-danger">*</span>}
            </CFormLabel>
            <CFormSelect
              id="parent_agent_id"
              value={formData.parent_agent_id || ''}
              onChange={(e) => onFieldChange('parent_agent_id', e.target.value)}
              invalid={!!formErrors.parent_agent_id}
            >
              <option value="">-- Select Parent Agent --</option>
              {filteredAgents.map((agent) => (
                <option key={agent.id} value={agent.id}>
                  {agent.display_name} ({agent.name})
                </option>
              ))}
            </CFormSelect>
            {formErrors.parent_agent_id && (
              <CFormFeedback invalid>{formErrors.parent_agent_id}</CFormFeedback>
            )}
            <small className="form-text text-muted">
              {filteredAgents.length === 0 
                ? 'No available parent agents. Please create a primary agent first.' 
                : 'Select a parent agent for this sub-agent/tool'}
            </small>
          </CCol>
        )}
      </CRow>

      <CRow className="mb-3">
        <CCol md={6}>
          <CFormLabel htmlFor="default_model">
            Default Model
          </CFormLabel>
          <CFormInput
            type="text"
            id="default_model"
            placeholder="e.g., gpt-4o"
            value={formData.default_model}
            onChange={(e) => onFieldChange('default_model', e.target.value)}
            invalid={!!formErrors.default_model}
            maxLength={100}
          />
          {formErrors.default_model && (
            <CFormFeedback invalid>{formErrors.default_model}</CFormFeedback>
          )}
          <small className="form-text text-muted">
            Default LLM model for this agent (optional)
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
              {formData.is_active ? 'Agent is active' : 'Agent is inactive'}
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
            rows={3}
            placeholder="Enter agent description (optional)"
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

      <CRow className="mb-3">
        <CCol md={12}>
          <CFormLabel htmlFor="system_prompt">
            System Prompt
          </CFormLabel>
          <CFormTextarea
            id="system_prompt"
            rows={5}
            placeholder="Enter system prompt for the agent (optional)"
            value={formData.system_prompt}
            onChange={(e) => onFieldChange('system_prompt', e.target.value)}
            invalid={!!formErrors.system_prompt}
            maxLength={5000}
          />
          {formErrors.system_prompt && (
            <CFormFeedback invalid>{formErrors.system_prompt}</CFormFeedback>
          )}
          <small className="form-text text-muted">
            {formData.system_prompt.length}/5000 characters
          </small>
        </CCol>
      </CRow>

      {isEditMode && (
        <div className="alert alert-info">
          <small>
            <strong>Note:</strong> Changes to the agent name cannot be made after creation. 
            Other fields can be updated as needed.
          </small>
        </div>
      )}
    </CForm>
  );
};

export default AgentsForm;

