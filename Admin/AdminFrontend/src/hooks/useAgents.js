import { useState, useEffect } from 'react';
import { agentsAPI } from '../Api/Auth';

export const useAgents = (token, initialPage = 1) => {
  const [agentsData, setAgentsData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(initialPage);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [pageSize] = useState(10);

  // Fetch agents data
  const fetchAgents = async (
    nameFilter = null,
    displayNameFilter = null,
    agentTypeFilter = null, 
    parentAgentIdFilter = null,
    statusFilter = null, 
    page = currentPage
  ) => {
    setLoading(true);
    try {
      const response = await agentsAPI.getList(
        token,
        nameFilter,
        displayNameFilter,
        agentTypeFilter,
        parentAgentIdFilter,
        statusFilter,
        page,
        pageSize
      );

      if (response.data) {
        setAgentsData(response.data);
        if (response.pagination) {
          setTotalCount(response.pagination.total_items || 0);
          setTotalPages(response.pagination.total_pages || 1);
        } else {
          // Fallback for old response format
          setTotalCount(response.total || response.data.length);
          setTotalPages(Math.ceil((response.total || response.data.length) / pageSize));
        }
      } else {
        setAgentsData([]);
        setTotalCount(0);
        setTotalPages(1);
      }
    } catch (error) {
      console.error('Error fetching agents:', error);
      setAgentsData([]);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  // Create agent
  const createAgent = async (formData) => {
    try {
      const response = await agentsAPI.create(token, formData);
      
      // Add new agent to local state instead of refetching all data
      if (response.data) {
        setAgentsData(prevData => [response.data, ...prevData]);
        setTotalCount(prev => prev + 1);
      }
      
      return { success: true };
    } catch (error) {
      console.error('Error creating agent:', error);
      throw error;
    }
  };

  // Update agent
  const updateAgent = async (id, formData) => {
    try {
      const response = await agentsAPI.update(token, id, formData);
      
      // Update local state instead of refetching all data
      setAgentsData(prevData => 
        prevData.map(agent => 
          agent.id === id 
            ? { ...agent, ...formData, ...response.data }
            : agent
        )
      );
      
      return { success: true };
    } catch (error) {
      console.error('Error updating agent:', error);
      throw error;
    }
  };

  // Delete agent
  const deleteAgent = async (id) => {
    try {
      await agentsAPI.delete(token, id);
      
      // Remove agent from local state instead of refetching all data
      setAgentsData(prevData => prevData.filter(agent => agent.id !== id));
      setTotalCount(prev => prev - 1);
      
      return { success: true };
    } catch (error) {
      console.error('Error deleting agent:', error);
      throw error;
    }
  };

  // Toggle status
  const toggleAgentStatus = async (id) => {
    try {
      const response = await agentsAPI.toggleStatus(token, id);
      
      // Update local state instead of refetching all data
      setAgentsData(prevData => 
        prevData.map(agent => 
          agent.id === id 
            ? { ...agent, is_active: response.data.is_active }
            : agent
        )
      );
      
      return response;
    } catch (error) {
      console.error('Error toggling status:', error);
      throw error;
    }
  };

  // Get agent by ID
  const getAgentById = async (id) => {
    try {
      const response = await agentsAPI.getById(token, id);
      return response.data;
    } catch (error) {
      console.error('Error fetching agent:', error);
      throw error;
    }
  };

  // Fetch all agents (for dropdown, no pagination)
  const fetchAllAgents = async () => {
    try {
      const response = await agentsAPI.getList(
        token,
        null, // name
        null, // display_name
        null, // agent_type
        null, // parent_agent_id
        null, // is_active
        1,    // page
        100   // max page_size allowed by backend
      );

      console.log('fetchAllAgents response:', response);
      
      if (response && response.data) {
        console.log('All agents fetched:', response.data.length, 'agents');
        return response.data;
      }
      
      console.log('No agents data in response');
      return [];
    } catch (error) {
      console.error('Error fetching all agents:', error);
      return [];
    }
  };

  return {
    agentsData,
    loading,
    currentPage,
    setCurrentPage,
    totalPages,
    totalCount,
    pageSize,
    fetchAgents,
    createAgent,
    updateAgent,
    deleteAgent,
    toggleAgentStatus,
    getAgentById,
    fetchAllAgents
  };
};

