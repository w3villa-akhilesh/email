import { useState } from 'react';
import { agentMappingsAPI } from '../Api/Auth';

export const useAgentMappings = (token) => {
  const [hierarchyData, setHierarchyData] = useState(null);
  const [mappingsData, setMappingsData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [pagination, setPagination] = useState({
    current_page: 1,
    page_size: 10,
    total_items: 0,
    total_pages: 1,
    has_next: false,
    has_prev: false
  });

  // Fetch company agent hierarchy
  const fetchCompanyHierarchy = async (companyId, page = 1, pageSize = 10) => {
    setLoading(true);
    setError(null);
    try {
      const response = await agentMappingsAPI.getCompanyHierarchy(token, companyId, page, pageSize);
      
      if (response.data) {
        setHierarchyData(response.data);
        if (response.pagination) {
          setPagination(response.pagination);
        }
        return response.data;
      } else {
        setHierarchyData(null);
        return null;
      }
    } catch (err) {
      console.error('Error fetching company hierarchy:', err);
      setError(err.message || 'Failed to load agent hierarchy');
      setHierarchyData(null);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Fetch agent mappings (filtered)
  const fetchMappings = async (companyId = null, agentId = null, isActive = null) => {
    setLoading(true);
    setError(null);
    try {
      const response = await agentMappingsAPI.getList(token, companyId, agentId, isActive);
      
      if (response.data) {
        setMappingsData(response.data);
        return response.data;
      } else {
        setMappingsData([]);
        return [];
      }
    } catch (err) {
      console.error('Error fetching mappings:', err);
      setError(err.message || 'Failed to load agent mappings');
      setMappingsData([]);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Create agent mapping
  const createMapping = async (mappingData) => {
    try {
      const response = await agentMappingsAPI.create(token, mappingData);
      return response;
    } catch (err) {
      console.error('Error creating mapping:', err);
      throw err;
    }
  };

  // Update agent mapping
  const updateMapping = async (mappingId, mappingData) => {
    try {
      const response = await agentMappingsAPI.update(token, mappingId, mappingData);
      return response;
    } catch (err) {
      console.error('Error updating mapping:', err);
      throw err;
    }
  };

  // Delete agent mapping
  const deleteMapping = async (mappingId) => {
    try {
      const response = await agentMappingsAPI.delete(token, mappingId);
      return response;
    } catch (err) {
      console.error('Error deleting mapping:', err);
      throw err;
    }
  };

  // Toggle mapping status
  const toggleMappingStatus = async (mappingId) => {
    try {
      const response = await agentMappingsAPI.toggleStatus(token, mappingId);
      return response;
    } catch (err) {
      console.error('Error toggling mapping status:', err);
      throw err;
    }
  };

  // Get mapping by ID
  const getMappingById = async (mappingId) => {
    try {
      const response = await agentMappingsAPI.getById(token, mappingId);
      return response.data;
    } catch (err) {
      console.error('Error fetching mapping:', err);
      throw err;
    }
  };

  // Bulk create mappings
  const bulkCreateMappings = async (mappingsArray) => {
    try {
      const response = await agentMappingsAPI.bulkCreate(token, mappingsArray);
      return response;
    } catch (err) {
      console.error('Error bulk creating mappings:', err);
      throw err;
    }
  };

  return {
    hierarchyData,
    mappingsData,
    loading,
    error,
    pagination,
    fetchCompanyHierarchy,
    fetchMappings,
    createMapping,
    updateMapping,
    deleteMapping,
    toggleMappingStatus,
    getMappingById,
    bulkCreateMappings,
  };
};

