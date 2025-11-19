import React, { useState, useEffect } from 'react';
import {
  CSpinner,
  CAlert
} from '@coreui/react';
import { useAgentMappings } from '../../hooks/useAgentMappings';
import AgentMappingList from './AgentMappingList';
import AgentConfigModal from './AgentConfigModal';
import PaginationComponent from '../../views/base/paginations/PaginationComponent';
import { extractErrorMessage } from '../../utils/commonHelpers';
import './AgentMappingTab.scss';

const AgentMappingTab = ({ companyId, onAlert, credentialsRefreshTrigger }) => {
  const token = localStorage.getItem('access_token');
  const {
    hierarchyData,
    loading,
    error,
    pagination,
    fetchCompanyHierarchy,
    createMapping,
    updateMapping,
    deleteMapping,
    toggleMappingStatus
  } = useAgentMappings(token);

  const [selectedAgent, setSelectedAgent] = useState(null);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(10);

  useEffect(() => {
    if (companyId) {
      loadHierarchy();
    }
  }, [companyId]);

  // Refresh when credentials are updated
  useEffect(() => {
    if (companyId && credentialsRefreshTrigger > 0) {
      loadHierarchy(currentPage);
    }
  }, [credentialsRefreshTrigger]);

  const loadHierarchy = async (page = currentPage) => {
    try {
      await fetchCompanyHierarchy(companyId, page, pageSize);
    } catch (err) {
      console.error('Error loading hierarchy:', err);
      if (onAlert) {
        onAlert(extractErrorMessage(err, 'Failed to load agent hierarchy'), 'danger');
      }
    }
  };

  const refreshHierarchy = async () => {
    setRefreshing(true);
    try {
      await loadHierarchy(currentPage);
    } finally {
      setRefreshing(false);
    }
  };

  const handlePageChange = (page) => {
    setCurrentPage(page);
    loadHierarchy(page);
  };

  const handleConfigure = (agent) => {
    setSelectedAgent(agent);
    setShowConfigModal(true);
  };

  const handleCloseModal = () => {
    setShowConfigModal(false);
    setSelectedAgent(null);
  };

  const handleSave = async (mappingId, formData) => {
    try {
      await updateMapping(mappingId, formData);
      if (onAlert) {
        onAlert('Agent mapping updated successfully', 'success');
      }
      await refreshHierarchy();
    } catch (err) {
      console.error('Error updating mapping:', err);
      if (onAlert) {
        onAlert(extractErrorMessage(err, 'Failed to update agent mapping'), 'danger');
      }
      throw err;
    }
  };

  const handleCreate = async (formData) => {
    try {
      const mappingData = {
        company_id: companyId,
        ...formData
      };
      await createMapping(mappingData);
      if (onAlert) {
        onAlert('Agent mapping created successfully', 'success');
      }
      await refreshHierarchy();
    } catch (err) {
      console.error('Error creating mapping:', err);
      if (onAlert) {
        onAlert(extractErrorMessage(err, 'Failed to create agent mapping'), 'danger');
      }
      throw err;
    }
  };

  const handleDelete = async (mappingId) => {
    try {
      await deleteMapping(mappingId);
      if (onAlert) {
        onAlert('Agent mapping cleared successfully', 'success');
      }
      await refreshHierarchy();
    } catch (err) {
      console.error('Error clearing mapping:', err);
      if (onAlert) {
        onAlert(extractErrorMessage(err, 'Failed to clear agent mapping'), 'danger');
      }
      throw err;
    }
  };

  const handleToggleStatus = async (mappingId) => {
    try {
      const response = await toggleMappingStatus(mappingId);
      
      const isActive = response.data?.is_active;
      const affectedCount = response.affected_mapping_ids?.length || 1;
      
      let message = `Agent mapping ${isActive ? 'activated' : 'deactivated'} successfully`;
      if (affectedCount > 1) {
        message += ` (${affectedCount} mappings affected including children)`;
      }
      
      if (onAlert) {
        onAlert(message, 'success');
      }
      
      await refreshHierarchy();
    } catch (err) {
      console.error('Error toggling mapping status:', err);
      if (onAlert) {
        onAlert(extractErrorMessage(err, 'Failed to toggle agent status'), 'danger');
      }
      throw err;
    }
  };

  if (loading && !hierarchyData) {
    return (
      <div className="text-center py-5">
        <CSpinner color="primary" size="lg" />
        <p className="mt-3">Loading agent mappings...</p>
      </div>
    );
  }

  if (error && !hierarchyData) {
    return (
      <CAlert color="danger">
        <h5>Error Loading Agent Mappings</h5>
        <p>{error}</p>
      </CAlert>
    );
  }

  if (!hierarchyData) {
    return (
      <CAlert color="info">
        <p>No agent hierarchy data available</p>
      </CAlert>
    );
  }

  return (
    <div className="agent-mapping-tab">
      <div className="mt-2 mb-4">
        <div className="d-flex justify-content-between align-items-center mb-0">
          <h5 className="mb-2">Agent Mappings for {hierarchyData.company_name}</h5>
          {refreshing && <CSpinner size="sm" />}
        </div>
        {!loading && (
          <div>
            <span className="text-muted" style={{ fontSize: '1rem'}}>
              Total Agents : {hierarchyData.total_agents}
            </span>
          </div>
        )}
      </div>

      {/* Agent List with Configure Buttons */}
      {hierarchyData.agent_hierarchy && hierarchyData.agent_hierarchy.length > 0 ? (
        <>
          <AgentMappingList
            agents={hierarchyData.agent_hierarchy}
            onConfigure={handleConfigure}
            level={0}
          />
          
          {/* Pagination */}
          {(hierarchyData.total_root_agents > 0 || pagination.total_items > 0) && (
            <div className="mt-4">
              {/* Pagination Component */}
              <div className="d-flex justify-content-center">
                <PaginationComponent
                  currentPage={pagination.current_page || currentPage}
                  totalPages={pagination.total_pages || 1}
                  onPageChange={handlePageChange}
                />
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-5 text-muted">
          <p>No agents found</p>
        </div>
      )}

      {/* Configuration Modal */}
      <AgentConfigModal
        visible={showConfigModal}
        onClose={handleCloseModal}
        selectedAgent={selectedAgent}
        availableCredentials={hierarchyData.available_llm_credentials || []}
        onSave={handleSave}
        onDelete={handleDelete}
        onToggleStatus={handleToggleStatus}
        onCreate={handleCreate}
        loading={refreshing}
      />
    </div>
  );
};

export default AgentMappingTab;


