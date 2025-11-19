import React, { useState, useEffect } from 'react';
import {
  CContainer,
  CCard,
  CCardBody,
  CCardHeader,
  CButton,
  CSpinner,
  CAlert,
  CNav,
  CNavItem,
  CNavLink,
  CTabContent,
  CTabPane,
  CTable,
  CTableHead,
  CTableBody,
  CTableRow,
  CTableHeaderCell,
  CTableDataCell,
  CBadge
} from '@coreui/react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { companiesAPI, llmCredentialAPI } from '../../Api/Auth';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faArrowLeft,
  faPlus,
  faBuilding,
  faCopy,
  faCheck
} from '@fortawesome/free-solid-svg-icons';
import { useButtonHover } from '../../hooks/useButtonHover';
import AddCredentialModal from '../../components/llm-credentials/AddCredentialModal';
import LLMCredentialEditModal from '../../components/llm-credentials/LLMCredentialEditModal';
import DeleteCredentialModal from '../../components/llm-credentials/DeleteCredentialModal';
import LLMCredentialActionButtons from '../../components/llm-credentials/LLMCredentialActionButtons';
import PaginationComponent from '../base/paginations/PaginationComponent.jsx';
import Toast from '../../components/Toast';
import AgentMappingTab from '../../components/agent-mappings/AgentMappingTab';
import { buttonStyles, hoverColors } from '../../utils/commonStyles';
import { formatDate, showAlert as showAlertHelper, extractErrorMessage } from '../../utils/commonHelpers';

const CompanyDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const token = localStorage.getItem('access_token');
  
  
  // State
  const [company, setCompany] = useState(null);
  const [credentials, setCredentials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [credentialsLoading, setCredentialsLoading] = useState(false);
  const [credentialsFetched, setCredentialsFetched] = useState(false);
  
  // Pagination state for credentials
  const [credentialsCurrentPage, setCredentialsCurrentPage] = useState(1);
  const [credentialsTotalPages, setCredentialsTotalPages] = useState(1);
  const [credentialsTotalCount, setCredentialsTotalCount] = useState(0);
  const [credentialsPageSize] = useState(10);

  // Use shared button styles and hover effects
  const primaryHover = useButtonHover(hoverColors.primary);
  const [error, setError] = useState('');
  
  // Initialize activeTab from URL parameters
  const queryParams = new URLSearchParams(location.search);
  const [activeTab, setActiveTab] = useState(queryParams.get('tab') || 'credentials');
  const [showAddCredentialModal, setShowAddCredentialModal] = useState(false);
  const [submitLoading, setSubmitLoading] = useState(false);
  
  
  // Modal states for credentials
  const [credentialModals, setCredentialModals] = useState({
    showEditModal: false,
    showDeleteModal: false
  });
  const [selectedCredential, setSelectedCredential] = useState(null);
  const [credentialSubmitLoading, setCredentialSubmitLoading] = useState(false);
  
  const [alertMessage, setAlertMessage] = useState('');
  const [alertType, setAlertType] = useState('success');
  const [copiedCredentialId, setCopiedCredentialId] = useState(null);
  
  // Trigger to refresh agent mappings when credentials change
  const [credentialsRefreshTrigger, setCredentialsRefreshTrigger] = useState(0);

  // Show alert (deprecated - use showToastAlert instead)
  const showAlert = (message, type = 'success') => {
    showToastAlert(message, type);
  };

  // Alert helper for new toast system
  const showToastAlert = (message, type = 'success') => {
    showAlertHelper(setAlertMessage, setAlertType, message, type);
  };

  // Handle tab change with URL update
  const handleTabChange = (tabName) => {
    setActiveTab(tabName);
    const params = new URLSearchParams(location.search);
    if (tabName === 'credentials') {
      params.delete('tab');
    } else {
      params.set('tab', tabName);
    }
    const newUrl = params.toString() ? `?${params.toString()}` : '';
    navigate(`/companies/${id}${newUrl}`, { replace: true });
  };


  // Fetch company details
  const fetchCompany = async () => {
    if (!id) {
      setError('No company ID provided');
      setLoading(false);
      return;
    }
    
    if (!token) {
      setError('Authentication required. Please login again.');
      setLoading(false);
      return;
    }
    
    try {
      setLoading(true);
      setError('');
      
      const response = await companiesAPI.getById(token, id);
      
      if (response && response.data) {
        setCompany(response.data);
      } else {
        setError('Company not found');
      }
    } catch (err) {
      console.error('Error fetching company:', err);
      
      if (err.response?.status === 401) {
        setError('Authentication failed. Please login again.');
      } else if (err.response?.status === 404) {
        setError('Company not found.');
      } else if (err.response?.status === 405) {
        setError('API endpoint not available. Please contact support.');
      } else {
        setError(`Failed to load company details: ${err.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  // Fetch credentials
  const fetchCredentials = async (page = credentialsCurrentPage) => {
    if (!company?.id || !token) return;
    
    try {
      setCredentialsLoading(true);
      const response = await llmCredentialAPI.getList(token, company.id, null, null, page, credentialsPageSize);
      if (response && response.data) {
        setCredentials(Array.isArray(response.data) ? response.data : []);
        
        // Handle pagination metadata
        if (response.pagination) {
          setCredentialsTotalCount(response.pagination.total_items || 0);
          setCredentialsTotalPages(response.pagination.total_pages || 1);
        } else {
          // Fallback for old response format
          const totalItems = response.total || response.data.length;
          const totalPages = Math.ceil(totalItems / credentialsPageSize);
          setCredentialsTotalCount(totalItems);
          setCredentialsTotalPages(totalPages);
        }
        setCredentialsFetched(true);
      } else {
        setCredentials([]);
        setCredentialsTotalCount(0);
        setCredentialsTotalPages(1);
      }
    } catch (error) {
      console.error('Error fetching credentials:', error);
      const errorMessage = extractErrorMessage(error, 'Error fetching credentials');
      showAlert(errorMessage, 'danger');
      setCredentials([]);
      setCredentialsTotalCount(0);
      setCredentialsTotalPages(1);
    } finally {
      setCredentialsLoading(false);
    }
  };


  // Create new credential
  const handleCreateCredential = async (credentialData) => {
    if (!token) {
      showAlert('Authentication required. Please login again.', 'danger');
      return;
    }

    try {
      setSubmitLoading(true);
      
      const response = await llmCredentialAPI.create(token, credentialData);
      
      if (response) {
        showAlert('LLM credential created successfully');
        // Add new credential to local state instead of refetching
        if (response.data) {
          setCredentials(prev => [response.data, ...prev]);
          setCredentialsTotalCount(prev => prev + 1);
        }
        // Trigger refresh of agent mappings
        setCredentialsRefreshTrigger(prev => prev + 1);
      }
    } catch (error) {
      console.error('Error creating credential:', error);
      
      let errorMessage = 'Failed to create credential';
      
      if (error.response?.status === 401) {
        errorMessage = 'Authentication failed. Please login again.';
      } else {
        errorMessage = extractErrorMessage(error, 'Failed to create credential');
      }
      
      showAlert(errorMessage, 'danger');
    } finally {
      setSubmitLoading(false);
    }
  };

  // Handle credentials page change
  const handleCredentialsPageChange = (page) => {
    setCredentialsCurrentPage(page);
    fetchCredentials(page);
  };

  // Credential modal handlers
  const openCredentialModal = (modalType, credential = null) => {
    setCredentialModals(prev => ({ ...prev, [`show${modalType}Modal`]: true }));
    if (credential) {
      setSelectedCredential(credential);
    }
  };

  const closeCredentialModal = (modalType) => {
    setCredentialModals(prev => ({ ...prev, [`show${modalType}Modal`]: false }));
    setSelectedCredential(null);
  };

  // Toggle credential status
  const handleToggleCredentialStatus = async (credential) => {
    try {
      const response = await llmCredentialAPI.toggleStatus(token, credential.id);
      showToastAlert(
        `Credential ${response.data.is_active ? 'activated' : 'deactivated'} successfully`
      );
      // Update local state
      setCredentials(prevCredentials =>
        prevCredentials.map(c =>
          c.id === credential.id ? { ...c, is_active: response.data.is_active } : c
        )
      );
      // Trigger refresh of agent mappings
      setCredentialsRefreshTrigger(prev => prev + 1);
    } catch (error) {
      const errorMessage = extractErrorMessage(error, 'Error toggling credential status');
      showToastAlert(errorMessage, 'danger');
    }
  };

  // Toggle CRM flow
  const handleToggleCrmFlow = async (credential) => {
    try {
      const response = await llmCredentialAPI.toggleCrmFlow(token, credential.id);
      showToastAlert(
        `CRM Flow ${response.data.is_crm_flow_active ? 'enabled' : 'disabled'} successfully`
      );
      // Update local state
      setCredentials(prevCredentials =>
        prevCredentials.map(c =>
          c.id === credential.id ? { ...c, is_crm_flow_active: response.data.is_crm_flow_active } : c
        )
      );
      // Trigger refresh of agent mappings
      setCredentialsRefreshTrigger(prev => prev + 1);
    } catch (error) {
      const errorMessage = extractErrorMessage(error, 'Error toggling CRM flow');
      showToastAlert(errorMessage, 'danger');
    }
  };

  // Update credential
  const handleUpdateCredential = async (credentialData) => {
    if (!selectedCredential) return;
    
    try {
      setCredentialSubmitLoading(true);
      const response = await llmCredentialAPI.update(token, selectedCredential.id, credentialData);
      showToastAlert('Credential updated successfully');
      closeCredentialModal('Edit');
      // Update local state instead of refetching
      setCredentials(prevCredentials =>
        prevCredentials.map(cred =>
          cred.id === selectedCredential.id
            ? { ...cred, ...credentialData, ...response.data }
            : cred
        )
      );
      // Trigger refresh of agent mappings
      setCredentialsRefreshTrigger(prev => prev + 1);
    } catch (error) {
      const errorMessage = extractErrorMessage(error, 'Error updating credential');
      showToastAlert(errorMessage, 'danger');
      throw error;
    } finally {
      setCredentialSubmitLoading(false);
    }
  };

  // Delete credential
  const handleDeleteCredential = async () => {
    if (!selectedCredential) return;
    
    try {
      setCredentialSubmitLoading(true);
      await llmCredentialAPI.delete(token, selectedCredential.id);
      showToastAlert('Credential deleted successfully');
      closeCredentialModal('Delete');
      // Remove credential from local state instead of refetching
      setCredentials(prevCredentials =>
        prevCredentials.filter(cred => cred.id !== selectedCredential.id)
      );
      setCredentialsTotalCount(prev => prev - 1);
      // Trigger refresh of agent mappings
      setCredentialsRefreshTrigger(prev => prev + 1);
    } catch (error) {
      const errorMessage = extractErrorMessage(error, 'Error deleting credential');
      showToastAlert(errorMessage, 'danger');
    } finally {
      setCredentialSubmitLoading(false);
    }
  };

  // Use shared formatDate function (no need to redefine)

  // Effects
  useEffect(() => {
    fetchCompany();
  }, [id]);

  // Sync activeTab with URL changes
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const tabFromUrl = params.get('tab') || 'credentials';
    if (tabFromUrl !== activeTab) {
      setActiveTab(tabFromUrl);
    }
  }, [location.search]);

  useEffect(() => {
    if (activeTab === 'credentials' && company && !credentialsFetched) {
      fetchCredentials();
    }
  }, [activeTab, company, credentialsFetched]);

  // Loading state
  if (loading) {
    return (
      <CContainer fluid>
        <div className="text-center py-5">
          <CSpinner color="primary" size="lg" />
          <p className="mt-3">Loading company details...</p>
        </div>
      </CContainer>
    );
  }

  // Error state
  if (error) {
    return (
      <CContainer fluid>
        <CAlert color="danger">
          <h4>Error</h4>
          <p>{error}</p>
          <CButton color="primary" onClick={() => navigate(-1)}>
            ← Back to Companies
          </CButton>
        </CAlert>
      </CContainer>
    );
  }

  // Not found state
  if (!company) {
    return (
      <CContainer fluid>
        <CAlert color="warning">
          <h4>Company Not Found</h4>
          <p>The requested company could not be found.</p>
          <CButton color="primary" onClick={() => navigate(-1)}>
            ← Back to Companies
          </CButton>
        </CAlert>
      </CContainer>
    );
  }

  return (
    <CContainer fluid>

      {/* Header and Tabs */}
      <CCard>
        <CCardBody className="pb-0">
          <div className="d-flex align-items-center gap-3 mb-4">
            <CButton
              onClick={() => navigate(-1)}
              style={{
                backgroundColor: '#f8f9fa',
                color: '#000000',
                border: 'none',
                padding: '8px 12px',
                borderRadius: '4px',
                fontSize: '1rem',
                cursor: 'pointer',
                transition: 'none',
                boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)'
              }}
              onMouseEnter={(e) => {
                e.target.style.backgroundColor = '#f8f9fa';
              }}
              onMouseLeave={(e) => {
                e.target.style.backgroundColor = '#f8f9fa';
              }}
            >
              <FontAwesomeIcon icon={faArrowLeft} />
            </CButton>
            <h2 className="mb-0" style={{ color: '#40518A' }}>
              <FontAwesomeIcon icon={faBuilding} className="me-2" />
              {company.name}
            </h2>
          </div>
        </CCardBody>
        <CCardHeader className="p-0" style={{ borderBottom: '1px solid #e9ecef' }}>
          <CNav variant="tabs" style={{ borderBottom: 'none' }}>
            <CNavItem>
              <CNavLink
                active={activeTab === 'credentials'}
                onClick={() => handleTabChange('credentials')}
                style={{
                  cursor: 'pointer',
                  padding: '12px 20px',
                  fontWeight: activeTab === 'credentials' ? '600' : '500',
                  color: activeTab === 'credentials' ? '#40518a' : '#6c757d',
                  backgroundColor: activeTab === 'credentials' ? '#f8f9fa' : 'transparent',
                  borderBottom: activeTab === 'credentials' ? '3px solid #40518a' : '3px solid transparent',
                  borderTop: 'none',
                  borderLeft: 'none',
                  borderRight: 'none',
                  transition: 'all 0.2s ease',
                  marginBottom: '-1px'
                }}
              >
                LLM Credentials
              </CNavLink>
            </CNavItem>
            <CNavItem>
              <CNavLink
                active={activeTab === 'agents'}
                onClick={() => handleTabChange('agents')}
                style={{
                  cursor: 'pointer',
                  padding: '12px 20px',
                  fontWeight: activeTab === 'agents' ? '600' : '500',
                  color: activeTab === 'agents' ? '#40518a' : '#6c757d',
                  backgroundColor: activeTab === 'agents' ? '#f8f9fa' : 'transparent',
                  borderBottom: activeTab === 'agents' ? '3px solid #40518a' : '3px solid transparent',
                  borderTop: 'none',
                  borderLeft: 'none',
                  borderRight: 'none',
                  transition: 'all 0.2s ease',
                  marginBottom: '-1px'
                }}
              >
                Agent Mappings
              </CNavLink>
            </CNavItem>
          </CNav>
        </CCardHeader>

        <CCardBody>
          <CTabContent>
            {/* LLM Credentials Tab */}
            <CTabPane visible={activeTab === 'credentials'}>
              <div className="mb-5">
                <div className="d-flex justify-content-between align-items-center mb-0">
                  <h5 className="mb-0">LLM Credentials for {company.name}</h5>
                  <CButton
                    variant="outline"
                    size="sm"
                    onClick={() => setShowAddCredentialModal(true)}
                    style={buttonStyles.primary}
                    onMouseEnter={primaryHover.onMouseEnter}
                    onMouseLeave={primaryHover.onMouseLeave}
                    >
                      <FontAwesomeIcon icon={faPlus} className="me-2" />
                      Add Credential
                    </CButton>
                </div>
                {!credentialsLoading && (
                  <div>
                    <span className="text-muted" style={{ fontSize: '1rem'}}>
                      Total LLM Credentials : {credentialsTotalCount}
                    </span>
                  </div>
                )}
              </div>

              {credentialsLoading ? (
                <div className="text-center py-4">
                  <CSpinner color="primary" />
                  <p className="mt-2">Loading credentials...</p>
                </div>
              ) : credentials.length === 0 ? (
                <div className="empty-state text-center py-4">
                  <p className="text-muted">No LLM credentials found for this company.</p>
                </div>
              ) : (
                <>
                  <div 
                    className="table-responsive" 
                    style={{ 
                      overflowX: 'auto',
                      scrollbarWidth: 'none',
                      msOverflowStyle: 'none'
                    }}
                  >
                    <style dangerouslySetInnerHTML={{
                      __html: `
                        .table-responsive::-webkit-scrollbar {
                          display: none;
                        }
                      `
                    }} />
                    <CTable hover className="clean-table">
                      <CTableHead className="table-header">
                        <CTableRow>
                          <CTableHeaderCell 
                            scope="col" 
                            className="table-header-cell"
                            style={{ width: '150px', minWidth: '150px' }}
                          >
                            Provider
                          </CTableHeaderCell>
                          <CTableHeaderCell 
                            scope="col" 
                            className="table-header-cell"
                            style={{ width: '200px', minWidth: '200px' }}
                          >
                            Base URL
                          </CTableHeaderCell>
                          <CTableHeaderCell 
                            scope="col" 
                            className="table-header-cell"
                            style={{ width: '250px', minWidth: '250px' }}
                          >
                            Available Models
                          </CTableHeaderCell>
                          <CTableHeaderCell 
                            scope="col" 
                            className="table-header-cell"
                            style={{ width: '200px', minWidth: '200px' }}
                          >
                            API Key
                          </CTableHeaderCell>
                          <CTableHeaderCell 
                            scope="col" 
                            className="table-header-cell"
                            style={{ width: '100px', minWidth: '100px' }}
                          >
                            Status
                          </CTableHeaderCell>
                          <CTableHeaderCell 
                            scope="col" 
                            className="table-header-cell"
                            style={{ width: '100px', minWidth: '100px' }}
                          >
                            CRM Flow
                          </CTableHeaderCell>
                          <CTableHeaderCell 
                            scope="col" 
                            className="table-header-cell"
                            style={{ width: '130px', minWidth: '130px' }}
                          >
                            Default Credential
                          </CTableHeaderCell>
                          <CTableHeaderCell 
                            scope="col" 
                            className="table-header-cell"
                            style={{ width: '120px', minWidth: '120px' }}
                          >
                            TTS Service
                          </CTableHeaderCell>
                          <CTableHeaderCell 
                            scope="col" 
                            className="table-header-cell"
                            style={{ width: '150px', minWidth: '150px' }}
                          >
                            Cartesia Key
                          </CTableHeaderCell>
                          <CTableHeaderCell 
                            scope="col" 
                            className="table-header-cell"
                            style={{ width: '150px', minWidth: '150px' }}
                          >
                            Deepgram Key
                          </CTableHeaderCell>
                          <CTableHeaderCell 
                            scope="col" 
                            className="table-header-cell"
                            style={{ width: '150px', minWidth: '150px' }}
                          >
                            OpenAI Key
                          </CTableHeaderCell>
                          <CTableHeaderCell 
                            scope="col" 
                            className="table-header-cell"
                            style={{ width: '150px', minWidth: '150px' }}
                          >
                            CRM Account IDs
                          </CTableHeaderCell>
                          <CTableHeaderCell 
                            scope="col" 
                            className="table-header-cell"
                            style={{ width: '120px', minWidth: '120px' }}
                          >
                            Created By
                          </CTableHeaderCell>
                          <CTableHeaderCell 
                            scope="col" 
                            className="table-header-cell"
                            style={{ width: '120px', minWidth: '120px' }}
                          >
                            Updated By
                          </CTableHeaderCell>
                          <CTableHeaderCell 
                            scope="col" 
                            className="table-header-cell"
                            style={{ width: '220px', minWidth: '220px', textAlign: 'center' }}
                          >
                            Actions
                          </CTableHeaderCell>
                        </CTableRow>
                      </CTableHead>
                      <CTableBody>
                        {credentials.map((credential) => (
                          <CTableRow 
                            key={credential.id}
                            className="table-row"
                          >
                            <CTableDataCell className="table-cell">
                              <div className="cell-content">
                                <span style={{ fontSize: '14px' }}>{credential.provider}</span>
                              </div>
                            </CTableDataCell>
                            <CTableDataCell className="table-cell">
                              <div className="cell-content">
                                <span className="text-muted" style={{ fontSize: '13px' }}>
                                  {credential.base_url}
                                </span>
                              </div>
                            </CTableDataCell>
                            <CTableDataCell className="table-cell">
                              <div className="cell-content">
                                {credential.available_models && credential.available_models.length > 0 ? (
                                  <div style={{ 
                                    display: 'flex', 
                                    flexWrap: 'wrap', 
                                    gap: '4px',
                                    maxWidth: '200px'
                                  }}>
                                    {credential.available_models.map((model, index) => (
                                      <CBadge 
                                        key={index} 
                                        className="mb-1" 
                                        style={{ 
                                          fontSize: '0.75rem',
                                          backgroundColor: '#40518A',
                                          color: 'white',
                                          whiteSpace: 'nowrap'
                                        }}
                                      >
                                        {model}
                                      </CBadge>
                                    ))}
                                  </div>
                                ) : (
                                  <span className="text-muted" style={{ fontSize: '13px' }}>None</span>
                                )}
                              </div>
                            </CTableDataCell>
                            <CTableDataCell className="table-cell">
                              <div className="cell-content">
                                <div className="d-flex align-items-center" style={{ whiteSpace: 'nowrap' }}>
                                  <code className="me-2" style={{ 
                                    fontSize: '0.85rem',
                                    whiteSpace: 'nowrap',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                    maxWidth: '140px'
                                  }}>
                                    {credential.api_key ? 
                                      `${credential.api_key.substring(0, 6)}••••${credential.api_key.substring(credential.api_key.length - 4)}` 
                                      : 'N/A'
                                    }
                                  </code>
                                  {credential.api_key && (
                                    <CButton
                                      variant="ghost"
                                      size="sm"
                                      onClick={async (e) => {
                                        e.stopPropagation();
                                        try {
                                          await navigator.clipboard.writeText(credential.api_key);
                                          setCopiedCredentialId(credential.id);
                                          showToastAlert('API Key copied!', 'success');
                                          setTimeout(() => setCopiedCredentialId(null), 2000);
                                        } catch (err) {
                                          console.error('Failed to copy: ', err);
                                          showToastAlert('Failed to copy to clipboard', 'danger');
                                        }
                                      }}
                                      title="Copy API Key"
                                      style={{
                                        borderRadius: '6px',
                                        padding: '4px 6px',
                                        border: '1px solid #dee2e6',
                                        color: copiedCredentialId === credential.id ? '#28a745' : '#6c757d',
                                        backgroundColor: 'transparent',
                                        minWidth: 'auto',
                                        height: 'auto',
                                        flexShrink: 0
                                      }}
                                    >
                                      <FontAwesomeIcon 
                                        icon={copiedCredentialId === credential.id ? faCheck : faCopy} 
                                        size="xs" 
                                      />
                                    </CButton>
                                  )}
                                </div>
                              </div>
                            </CTableDataCell>
                            <CTableDataCell className="table-cell">
                              <div className="cell-content">
                                <CBadge 
                                  color={credential.is_active ? 'success' : 'danger'}
                                  className="status-badge"
                                >
                                  {credential.is_active ? 'Active' : 'Inactive'}
                                </CBadge>
                              </div>
                            </CTableDataCell>
                            <CTableDataCell className="table-cell">
                              <div className="cell-content">
                                <CBadge 
                                  color={credential.is_crm_flow_active ? 'success' : 'secondary'}
                                  className="status-badge"
                                >
                                  {credential.is_crm_flow_active ? 'Enabled' : 'Disabled'}
                                </CBadge>
                              </div>
                            </CTableDataCell>
                            <CTableDataCell className="table-cell">
                              <div className="cell-content">
                                <span className="text-muted" style={{ fontSize: '13px' }}>
                                  {credential.is_default ? 'Yes' : 'No'}
                                </span>
                              </div>
                            </CTableDataCell>
                            <CTableDataCell className="table-cell">
                              <div className="cell-content">
                                <span className="text-muted" style={{ fontSize: '13px' }}>
                                  {credential.tts_service || 'None'}
                                </span>
                              </div>
                            </CTableDataCell>
                            <CTableDataCell className="table-cell">
                              <div className="cell-content">
                                {credential.cartesia_api_key ? (
                                  <div className="d-flex align-items-center" style={{ whiteSpace: 'nowrap' }}>
                                    <code className="me-2" style={{ 
                                      fontSize: '0.85rem',
                                      whiteSpace: 'nowrap',
                                      overflow: 'hidden',
                                      textOverflow: 'ellipsis',
                                      maxWidth: '100px'
                                    }}>
                                      {`${credential.cartesia_api_key.substring(0, 6)}••••`}
                                    </code>
                                    <CButton
                                      variant="ghost"
                                      size="sm"
                                      onClick={async (e) => {
                                        e.stopPropagation();
                                        try {
                                          await navigator.clipboard.writeText(credential.cartesia_api_key);
                                          setCopiedCredentialId(`cartesia_${credential.id}`);
                                          showToastAlert('Cartesia API Key copied!', 'success');
                                          setTimeout(() => setCopiedCredentialId(null), 2000);
                                        } catch (err) {
                                          console.error('Failed to copy: ', err);
                                          showToastAlert('Failed to copy to clipboard', 'danger');
                                        }
                                      }}
                                      title="Copy Cartesia API Key"
                                      style={{
                                        borderRadius: '6px',
                                        padding: '4px 6px',
                                        border: '1px solid #dee2e6',
                                        color: copiedCredentialId === `cartesia_${credential.id}` ? '#28a745' : '#6c757d',
                                        backgroundColor: 'transparent',
                                        minWidth: 'auto',
                                        height: 'auto',
                                        flexShrink: 0
                                      }}
                                    >
                                      <FontAwesomeIcon 
                                        icon={copiedCredentialId === `cartesia_${credential.id}` ? faCheck : faCopy} 
                                        size="xs" 
                                      />
                                    </CButton>
                                  </div>
                                ) : (
                                  <span className="text-muted" style={{ fontSize: '13px' }}>None</span>
                                )}
                              </div>
                            </CTableDataCell>
                            <CTableDataCell className="table-cell">
                              <div className="cell-content">
                                {credential.deepgram_api_key ? (
                                  <div className="d-flex align-items-center" style={{ whiteSpace: 'nowrap' }}>
                                    <code className="me-2" style={{ 
                                      fontSize: '0.85rem',
                                      whiteSpace: 'nowrap',
                                      overflow: 'hidden',
                                      textOverflow: 'ellipsis',
                                      maxWidth: '100px'
                                    }}>
                                      {`${credential.deepgram_api_key.substring(0, 6)}••••`}
                                    </code>
                                    <CButton
                                      variant="ghost"
                                      size="sm"
                                      onClick={async (e) => {
                                        e.stopPropagation();
                                        try {
                                          await navigator.clipboard.writeText(credential.deepgram_api_key);
                                          setCopiedCredentialId(`deepgram_${credential.id}`);
                                          showToastAlert('Deepgram API Key copied!', 'success');
                                          setTimeout(() => setCopiedCredentialId(null), 2000);
                                        } catch (err) {
                                          console.error('Failed to copy: ', err);
                                          showToastAlert('Failed to copy to clipboard', 'danger');
                                        }
                                      }}
                                      title="Copy Deepgram API Key"
                                      style={{
                                        borderRadius: '6px',
                                        padding: '4px 6px',
                                        border: '1px solid #dee2e6',
                                        color: copiedCredentialId === `deepgram_${credential.id}` ? '#28a745' : '#6c757d',
                                        backgroundColor: 'transparent',
                                        minWidth: 'auto',
                                        height: 'auto',
                                        flexShrink: 0
                                      }}
                                    >
                                      <FontAwesomeIcon 
                                        icon={copiedCredentialId === `deepgram_${credential.id}` ? faCheck : faCopy} 
                                        size="xs" 
                                      />
                                    </CButton>
                                  </div>
                                ) : (
                                  <span className="text-muted" style={{ fontSize: '13px' }}>None</span>
                                )}
                              </div>
                            </CTableDataCell>
                            <CTableDataCell className="table-cell">
                              <div className="cell-content">
                                {credential.openai_api_key ? (
                                  <div className="d-flex align-items-center" style={{ whiteSpace: 'nowrap' }}>
                                    <code className="me-2" style={{ 
                                      fontSize: '0.85rem',
                                      whiteSpace: 'nowrap',
                                      overflow: 'hidden',
                                      textOverflow: 'ellipsis',
                                      maxWidth: '100px'
                                    }}>
                                      {`${credential.openai_api_key.substring(0, 6)}••••`}
                                    </code>
                                    <CButton
                                      variant="ghost"
                                      size="sm"
                                      onClick={async (e) => {
                                        e.stopPropagation();
                                        try {
                                          await navigator.clipboard.writeText(credential.openai_api_key);
                                          setCopiedCredentialId(`openai_${credential.id}`);
                                          showToastAlert('OpenAI API Key copied!', 'success');
                                          setTimeout(() => setCopiedCredentialId(null), 2000);
                                        } catch (err) {
                                          console.error('Failed to copy: ', err);
                                          showToastAlert('Failed to copy to clipboard', 'danger');
                                        }
                                      }}
                                      title="Copy OpenAI API Key"
                                      style={{
                                        borderRadius: '6px',
                                        padding: '4px 6px',
                                        border: '1px solid #dee2e6',
                                        color: copiedCredentialId === `openai_${credential.id}` ? '#28a745' : '#6c757d',
                                        backgroundColor: 'transparent',
                                        minWidth: 'auto',
                                        height: 'auto',
                                        flexShrink: 0
                                      }}
                                    >
                                      <FontAwesomeIcon 
                                        icon={copiedCredentialId === `openai_${credential.id}` ? faCheck : faCopy} 
                                        size="xs" 
                                      />
                                    </CButton>
                                  </div>
                                ) : (
                                  <span className="text-muted" style={{ fontSize: '13px' }}>None</span>
                                )}
                              </div>
                            </CTableDataCell>
                            <CTableDataCell className="table-cell">
                              <div className="cell-content">
                                <span className="text-muted" style={{ fontSize: '13px' }}>
                                  {credential.crm_accounts_ids || 'None'}
                                </span>
                              </div>
                            </CTableDataCell>
                            <CTableDataCell className="table-cell">
                              <div className="cell-content">
                                <span className="text-muted" style={{ fontSize: '13px' }}>
                                  {credential.created_by || 'N/A'}
                                </span>
                              </div>
                            </CTableDataCell>
                            <CTableDataCell className="table-cell">
                              <div className="cell-content">
                                <span className="text-muted" style={{ fontSize: '13px' }}>
                                  {credential.updated_by || 'N/A'}
                                </span>
                              </div>
                            </CTableDataCell>
                            <CTableDataCell className="table-cell" style={{ textAlign: 'center' }}>
                              <div className="cell-content" style={{ justifyContent: 'center' }}>
                                <LLMCredentialActionButtons
                                  credential={credential}
                                  onEdit={() => openCredentialModal('Edit', credential)}
                                  onDelete={() => openCredentialModal('Delete', credential)}
                                  onToggleStatus={handleToggleCredentialStatus}
                                  onToggleCrmFlow={handleToggleCrmFlow}
                                />
                              </div>
                            </CTableDataCell>
                          </CTableRow>
                        ))}
                      </CTableBody>
                    </CTable>
                  </div>
                  
                  {/* Pagination for credentials */}
                  {credentialsTotalCount > 0 && (
                    <PaginationComponent
                      currentPage={credentialsCurrentPage}
                      totalPages={credentialsTotalPages}
                      onPageChange={handleCredentialsPageChange}
                    />
                  )}
                </>
              )}
            </CTabPane>

            {/* Agent Mappings Tab */}
            <CTabPane visible={activeTab === 'agents'}>
              <AgentMappingTab
                companyId={company.id}
                onAlert={showToastAlert}
                credentialsRefreshTrigger={credentialsRefreshTrigger}
              />
            </CTabPane>
          </CTabContent>
        </CCardBody>
      </CCard>

      {/* Add Credential Modal */}
      <AddCredentialModal
        visible={showAddCredentialModal}
        onClose={() => setShowAddCredentialModal(false)}
        onSubmit={handleCreateCredential}
        companyId={company?.id}
        loading={submitLoading}
      />

      {/* Edit Credential Modal */}
      <LLMCredentialEditModal
        visible={credentialModals.showEditModal}
        onClose={() => closeCredentialModal('Edit')}
        onSubmit={handleUpdateCredential}
        credential={selectedCredential}
        loading={credentialSubmitLoading}
      />

      {/* Delete Credential Modal */}
      <DeleteCredentialModal
        visible={credentialModals.showDeleteModal}
        onClose={() => closeCredentialModal('Delete')}
        onConfirm={handleDeleteCredential}
        credential={selectedCredential}
        loading={credentialSubmitLoading}
      />


      {/* Toast Notifications */}
      <Toast 
        message={alertMessage}
        type={alertType}
        onClose={() => setAlertMessage('')}
      />
    </CContainer>
  );
};

export default CompanyDetailPage;
