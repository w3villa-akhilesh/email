import { useState } from 'react';

export const useAgentFormValidation = () => {
  const [formData, setFormData] = useState({
    name: '',
    display_name: '',
    description: '',
    parent_agent_id: '',
    agent_type: 'primary',
    default_model: '',
    system_prompt: '',
    capabilities: {},
    is_active: true
  });

  const [formErrors, setFormErrors] = useState({});
  const [submitLoading, setSubmitLoading] = useState(false);

  // Validation rules
  const validateForm = () => {
    const errors = {};

    // Name validation (unique identifier)
    if (!formData.name || formData.name.trim().length === 0) {
      errors.name = 'Agent name is required';
    } else if (formData.name.trim().length < 2) {
      errors.name = 'Agent name must be at least 2 characters';
    } else if (formData.name.trim().length > 100) {
      errors.name = 'Agent name must not exceed 100 characters';
    } else if (!/^[a-z0-9_-]+$/.test(formData.name.trim())) {
      errors.name = 'Agent name can only contain lowercase letters, numbers, hyphens, and underscores';
    }

    // Display Name validation
    if (!formData.display_name || formData.display_name.trim().length === 0) {
      errors.display_name = 'Display name is required';
    } else if (formData.display_name.trim().length < 2) {
      errors.display_name = 'Display name must be at least 2 characters';
    } else if (formData.display_name.trim().length > 255) {
      errors.display_name = 'Display name must not exceed 255 characters';
    }

    // Description validation (optional)
    if (formData.description && formData.description.trim().length > 1000) {
      errors.description = 'Description must not exceed 1000 characters';
    }

    // Agent Type validation
    const validTypes = ['primary', 'sub_agent', 'tool'];
    if (!validTypes.includes(formData.agent_type)) {
      errors.agent_type = 'Invalid agent type';
    }

    // Parent Agent ID validation - Required for sub_agent and tool types
    if (formData.agent_type === 'sub_agent' || formData.agent_type === 'tool') {
      if (!formData.parent_agent_id || formData.parent_agent_id === '') {
        errors.parent_agent_id = 'Parent agent is required for sub-agents and tools';
      } else {
        const parentId = parseInt(formData.parent_agent_id, 10);
        if (isNaN(parentId) || parentId <= 0) {
          errors.parent_agent_id = 'Parent agent ID must be a valid positive number';
        }
      }
    } else if (formData.parent_agent_id && formData.parent_agent_id !== '') {
      // Optional validation for primary agents
      const parentId = parseInt(formData.parent_agent_id, 10);
      if (isNaN(parentId) || parentId <= 0) {
        errors.parent_agent_id = 'Parent agent ID must be a valid positive number';
      }
    }

    // Default Model validation (optional)
    if (formData.default_model && formData.default_model.trim().length > 100) {
      errors.default_model = 'Default model must not exceed 100 characters';
    }

    // System Prompt validation (optional)
    if (formData.system_prompt && formData.system_prompt.trim().length > 5000) {
      errors.system_prompt = 'System prompt must not exceed 5000 characters';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Update form field
  const updateFormField = (field, value) => {
    setFormData(prev => {
      const newData = {
        ...prev,
        [field]: value
      };

      // Clear parent_agent_id when changing to primary agent type
      if (field === 'agent_type' && value === 'primary') {
        newData.parent_agent_id = '';
      }

      return newData;
    });

    // Clear error for this field when user starts typing
    if (formErrors[field]) {
      setFormErrors(prev => ({
        ...prev,
        [field]: ''
      }));
    }
    
    // Also clear parent_agent_id error when switching to primary
    if (field === 'agent_type' && value === 'primary' && formErrors.parent_agent_id) {
      setFormErrors(prev => ({
        ...prev,
        parent_agent_id: ''
      }));
    }
  };

  // Reset form
  const resetForm = () => {
    setFormData({
      name: '',
      display_name: '',
      description: '',
      parent_agent_id: '',
      agent_type: 'primary',
      default_model: '',
      system_prompt: '',
      capabilities: {},
      is_active: true
    });
    setFormErrors({});
  };

  // Set form data from existing agent
  const setFormDataFromAgent = (agent) => {
    setFormData({
      name: agent.name || '',
      display_name: agent.display_name || '',
      description: agent.description || '',
      parent_agent_id: agent.parent_agent_id || '',
      agent_type: agent.agent_type || 'primary',
      default_model: agent.default_model || '',
      system_prompt: agent.system_prompt || '',
      capabilities: agent.capabilities || {},
      is_active: agent.is_active !== undefined ? agent.is_active : true
    });
    setFormErrors({});
  };

  // Get clean form data for submission
  const getCleanFormData = () => {
    const cleanData = {
      name: formData.name.trim(),
      display_name: formData.display_name.trim(),
      agent_type: formData.agent_type,
      is_active: formData.is_active
    };

    // Only include optional fields if they have values
    if (formData.description && formData.description.trim()) {
      cleanData.description = formData.description.trim();
    }

    if (formData.parent_agent_id && formData.parent_agent_id !== '') {
      cleanData.parent_agent_id = parseInt(formData.parent_agent_id, 10);
    }

    if (formData.default_model && formData.default_model.trim()) {
      cleanData.default_model = formData.default_model.trim();
    }

    if (formData.system_prompt && formData.system_prompt.trim()) {
      cleanData.system_prompt = formData.system_prompt.trim();
    }

    if (formData.capabilities && Object.keys(formData.capabilities).length > 0) {
      cleanData.capabilities = formData.capabilities;
    }

    return cleanData;
  };

  return {
    formData,
    formErrors,
    submitLoading,
    setSubmitLoading,
    validateForm,
    updateFormField,
    resetForm,
    setFormDataFromAgent,
    getCleanFormData
  };
};

