import React, { useState, useEffect, useCallback } from 'react';
import {
  CCard,
  CCardBody,
  CCardHeader,
  CCol,
  CRow,
  CTable,
  CTableHead,
  CTableRow,
  CTableHeaderCell,
  CTableBody,
  CTableDataCell,
  CSpinner,
  CBadge,
  CForm,
  CFormInput,
  CFormSelect,
  CButton,
  CInputGroup,
  CInputGroupText,
  CTooltip,
  CCollapse,
  CPagination,
  CPaginationItem,
} from '@coreui/react';
import CIcon from '@coreui/icons-react';
import {
  cilFilter,
  cilReload,
  cilSearch,
  cilX,
  cilChevronBottom,
  cilChevronTop,
  cilInfo,
} from '@coreui/icons';
import endpoints from '../../Constants/endpoints';
import sendRequest from '../../Api/SendRequest';
import '../../scss/login.scss';

const NetworkActivity = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [showFilters, setShowFilters] = useState(false);
  const [expandedRow, setExpandedRow] = useState(null);

  // Filter states
  const [filters, setFilters] = useState({
    endpoint: '',
    method: '',
    ip_address: '',
    device_type: '',
    user_id: '',
    company_id: '',
    date_from: '',
    date_to: '',
  });

  // Fetch network activity logs
  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const url = endpoints.network_activity.list(currentPage, pageSize, filters);
      const response = await sendRequest({
        url,
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.status === 'success') {
        setLogs(response.data);
        setTotalPages(response.pagination.total_pages);
        setTotalCount(response.pagination.total_count);
      }
    } catch (error) {
      console.error('Error fetching network activity logs:', error);
    } finally {
      setLoading(false);
    }
  }, [currentPage, pageSize, filters]);

  // Fetch statistics
  const fetchStats = useCallback(async () => {
    try {
      const token = localStorage.getItem('access_token');
      const url = endpoints.network_activity.stats();
      const response = await sendRequest({
        url,
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.status === 'success') {
        setStats(response.data);
      }
    } catch (error) {
      console.error('Error fetching network activity stats:', error);
    }
  }, []);

  useEffect(() => {
    fetchLogs();
    fetchStats();
  }, [fetchLogs, fetchStats]);

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilters((prev) => ({ ...prev, [name]: value }));
  };

  const handleApplyFilters = () => {
    setCurrentPage(1);
    fetchLogs();
  };

  const handleClearFilters = () => {
    setFilters({
      endpoint: '',
      method: '',
      ip_address: '',
      device_type: '',
      user_id: '',
      company_id: '',
      date_from: '',
      date_to: '',
    });
    setCurrentPage(1);
  };

  const handleRefresh = () => {
    fetchLogs();
    fetchStats();
  };

  const toggleRowExpand = (id) => {
    setExpandedRow(expandedRow === id ? null : id);
  };

  const getDeviceBadge = (deviceType) => {
    const colors = {
      mobile: 'info',
      desktop: 'success',
      tablet: 'warning',
      bot: 'danger',
      unknown: 'secondary',
    };
    return <CBadge color={colors[deviceType] || 'secondary'}>{deviceType || 'unknown'}</CBadge>;
  };

  const getMethodBadge = (method) => {
    const colors = {
      GET: 'info',
      POST: 'success',
      PUT: 'warning',
      DELETE: 'danger',
      PATCH: 'primary',
    };
    return <CBadge color={colors[method] || 'secondary'}>{method}</CBadge>;
  };

  const formatDateTime = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const renderPagination = () => {
    const maxVisible = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let endPage = Math.min(totalPages, startPage + maxVisible - 1);

    if (endPage - startPage < maxVisible - 1) {
      startPage = Math.max(1, endPage - maxVisible + 1);
    }

    const pages = [];
    for (let i = startPage; i <= endPage; i++) {
      pages.push(
        <CPaginationItem
          key={i}
          active={i === currentPage}
          onClick={() => setCurrentPage(i)}
        >
          {i}
        </CPaginationItem>
      );
    }

    return (
      <CPagination className="justify-content-center">
        <CPaginationItem
          disabled={currentPage === 1}
          onClick={() => setCurrentPage(currentPage - 1)}
        >
          Previous
        </CPaginationItem>
        {startPage > 1 && (
          <>
            <CPaginationItem onClick={() => setCurrentPage(1)}>1</CPaginationItem>
            {startPage > 2 && <CPaginationItem disabled>...</CPaginationItem>}
          </>
        )}
        {pages}
        {endPage < totalPages && (
          <>
            {endPage < totalPages - 1 && <CPaginationItem disabled>...</CPaginationItem>}
            <CPaginationItem onClick={() => setCurrentPage(totalPages)}>
              {totalPages}
            </CPaginationItem>
          </>
        )}
        <CPaginationItem
          disabled={currentPage === totalPages}
          onClick={() => setCurrentPage(currentPage + 1)}
        >
          Next
        </CPaginationItem>
      </CPagination>
    );
  };

  return (
    <>
      {/* Statistics Cards */}
      {stats && (
        <CRow className="mb-4">
          <CCol sm={6} lg={3}>
            <CCard className="text-white bg-primary">
              <CCardBody className="pb-0 d-flex justify-content-between align-items-start">
                <div>
                  <div className="fs-4 fw-semibold">{stats.total_requests.toLocaleString()}</div>
                  <div>Total Requests</div>
                </div>
              </CCardBody>
            </CCard>
          </CCol>
          <CCol sm={6} lg={3}>
            <CCard className="text-white bg-info">
              <CCardBody className="pb-0 d-flex justify-content-between align-items-start">
                <div>
                  <div className="fs-4 fw-semibold">
                    {stats.device_distribution?.find((d) => d.device_type === 'mobile')?.count || 0}
                  </div>
                  <div>Mobile Devices</div>
                </div>
              </CCardBody>
            </CCard>
          </CCol>
          <CCol sm={6} lg={3}>
            <CCard className="text-white bg-warning">
              <CCardBody className="pb-0 d-flex justify-content-between align-items-start">
                <div>
                  <div className="fs-4 fw-semibold">
                    {stats.device_distribution?.find((d) => d.device_type === 'desktop')?.count || 0}
                  </div>
                  <div>Desktop Devices</div>
                </div>
              </CCardBody>
            </CCard>
          </CCol>
          <CCol sm={6} lg={3}>
            <CCard className="text-white bg-danger">
              <CCardBody className="pb-0 d-flex justify-content-between align-items-start">
                <div>
                  <div className="fs-4 fw-semibold">
                    {stats.device_distribution?.find((d) => d.device_type === 'bot')?.count || 0}
                  </div>
                  <div>Bot Requests</div>
                </div>
              </CCardBody>
            </CCard>
          </CCol>
        </CRow>
      )}

      {/* Main Table */}
      <CCard>
        <CCardHeader className="d-flex justify-content-between align-items-center">
          <strong>Network Activity Logs</strong>
          <div>
            <CButton
              color="primary"
              variant="ghost"
              size="sm"
              className="me-2"
              onClick={() => setShowFilters(!showFilters)}
            >
              <CIcon icon={cilFilter} className="me-1" />
              {showFilters ? 'Hide Filters' : 'Show Filters'}
              <CIcon icon={showFilters ? cilChevronTop : cilChevronBottom} className="ms-1" />
            </CButton>
            <CButton color="info" variant="ghost" size="sm" onClick={handleRefresh}>
              <CIcon icon={cilReload} className="me-1" />
              Refresh
            </CButton>
          </div>
        </CCardHeader>

        {/* Filters */}
        <CCollapse visible={showFilters}>
          <CCardBody className="border-bottom">
            <CForm>
              <CRow className="g-3">
                <CCol md={3}>
                  <CFormInput
                    type="text"
                    name="endpoint"
                    placeholder="Endpoint"
                    value={filters.endpoint}
                    onChange={handleFilterChange}
                    size="sm"
                  />
                </CCol>
                <CCol md={2}>
                  <CFormSelect
                    name="method"
                    value={filters.method}
                    onChange={handleFilterChange}
                    size="sm"
                  >
                    <option value="">All Methods</option>
                    <option value="GET">GET</option>
                    <option value="POST">POST</option>
                    <option value="PUT">PUT</option>
                    <option value="DELETE">DELETE</option>
                    <option value="PATCH">PATCH</option>
                  </CFormSelect>
                </CCol>
                <CCol md={2}>
                  <CFormInput
                    type="text"
                    name="ip_address"
                    placeholder="IP Address"
                    value={filters.ip_address}
                    onChange={handleFilterChange}
                    size="sm"
                  />
                </CCol>
                <CCol md={2}>
                  <CFormSelect
                    name="device_type"
                    value={filters.device_type}
                    onChange={handleFilterChange}
                    size="sm"
                  >
                    <option value="">All Devices</option>
                    <option value="mobile">Mobile</option>
                    <option value="desktop">Desktop</option>
                    <option value="tablet">Tablet</option>
                    <option value="bot">Bot</option>
                  </CFormSelect>
                </CCol>
                <CCol md={3}>
                  <CFormInput
                    type="text"
                    name="user_id"
                    placeholder="User ID (Email)"
                    value={filters.user_id}
                    onChange={handleFilterChange}
                    size="sm"
                  />
                </CCol>
                <CCol md={2}>
                  <CFormInput
                    type="text"
                    name="company_id"
                    placeholder="Company ID"
                    value={filters.company_id}
                    onChange={handleFilterChange}
                    size="sm"
                  />
                </CCol>
                <CCol md={2}>
                  <CFormInput
                    type="date"
                    name="date_from"
                    placeholder="From Date"
                    value={filters.date_from}
                    onChange={handleFilterChange}
                    size="sm"
                  />
                </CCol>
                <CCol md={2}>
                  <CFormInput
                    type="date"
                    name="date_to"
                    placeholder="To Date"
                    value={filters.date_to}
                    onChange={handleFilterChange}
                    size="sm"
                  />
                </CCol>
                <CCol md={6} className="d-flex gap-2">
                  <CButton color="primary" size="sm" onClick={handleApplyFilters}>
                    <CIcon icon={cilSearch} className="me-1" />
                    Apply Filters
                  </CButton>
                  <CButton
                    color="secondary"
                    variant="outline"
                    size="sm"
                    onClick={handleClearFilters}
                  >
                    <CIcon icon={cilX} className="me-1" />
                    Clear
                  </CButton>
                </CCol>
              </CRow>
            </CForm>
          </CCardBody>
        </CCollapse>

        <CCardBody>
          {loading ? (
            <div className="text-center py-5">
              <CSpinner color="primary" />
              <div className="mt-2">Loading network activity logs...</div>
            </div>
          ) : (
            <>
              <div className="mb-3 d-flex justify-content-between align-items-center">
                <div>
                  <small className="text-medium-emphasis">
                    Showing {logs.length} of {totalCount.toLocaleString()} records
                  </small>
                </div>
                <CFormSelect
                  size="sm"
                  style={{ width: 'auto' }}
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value));
                    setCurrentPage(1);
                  }}
                >
                  <option value="10">10 per page</option>
                  <option value="20">20 per page</option>
                  <option value="50">50 per page</option>
                  <option value="100">100 per page</option>
                </CFormSelect>
              </div>

              <div className="table-responsive">
                <CTable hover striped bordered small>
                  <CTableHead>
                    <CTableRow>
                      <CTableHeaderCell style={{ width: '40px' }}></CTableHeaderCell>
                      <CTableHeaderCell>Timestamp</CTableHeaderCell>
                      <CTableHeaderCell>Endpoint</CTableHeaderCell>
                      <CTableHeaderCell>Method</CTableHeaderCell>
                      <CTableHeaderCell>IP Address</CTableHeaderCell>
                      <CTableHeaderCell>Device</CTableHeaderCell>
                      <CTableHeaderCell>Browser</CTableHeaderCell>
                      <CTableHeaderCell>User ID</CTableHeaderCell>
                    </CTableRow>
                  </CTableHead>
                  <CTableBody>
                    {logs.length === 0 ? (
                      <CTableRow>
                        <CTableDataCell colSpan="8" className="text-center py-4">
                          No network activity logs found
                        </CTableDataCell>
                      </CTableRow>
                    ) : (
                      logs.map((log) => (
                        <React.Fragment key={log.id}>
                          <CTableRow>
                            <CTableDataCell>
                              <CButton
                                size="sm"
                                color="link"
                                onClick={() => toggleRowExpand(log.id)}
                              >
                                <CIcon
                                  icon={expandedRow === log.id ? cilChevronTop : cilChevronBottom}
                                />
                              </CButton>
                            </CTableDataCell>
                            <CTableDataCell>
                              <small>{formatDateTime(log.created_at)}</small>
                            </CTableDataCell>
                            <CTableDataCell>
                              <code className="text-primary">{log.endpoint}</code>
                            </CTableDataCell>
                            <CTableDataCell>{getMethodBadge(log.method)}</CTableDataCell>
                            <CTableDataCell>
                              <code>{log.ip_address || 'N/A'}</code>
                            </CTableDataCell>
                            <CTableDataCell>{getDeviceBadge(log.device_type)}</CTableDataCell>
                            <CTableDataCell>
                              {log.browser ? (
                                <span>
                                  {log.browser}
                                  {log.browser_version && (
                                    <small className="text-medium-emphasis"> v{log.browser_version}</small>
                                  )}
                                </span>
                              ) : (
                                'N/A'
                              )}
                            </CTableDataCell>
                            <CTableDataCell>
                              <small>{log.user_id || 'Anonymous'}</small>
                            </CTableDataCell>
                          </CTableRow>
                          {expandedRow === log.id && (
                            <CTableRow>
                              <CTableDataCell colSpan="8" className="bg-light">
                                <CRow className="g-3 p-3">
                                  <CCol md={6}>
                                    <strong>Operating System:</strong>{' '}
                                    {log.os ? `${log.os} ${log.os_version || ''}` : 'N/A'}
                                  </CCol>
                                  <CCol md={6}>
                                    <strong>Platform:</strong> {log.platform || 'N/A'}
                                  </CCol>
                                  <CCol md={6}>
                                    <strong>Session ID:</strong>{' '}
                                    <code>{log.session_id || 'N/A'}</code>
                                  </CCol>
                                  <CCol md={6}>
                                    <strong>Company ID:</strong> {log.company_id || 'N/A'}
                                  </CCol>
                                  <CCol md={6}>
                                    <strong>Origin:</strong> {log.origin || 'N/A'}
                                  </CCol>
                                  <CCol md={6}>
                                    <strong>Host:</strong> {log.host || 'N/A'}
                                  </CCol>
                                  <CCol md={6}>
                                    <strong>Referer:</strong>{' '}
                                    <small>{log.referer || 'N/A'}</small>
                                  </CCol>
                                  <CCol md={6}>
                                    <strong>Status Code:</strong>{' '}
                                    <CBadge
                                      color={
                                        log.status_code >= 200 && log.status_code < 300
                                          ? 'success'
                                          : log.status_code >= 400
                                          ? 'danger'
                                          : 'warning'
                                      }
                                    >
                                      {log.status_code || 'N/A'}
                                    </CBadge>
                                  </CCol>
                                  {log.forwarded_for && (
                                    <CCol md={12}>
                                      <strong>Forwarded For:</strong>{' '}
                                      <code>{log.forwarded_for}</code>
                                    </CCol>
                                  )}
                                  <CCol md={12}>
                                    <strong>User Agent:</strong>
                                    <div className="mt-1">
                                      <small className="font-monospace text-medium-emphasis">
                                        {log.user_agent || 'N/A'}
                                      </small>
                                    </div>
                                  </CCol>
                                  <CCol md={12}>
                                    <strong>Request ID:</strong>{' '}
                                    <code className="text-muted">{log.request_id}</code>
                                  </CCol>
                                </CRow>
                              </CTableDataCell>
                            </CTableRow>
                          )}
                        </React.Fragment>
                      ))
                    )}
                  </CTableBody>
                </CTable>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="mt-3">
                  {renderPagination()}
                </div>
              )}
            </>
          )}
        </CCardBody>
      </CCard>
    </>
  );
};

export default NetworkActivity;

