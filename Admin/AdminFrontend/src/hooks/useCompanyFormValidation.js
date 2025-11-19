import { useState } from 'react';

export const useCompanyFormValidation = () => {
  const [formData, setFormData] = useState({
    id: '',
    name: '',
    origin: '',
    description: '',
    company_id: '',
    is_active: true
  });

  const [formErrors, setFormErrors] = useState({});
  const [submitLoading, setSubmitLoading] = useState(false);

  // Validation rules
  const validateForm = () => {
    const errors = {};

    // ID validation
    if (!formData.id || formData.id === '') {
      errors.id = 'Company ID is required';
    } else {
      const idNum = parseInt(formData.id, 10);
      if (isNaN(idNum)) {
        errors.id = 'Company ID must be a valid number';
      } else if (idNum <= 0) {
        errors.id = 'Company ID must be a positive number';
      } else if (idNum > 2147483647) {
        errors.id = 'Company ID is too large';
      }
    }

    // Name validation
    if (!formData.name || formData.name.trim().length === 0) {
      errors.name = 'Company name is required';
    } else if (formData.name.trim().length < 2) {
      errors.name = 'Company name must be at least 2 characters';
    } else if (formData.name.trim().length > 255) {
      errors.name = 'Company name must not exceed 255 characters';
    }

    // Origin validation
    if (!formData.origin || formData.origin.trim().length === 0) {
      errors.origin = 'Origin is required';
    } else if (formData.origin.trim().length < 3) {
      errors.origin = 'Origin must be at least 3 characters';
    } else if (formData.origin.trim().length > 255) {
      errors.origin = 'Origin must not exceed 255 characters';
    }

    // Description validation (optional)
    if (formData.description && formData.description.trim().length > 1000) {
      errors.description = 'Description must not exceed 1000 characters';
    }

    // Company ID validation (optional)
    if (formData.company_id && formData.company_id.trim().length > 100) {
      errors.company_id = 'Company ID must not exceed 100 characters';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Update form field
  const updateFormField = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));

    // Clear error for this field when user starts typing
    if (formErrors[field]) {
      setFormErrors(prev => ({
        ...prev,
        [field]: ''
      }));
    }
  };

  // Reset form
  const resetForm = () => {
    setFormData({
      id: '',
      name: '',
      origin: '',
      description: '',
      company_id: '',
      is_active: true
    });
    setFormErrors({});
  };

  // Set form data from existing company
  const setFormDataFromCompany = (company) => {
    setFormData({
      id: company.id || '',
      name: company.name || '',
      origin: company.origin || '',
      description: company.description || '',
      company_id: company.company_id || '',
      is_active: company.is_active !== undefined ? company.is_active : true
    });
    setFormErrors({});
  };

  // Get clean form data for submission
  const getCleanFormData = () => {
    const cleanData = {
      id: parseInt(formData.id, 10),
      name: formData.name.trim(),
      origin: formData.origin.trim(),
      is_active: formData.is_active
    };

    // Only include optional fields if they have values
    if (formData.description && formData.description.trim()) {
      cleanData.description = formData.description.trim();
    }

    if (formData.company_id && formData.company_id.trim()) {
      cleanData.company_id = formData.company_id.trim();
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
    setFormDataFromCompany,
    getCleanFormData
  };
};
