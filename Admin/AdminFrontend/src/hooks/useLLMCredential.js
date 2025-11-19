import { useState } from 'react';
import { llmCredentialAPI } from '../Api/Auth';

export const useLLMCredential = (token) => {
  const [credentialsData, setCredentialsData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [pageSize] = useState(10);

  // Fetch credentials data
  const fetchCredentials = async (companyIdFilter = null, providerFilter = null, statusFilter = null, page = currentPage) => {
    setLoading(true);
    try {
      const response = await llmCredentialAPI.getList(
        token,
        companyIdFilter,
        providerFilter,
        statusFilter,
        page,
        pageSize
      );

      if (response.data) {
        setCredentialsData(response.data);
        if (response.pagination) {
          setTotalCount(response.pagination.total_items || 0);
          setTotalPages(response.pagination.total_pages || 1);
        } else {
          // Fallback for old response format
          setTotalCount(response.total || response.data.length);
          setTotalPages(Math.ceil((response.total || response.data.length) / pageSize));
        }
      } else {
        setCredentialsData([]);
        setTotalCount(0);
        setTotalPages(1);
      }
    } catch (error) {
      console.error('Error fetching credentials:', error);
      setCredentialsData([]);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  // Create credential
  const createCredential = async (formData) => {
    try {
      const response = await llmCredentialAPI.create(token, formData);
      
      // Add new credential to local state instead of refetching all data
      if (response.data) {
        setCredentialsData(prevData => [response.data, ...prevData]);
        setTotalCount(prev => prev + 1);
      }
      
      return { success: true };
    } catch (error) {
      console.error('Error creating credential:', error);
      throw error;
    }
  };

  // Update credential
  const updateCredential = async (id, formData) => {
    try {
      const response = await llmCredentialAPI.update(token, id, formData);
      
      // Update local state instead of refetching all data
      setCredentialsData(prevData => 
        prevData.map(credential => 
          credential.id === id 
            ? { ...credential, ...formData, ...response.data }
            : credential
        )
      );
      
      return { success: true };
    } catch (error) {
      console.error('Error updating credential:', error);
      throw error;
    }
  };

  // Delete credential
  const deleteCredential = async (id) => {
    try {
      await llmCredentialAPI.delete(token, id);
      
      // Remove credential from local state instead of refetching all data
      setCredentialsData(prevData => prevData.filter(credential => credential.id !== id));
      setTotalCount(prev => prev - 1);
      
      return { success: true };
    } catch (error) {
      console.error('Error deleting credential:', error);
      throw error;
    }
  };

  // Toggle status
  const toggleCredentialStatus = async (id) => {
    try {
      const response = await llmCredentialAPI.toggleStatus(token, id);
      
      // Update local state instead of refetching all data
      setCredentialsData(prevData => 
        prevData.map(credential => 
          credential.id === id 
            ? { ...credential, is_active: response.data.is_active }
            : credential
        )
      );
      
      return response;
    } catch (error) {
      console.error('Error toggling status:', error);
      throw error;
    }
  };

  // Get credential by ID
  const getCredentialById = async (id) => {
    try {
      const response = await llmCredentialAPI.getById(token, id);
      return response.data;
    } catch (error) {
      console.error('Error fetching credential:', error);
      throw error;
    }
  };

  return {
    credentialsData,
    loading,
    currentPage,
    setCurrentPage,
    totalPages,
    totalCount,
    pageSize,
    fetchCredentials,
    createCredential,
    updateCredential,
    deleteCredential,
    toggleCredentialStatus,
    getCredentialById
  };
};
