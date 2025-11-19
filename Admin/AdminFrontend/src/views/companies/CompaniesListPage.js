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
import { useCompanies } from '../../hooks/useCompanies';
import { useCompanyFormValidation } from '../../hooks/useCompanyFormValidation';
import { useButtonHover } from '../../hooks/useButtonHover';
import CompaniesTable from '../../components/companies/CompaniesTable';
import CompaniesModals from '../../components/companies/CompaniesModals';
import CompaniesFilters from '../../components/companies/CompaniesFilters';
import PaginationComponent from '../base/paginations/PaginationComponent';
import Toast from '../../components/Toast';
import { buttonStyles, hoverColors } from '../../utils/commonStyles';
import { showAlert as showAlertHelper, extractErrorMessage } from '../../utils/commonHelpers';

const CompaniesListPage = () => {
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
    companiesData,
    loading,
    currentPage,
    setCurrentPage,
    totalPages,
    totalCount,
    pageSize,
    fetchCompanies,
    createCompany,
    updateCompany,
    deleteCompany,
    toggleCompanyStatus
  } = useCompanies(token, initialPage);

  const {
    formData,
    formErrors,
    submitLoading,
    setSubmitLoading,
    validateForm,
    resetForm,
    setFormDataFromCompany,
    updateFormField,
    getCleanFormData
  } = useCompanyFormValidation();

  // Filters state - initialize from URL on mount
  const [filters, setFilters] = useState(() => {
    const queryParams = new URLSearchParams(location.search);
    return {
      name: queryParams.get('name') || '',
      origin: queryParams.get('origin') || '',
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
    const originFromUrl = queryParams.get('origin') || '';
    const statusFromUrl = queryParams.get('status') || '';
    
    const needsPageUpdate = pageFromUrl !== currentPage;
    const needsFiltersUpdate = nameFromUrl !== filters.name || 
                               originFromUrl !== filters.origin || 
                               statusFromUrl !== filters.status;
    
    if (needsPageUpdate || needsFiltersUpdate) {
      isSyncingFromUrl.current = true;
      
      if (needsPageUpdate) {
        setCurrentPage(pageFromUrl);
      }
      
      if (needsFiltersUpdate) {
        setFilters({
          name: nameFromUrl,
          origin: originFromUrl,
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

  const [selectedCompany, setSelectedCompany] = useState(null);
  const [alertMessage, setAlertMessage] = useState('');
  const [alertType, setAlertType] = useState('success');

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
    if (filters.origin) params.append('origin', filters.origin);
    if (filters.status) params.append('status', filters.status);
    if (currentPage > 1) params.append('page', currentPage.toString());
    
    const newSearch = params.toString();
    const currentSearch = location.search.substring(1); // Remove leading '?'
    
    // Only navigate if the URL actually needs to change
    if (newSearch !== currentSearch) {
      navigate(`?${newSearch}`, { replace: true });
    }
  }, [filters.name, filters.origin, filters.status, currentPage, navigate, location.search]);

  // Fetch data when filters or page change
  useEffect(() => {
    // Convert status filter to proper boolean or null
    let statusFilter = null;
    if (filters.status === 'true') {
      statusFilter = true;
    } else if (filters.status === 'false') {
      statusFilter = false;
    }

    fetchCompanies(
      filters.name || null,
      filters.origin || null,
      statusFilter,
      currentPage
    ).catch((error) => {
      console.error('Error fetching companies data:', error);
      const errorMessage = extractErrorMessage(error, 'Error fetching companies data');
      showAlert(errorMessage, 'danger');
    });
  }, [filters.name, filters.origin, filters.status, currentPage]);

  // Filter handlers
  const handleFilterChange = (filterType, value) => {
    setFilters(prev => ({ ...prev, [filterType]: value }));
  };

  const clearFilters = () => {
    setFilters({
      name: '',
      origin: '',
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
  }, [filters.name, filters.origin, filters.status]);

  // Modal handlers
  const openModal = (modalType, company = null) => {
    if (company) {
      setSelectedCompany(company);
      setFormDataFromCompany(company);
    } else {
      resetForm();
    }
    
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
    setSelectedCompany(null);
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
          await createCompany(cleanData);
          showAlert('Company created successfully');
          closeModal('create');
          break;
        case 'edit':
          await updateCompany(selectedCompany.id, cleanData);
          showAlert('Company updated successfully');
          closeModal('edit');
          break;
        case 'delete':
          await deleteCompany(selectedCompany.id);
          showAlert('Company deleted successfully');
          closeModal('delete');
          break;
      }
    } catch (error) {
      console.error(`Error ${action}ing company:`, error);
      const errorMessage = extractErrorMessage(error, `Error ${action}ing company`);
      showAlert(errorMessage, 'danger');
    } finally {
      setSubmitLoading(false);
    }
  };

  const handleToggleStatus = async (company) => {
    try {
      const response = await toggleCompanyStatus(company.id);
      showAlert(
        `Company ${response.data.is_active ? 'activated' : 'deactivated'} successfully`
      );
    } catch (error) {
      console.error('Error toggling company status:', error);
      const errorMessage = extractErrorMessage(error, 'Error toggling company status');
      showAlert(errorMessage, 'danger');
    }
  };

  const handleRowClick = (company) => {
    navigate(`/companies/${company.id}`);
  };

  // Check if any filter is active
  const isFilterActive = filters.name || filters.origin || filters.status;

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
            <h4 className="card-title">Companies Management</h4>
            <CompaniesFilters
              isFilterActive={isFilterActive}
              onClearFilters={clearFilters}
              onAddCompany={() => openModal('create')}
              totalCount={totalCount}
              loading={loading}
              hasData={companiesData.length > 0}
            />
          </div>
        </CCardHeader>

        <CCardBody className="data-card-body">
          {loading ? (
            <div className="loading-container">
              <CSpinner color="primary" size="lg" />
              <p>Loading companies data...</p>
            </div>
          ) : companiesData.length === 0 ? (
            <div className="empty-state text-center py-4">
              <i className="fas fa-building fa-2x mb-2" />
              <p>No companies available.</p>
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
                  Add first company
                </CButton>
              )}
            </div>
          ) : (
            <>
              <CompaniesTable
                companiesData={companiesData}
                onAlert={showAlert}
                filters={filters}
                onFilterChange={handleFilterChange}
                onRowClick={handleRowClick}
                onEdit={(company) => openModal('edit', company)}
                onDelete={(company) => openModal('delete', company)}
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

      <CompaniesModals
        modals={modals}
        onCloseModals={closeModal}
        selectedCompany={selectedCompany}
        formData={formData}
        formErrors={formErrors}
        submitLoading={submitLoading}
        onFieldChange={updateFormField}
        onCreateSubmit={() => handleSubmit('create')}
        onEditSubmit={() => handleSubmit('edit')}
        onDeleteSubmit={() => handleSubmit('delete')}
      />
    </CContainer>
  );
};

export default CompaniesListPage;
