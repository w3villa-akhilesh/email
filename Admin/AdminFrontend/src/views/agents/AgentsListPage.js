import React, { useState, useEffect, useRef } from 'react';
import {
  CSpinner,
  CContainer,
  CCard,
  CCardBody,
  CCardHeader,
  CButton
} from '@coreui/react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAgents } from '../../hooks/useAgents';
import { useAgentFormValidation } from '../../hooks/useAgentFormValidation';
import { useButtonHover } from '../../hooks/useButtonHover';
import AgentsTable from '../../components/agents/AgentsTable';
import AgentsModals from '../../components/agents/AgentsModals';
import AgentsFilters from '../../components/agents/AgentsFilters';
import PaginationComponent from '../base/paginations/PaginationComponent';
import Toast from '../../components/Toast';
import { buttonStyles, hoverColors } from '../../utils/commonStyles';
import { showAlert as showAlertHelper, extractErrorMessage } from '../../utils/commonHelpers';

const AgentsListPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const token = localStorage.getItem('access_token');

  // Get initial page from URL before initializing hooks
  const initialPage = (() => {
    const queryParams = new URLSearchParams(location.search);
    return parseInt(queryParams.get('page')) || 1;
  })();

  // Initialize hooks with initial page from URL
  const {
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
    fetchAllAgents
  } = useAgents(token, initialPage);

  const {
    formData,
    formErrors,
    submitLoading,
    setSubmitLoading,
    validateForm,
    resetForm,
    setFormDataFromAgent,
    updateFormField,
    getCleanFormData
  } = useAgentFormValidation();

  // Filters state - initialize from URL on mount
  const [filters, setFilters] = useState(() => {
    const queryParams = new URLSearchParams(location.search);
    return {
      name: queryParams.get('name') || '',
      display_name: queryParams.get('display_name') || '',
      agent_type: queryParams.get('agent_type') || '',
      status: queryParams.get('status') || ''
    };
  });

  // Track if we're syncing from URL to prevent loops
  const isSyncingFromUrl = useRef(false);
  
  // Sync state with URL when browser back/forward is used
  useEffect(() => {
    const queryParams = new URLSearchParams(location.search);
    const pageFromUrl = parseInt(queryParams.get('page')) || 1;
    const nameFromUrl = queryParams.get('name') || '';
    const displayNameFromUrl = queryParams.get('display_name') || '';
    const agentTypeFromUrl = queryParams.get('agent_type') || '';
    const statusFromUrl = queryParams.get('status') || '';
    
    const needsPageUpdate = pageFromUrl !== currentPage;
    const needsFiltersUpdate = nameFromUrl !== filters.name || 
                               displayNameFromUrl !== filters.display_name ||
                               agentTypeFromUrl !== filters.agent_type ||
                               statusFromUrl !== filters.status;
    
    if (needsPageUpdate || needsFiltersUpdate) {
      isSyncingFromUrl.current = true;
      
      if (needsPageUpdate) {
        setCurrentPage(pageFromUrl);
      }
      
      if (needsFiltersUpdate) {
        setFilters({
          name: nameFromUrl,
          display_name: displayNameFromUrl,
          agent_type: agentTypeFromUrl,
          status: statusFromUrl
        });
      }
      
      // Reset sync flag after state updates
      setTimeout(() => {
        isSyncingFromUrl.current = false;
      }, 0);
    }
  }, [location.search]);

  // Modal states
  const [modals, setModals] = useState({
    showCreateModal: false,
    showEditModal: false,
    showDeleteModal: false
  });

  const [selectedAgent, setSelectedAgent] = useState(null);
  const [alertMessage, setAlertMessage] = useState('');
  const [alertType, setAlertType] = useState('success');
  const [allAgents, setAllAgents] = useState([]); // For parent agent dropdown

  // Alert helper
  const showAlert = (message, type = 'success') => {
    showAlertHelper(setAlertMessage, setAlertType, message, type);
  };

  // Use shared button styles and hover effects
  const primaryHover = useButtonHover(hoverColors.primary);

  // Update URL when filters or page change (only if different from current URL)
  useEffect(() => {
    // Skip if we're currently syncing from URL
    if (isSyncingFromUrl.current) {
      return;
    }
    
    const params = new URLSearchParams();
    if (filters.name) params.append('name', filters.name);
    if (filters.display_name) params.append('display_name', filters.display_name);
    if (filters.agent_type) params.append('agent_type', filters.agent_type);
    if (filters.status) params.append('status', filters.status);
    if (currentPage > 1) params.append('page', currentPage.toString());
    
    const newSearch = params.toString();
    const currentSearch = location.search.substring(1); // Remove leading '?'
    
    // Only navigate if the URL actually needs to change
    if (newSearch !== currentSearch) {
      navigate(`?${newSearch}`, { replace: true });
    }
  }, [filters.name, filters.display_name, filters.agent_type, filters.status, currentPage, navigate, location.search]);

  // Fetch data when filters or page change
  useEffect(() => {
    // Convert status filter to proper boolean or null
    let statusFilter = null;
    if (filters.status === 'true') {
      statusFilter = true;
    } else if (filters.status === 'false') {
      statusFilter = false;
    }

    fetchAgents(
      filters.name || null,
      filters.display_name || null,
      filters.agent_type || null,
      null, // parent_agent_id filter not implemented in UI yet
      statusFilter,
      currentPage
    ).catch((error) => {
      console.error('Error fetching agents data:', error);
      const errorMessage = extractErrorMessage(error, 'Error fetching agents data');
      showAlert(errorMessage, 'danger');
    });
  }, [filters.name, filters.display_name, filters.agent_type, filters.status, currentPage]);

  // Filter handlers
  const handleFilterChange = (filterType, value) => {
    setFilters(prev => ({ ...prev, [filterType]: value }));
  };

  const clearFilters = () => {
    setFilters({
      name: '',
      display_name: '',
      agent_type: '',
      status: ''
    });
    setCurrentPage(1);
    navigate(location.pathname, { replace: true });
  };

  // Handle page change
  const handlePageChange = (page) => {
    setCurrentPage(page);
  };

  // Reset to first page when filters change (but not on initial mount or URL sync)
  const [isInitialMount, setIsInitialMount] = useState(true);
  
  useEffect(() => {
    if (isInitialMount) {
      setIsInitialMount(false);
      return;
    }
    
    // Skip if we're currently syncing from URL
    if (isSyncingFromUrl.current) {
      return;
    }
    
    // Only reset page if we're not on page 1 and filters actually changed
    if (currentPage !== 1) {
      setCurrentPage(1);
    }
  }, [filters.name, filters.display_name, filters.agent_type, filters.status]);

  // Modal handlers
  const openModal = async (modalType, agent = null) => {
    // Fetch all agents for parent agent dropdown BEFORE opening create or edit modal
    if (modalType === 'create' || modalType === 'edit') {
      console.log('Fetching all agents for dropdown...');
      const agents = await fetchAllAgents();
      console.log('Fetched agents:', agents);
      setAllAgents(agents);
      console.log('Set allAgents state with', agents.length, 'agents');
    }
    
    if (agent) {
      setSelectedAgent(agent);
      setFormDataFromAgent(agent);
    } else {
      resetForm();
    }
    
    // Open modal AFTER fetching agents
    setModals(prev => ({ 
      ...prev, 
      [`show${modalType.charAt(0).toUpperCase() + modalType.slice(1)}Modal`]: true 
    }));
  };

  const closeModal = (modalType) => {
    setModals(prev => ({ 
      ...prev, 
      [`show${modalType.charAt(0).toUpperCase() + modalType.slice(1)}Modal`]: false 
    }));
    resetForm();
    setSelectedAgent(null);
  };

  // CRUD operations
  const handleSubmit = async (action) => {
    if ((action === 'create' || action === 'edit') && !validateForm()) {
      return;
    }

    setSubmitLoading(true);
    try {
      const cleanData = getCleanFormData();
      
      switch (action) {
        case 'create':
          await createAgent(cleanData);
          showAlert('Agent created successfully');
          closeModal('create');
          break;
        case 'edit':
          await updateAgent(selectedAgent.id, cleanData);
          showAlert('Agent updated successfully');
          closeModal('edit');
          break;
        case 'delete':
          await deleteAgent(selectedAgent.id);
          showAlert('Agent deleted successfully');
          closeModal('delete');
          break;
      }
    } catch (error) {
      console.error(`Error ${action}ing agent:`, error);
      const errorMessage = extractErrorMessage(error, `Error ${action}ing agent`);
      showAlert(errorMessage, 'danger');
    } finally {
      setSubmitLoading(false);
    }
  };

  const handleToggleStatus = async (agent) => {
    try {
      const response = await toggleAgentStatus(agent.id);
      showAlert(
        `Agent ${response.data.is_active ? 'activated' : 'deactivated'} successfully`
      );
    } catch (error) {
      console.error('Error toggling agent status:', error);
      const errorMessage = extractErrorMessage(error, 'Error toggling agent status');
      showAlert(errorMessage, 'danger');
    }
  };

  // Check if any filter is active
  const isFilterActive = filters.name || filters.display_name || filters.agent_type || filters.status;

  return (
    <CContainer fluid>
      <Toast 
        message={alertMessage}
        type={alertType}
        onClose={() => setAlertMessage('')}
        duration={3000}
      />

      <CCard className="data-card">
        <CCardHeader className="data-card-header">
          <div className="d-flex justify-content-between align-items-center">
            <h4 className="card-title">Agents Management</h4>
            <AgentsFilters
              isFilterActive={isFilterActive}
              onClearFilters={clearFilters}
              onAddAgent={() => openModal('create')}
              totalCount={totalCount}
              loading={loading}
              hasData={agentsData.length > 0}
            />
          </div>
        </CCardHeader>

        <CCardBody className="data-card-body">
          {loading ? (
            <div className="loading-container">
              <CSpinner color="primary" size="lg" />
              <p>Loading agents data...</p>
            </div>
          ) : agentsData.length === 0 ? (
            <div className="empty-state text-center py-4">
              <i className="fas fa-robot fa-2x mb-2" />
              <p>No agents available.</p>
              {isFilterActive ? (
                <CButton 
                  variant="outline"
                  onClick={clearFilters}
                  style={buttonStyles.primary}
                  onMouseEnter={primaryHover.onMouseEnter}
                  onMouseLeave={primaryHover.onMouseLeave}
                >
                  Clear filters
                </CButton>
              ) : (
                <CButton 
                  variant="outline"
                  onClick={() => openModal('create')}
                  style={buttonStyles.primary}
                  onMouseEnter={primaryHover.onMouseEnter}
                  onMouseLeave={primaryHover.onMouseLeave}
                >
                  Add first agent
                </CButton>
              )}
            </div>
          ) : (
            <>
              <AgentsTable
                agentsData={agentsData}
                onAlert={showAlert}
                filters={filters}
                onFilterChange={handleFilterChange}
                onEdit={(agent) => openModal('edit', agent)}
                onDelete={(agent) => openModal('delete', agent)}
                onToggleStatus={handleToggleStatus}
              />
              {totalCount > 0 && (
                <PaginationComponent
                  currentPage={currentPage}
                  totalPages={totalPages}
                  onPageChange={handlePageChange}
                />
              )}
            </>
          )}
        </CCardBody>
      </CCard>

      <AgentsModals
        modals={modals}
        onCloseModals={closeModal}
        selectedAgent={selectedAgent}
        formData={formData}
        formErrors={formErrors}
        submitLoading={submitLoading}
        onFieldChange={updateFormField}
        onCreateSubmit={() => handleSubmit('create')}
        onEditSubmit={() => handleSubmit('edit')}
        onDeleteSubmit={() => handleSubmit('delete')}
        availableAgents={allAgents}
      />
    </CContainer>
  );
};

export default AgentsListPage;

