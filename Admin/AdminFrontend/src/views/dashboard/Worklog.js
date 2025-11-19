import React, { useState, useEffect, useRef } from 'react';
import {
  CRow,
  CCol,
  CTable,
  CTableHead,
  CTableBody,
  CTableRow,
  CTableHeaderCell,
  CTableDataCell,
  CSpinner,
  CContainer,
  CCard,
  CCardBody,
  CCardHeader,
  CFormInput,
  CFormSelect,
  CButton
} from '@coreui/react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { GetSessionCounts } from '../../Api/Auth';
import PaginationComponent from '../base/paginations/PaginationComponent';
import SearchQuery from '../base/SearchBar/SearchQuery.jsx';
import { DateRange } from "react-date-range";
import { format, parseISO } from "date-fns";
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { faCalendarDays, faFilter, faFilterCircleXmark } from "@fortawesome/free-solid-svg-icons";
import 'react-date-range/dist/styles.css';
import 'react-date-range/dist/theme/default.css';
import { availableAppname } from '../../Api/Auth';
import { useButtonHover } from '../../hooks/useButtonHover';
import { ADKIconButton } from '../../components/ADKButton';

const Worklog = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [sessionData, setSessionData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [totalPages, setTotalPages] = useState(1);
  const [pageSize] = useState(15);
  const token = localStorage.getItem('access_token');

  const queryParams = new URLSearchParams(location.search);
  const [currentPage, setCurrentPage] = useState(parseInt(queryParams.get('page')) || 1);

  const [query, setQuery] = useState(queryParams.get('email') || "");
  const [appNameFilter, setAppNameFilter] = useState(queryParams.get('app') || "");
  const [modeFilter, setModeFilter] = useState(queryParams.get('mode') || "");
  const [sessionIdFilter, setSessionIdFilter] = useState(queryParams.get('sessionId') || "");
  const [countFilter, setCountFilter] = useState(queryParams.get('count') || "");
  const today = new Date();
  const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
  const [startDate, setStartDate] = useState(
    queryParams.get('start') ? parseISO(queryParams.get('start')) : firstDayOfMonth
  );
  const [endDate, setEndDate] = useState(
    queryParams.get('end') ? parseISO(queryParams.get('end')) : today
  );
  const selectionRange = { startDate, endDate };
  const [openDateRange, setOpenDateRange] = useState(false);
  const refOne = useRef();

  // Update URL when filters change
  useEffect(() => {
    const params = new URLSearchParams();

    if (query) params.set('email', query);
    if (appNameFilter) params.set('app', appNameFilter);
    if (modeFilter) params.set('mode', modeFilter);
    if (sessionIdFilter) params.set('sessionId', sessionIdFilter);
    if (countFilter) params.set('count', countFilter);
    params.set('start', startDate.toISOString());
    params.set('end', endDate.toISOString());
    params.set('page', currentPage);

    navigate(`?${params.toString()}`, { replace: true });
  }, [
    query,
    appNameFilter,
    modeFilter,
    sessionIdFilter,
    countFilter,
    startDate,
    endDate,
    currentPage,
    navigate
  ]);

  const prevloc = useLocation(); // To get the current location

  // Store the previous route path
  const previousRoute = prevloc.pathname;
  // Handle date range selection
  const handleDateRange = (range) => {
    setStartDate(range.range1.startDate);
    setEndDate(range.range1.endDate);
    setCurrentPage(1);
  };



  const [apps, setApps] = useState([]);

  const Availableapp = async () => {
    try {
      const res = await availableAppname(token);
      console.log(res);
      if (res?.app_names?.length) {
        setApps(res.app_names);
      }
    } catch (error) {
      console.log('Error fetching app names:', error);
    }
  };

  useEffect(() => {
    Availableapp();
  }, [token]);


  const handleRowClick = (sessionId) => {
    navigate(`${previousRoute}/session/${sessionId}`);
  };

  // Close date picker when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (refOne.current && !refOne.current.contains(event.target)) {
        setOpenDateRange(false);
      }
    };

    if (openDateRange) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [openDateRange]);

  useEffect(() => {
    setLoading(true);
    localStorage.setItem("win_loc", window.location.href);
    GetSessionCounts(
      token,
      currentPage,
      pageSize,
      query,
      startDate,
      endDate,
      appNameFilter,
      sessionIdFilter,
      modeFilter,
      query,
      countFilter
    )
      .then((data) => {
        setSessionData(data.data || []);
        setTotalPages(data.total_pages || 1);
        setLoading(false);
      })
      .catch((error) => {
        console.error('Error fetching session data:', error);
        setLoading(false);
      });
  }, [
    token,
    currentPage,
    pageSize,
    query,
    startDate,
    endDate,
    appNameFilter,
    modeFilter,
    sessionIdFilter,
    countFilter
  ]);

  // Reset all filters
  const clearFilters = () => {
    setQuery("");
    setAppNameFilter("");
    setModeFilter("");
    setSessionIdFilter("");
    setCountFilter("");
    setStartDate(new Date());
    setEndDate(new Date());
    setCurrentPage(1);

    navigate(location.pathname, { replace: true });
  };

  const handleSearchChange = (searchQuery) => {
    setQuery(searchQuery);
    setCurrentPage(1);
  };


  const columns = [
    { key: 'session_id', label: 'Session ID' },
    { key: 'count', label: 'Agent call' },
    { key: 'email', label: 'Email' },
    { key: 'app_name', label: 'App Name' },
    { key: 'mode', label: 'Mode' },
    { key: 'timestamp', label: 'Last Activity' },
    { key: 'actions', label: 'ADK' },
  ];

  const items = sessionData.map((session, index) => ({
    session_id: (
      <div className="cell-content session-id">
        <span className="cell-value">{session.session_id}</span>
      </div>
    ),
    count: (
      <div className="cell-content">
        <span className="cell-value">{session.count}</span>
      </div>
    ),
    email: (
      <div className="cell-content">
        <span className="cell-value">{session.user_id}</span>
      </div>
    ),
    app_name: (
      <div className="cell-content">
        <span className="cell-value">{session.app_name}</span>
      </div>
    ),
    mode: (
      <div className="cell-content">
        <span className="cell-value">{session.mode}</span>
      </div>
    ),
    timestamp: (
      <div className="cell-content left">
        <span className="cell-value muted">
          {new Date(session.last_timestamp).toLocaleString()}
        </span>
      </div>
    ),
    actions: (
      <div className="cell-content" style={{ textAlign: 'center' }}>
        <ADKIconButton
          appName={session.app_name}
          userId={session.user_id}
          sessionId={session.session_id}
        />
      </div>
    ),
  }));

  const handlePageChange = (newPage) => {
    if (newPage !== currentPage) {
      setCurrentPage(newPage);
    }
  };

  // Update URL when currentPage changes
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (currentPage > 1) {
      params.set('page', currentPage.toString());
    } else {
      params.delete('page');
    }
    navigate(`?${params.toString()}`, { replace: true });
  }, [currentPage, navigate, location.search]);

  // Update currentPage state when URL changes
  useEffect(() => {
    const newPageFromUrl = parseInt(new URLSearchParams(location.search).get('page')) || 1;
    if (newPageFromUrl !== currentPage) {
      setCurrentPage(newPageFromUrl);
    }
  }, [location.search]);

  // Check if any filter is active
  const isFilterActive = query || appNameFilter || modeFilter ||
    sessionIdFilter || countFilter ||
    startDate.toDateString() !== new Date().toDateString() ||
    endDate.toDateString() !== new Date().toDateString();

  // Modern button styles (matching Company Listing Page)
  const buttonStyle = {
    borderRadius: '10px',
    fontWeight: '600',
    padding: '8px 16px',
    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
    position: 'relative',
    overflow: 'hidden'
  };

  const clearButtonStyle = {
    ...buttonStyle,
    border: '2px solid #6c757d',
    color: '#6c757d',
    backgroundColor: 'rgba(108, 117, 125, 0.08)',
    boxShadow: '0 3px 10px rgba(108, 117, 125, 0.15)'
  };


  return (
    <CContainer fluid>
      <CCard className="data-card">
        <CCardHeader className="data-card-header">
          <CRow className="align-items-center">
            <CCol xs={12} md={6} className="mb-3 mb-md-0">
              <h4 className="card-title mb-0">Session Overview</h4>
            </CCol>
            <CCol xs={12} md={6}>
              <div className="d-flex flex-column flex-sm-row align-items-stretch align-items-sm-center justify-content-md-end gap-2">
                <div className="calenderWarp position-relative">
                  <input
                    readOnly
                    value={`${format(selectionRange.startDate, "MM/dd/yyyy")} to ${format(
                      selectionRange.endDate,
                      "MM/dd/yyyy"
                    )}`}
                    onClick={() => setOpenDateRange((prev) => !prev)}
                    autoFocus={false}
                    className="inputBox"
                    style={{ minWidth: '200px' }}
                  />
                  <span className="date-icon">
                    <FontAwesomeIcon className="font-20" icon={faCalendarDays} />
                  </span>
                  <div ref={refOne}>
                    {openDateRange && (
                      <DateRange
                        ranges={[selectionRange]}
                        onChange={handleDateRange}
                        editableDateInputs={true}
                        moveRangeOnFirstSelection={false}
                        months={1}
                        direction="vertical"
                        className="calendarElement"
                        maxDate={new Date()}
                      />
                    )}
                  </div>
                </div>
                <div className="d-flex align-items-center gap-2">
                  {isFilterActive && (
                    <CButton
                      variant="outline"
                      onClick={clearFilters}
                      className="d-flex align-items-center"
                      style={clearButtonStyle}
                      size="sm"
                    >
                      <FontAwesomeIcon icon={faFilterCircleXmark} className="me-1" />
                      <span className="d-none d-sm-inline">Clear Filters</span>
                    </CButton>
                  )}
                  {!loading && sessionData.length > 0 && (
                    <span className="record-badge text-nowrap">
                      {sessionData.length} {sessionData.length === 1 ? 'Record' : 'Records'}
                    </span>
                  )}
                </div>
              </div>
            </CCol>
          </CRow>
        </CCardHeader>

        <CCardBody className="data-card-body">
          {loading ? (
            <div className="loading-container">
              <CSpinner color="primary" size="lg" />
              <p>Loading session data...</p>
            </div>
          ) : sessionData.length === 0 ? (
            <div className="empty-state text-center py-4">
              <i className="fas fa-inbox fa-2x mb-2" />
              <p>No session details available.</p>
              {isFilterActive && (
                <CButton color="primary" onClick={clearFilters}>
                  Clear filters
                </CButton>
              )}
            </div>
          ) : (
            <>
              {/* Mobile Filters - Show on small screens */}
              <div className="d-block d-lg-none mb-3">
                <CRow className="g-2">
                  <CCol xs={12} sm={6}>
                    <SearchQuery
                      placeholder="Search by Session ID"
                      onSearchChange={(val) => {
                        setSessionIdFilter(val);
                        setCurrentPage(1);
                      }}
                      value={sessionIdFilter}
                      icon={true}
                    />
                  </CCol>
                  <CCol xs={12} sm={6}>
                    <SearchQuery
                      placeholder="Search by email"
                      onSearchChange={handleSearchChange}
                      value={query}
                      icon={true}
                    />
                  </CCol>
                  <CCol xs={12} sm={6}>
                    <CFormSelect
                      value={appNameFilter}
                      onChange={(e) => {
                        setAppNameFilter(e.target.value);
                        setCurrentPage(1);
                      }}
                      size="sm"
                    >
                      <option value="">All Apps</option>
                      {apps.map((app) => (
                        <option key={app} value={app}>
                          {app
                            .split('_')
                            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                            .join(' ')}
                        </option>
                      ))}
                    </CFormSelect>
                  </CCol>
                  <CCol xs={12} sm={6}>
                    <CFormSelect
                      value={modeFilter}
                      onChange={(e) => {
                        setModeFilter(e.target.value);
                        setCurrentPage(1);
                      }}
                      size="sm"
                    >
                      <option value="">All Modes</option>
                      <option value="whatsapp">WhatsApp</option>
                      <option value="slack">Slack</option>
                      <option value="postman">Postman</option>
                      <option value="web">Website</option>
                    </CFormSelect>
                  </CCol>
                </CRow>
              </div>

              {/* Desktop Table - Show on large screens */}
              <div 
                className="table-responsive d-none d-lg-block" 
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
                <CTable hover className="clean-table" style={{ minWidth: '1000px' }}>
                  <CTableHead className="table-header">
                    <CTableRow>
                      {columns.map((column) => (
                        <CTableHeaderCell
                          key={column.key}
                          scope="col"
                          className={column.className || ''}
                          style={{ 
                            width: column.key === 'session_id' ? '150px' : 
                                   column.key === 'count' ? '120px' :
                                   column.key === 'email' ? '200px' :
                                   column.key === 'app_name' ? '150px' :
                                   column.key === 'mode' ? '120px' : 
                                   column.key === 'timestamp' ? '180px' : '80px',
                            minWidth: column.key === 'session_id' ? '150px' : 
                                      column.key === 'count' ? '120px' :
                                      column.key === 'email' ? '200px' :
                                      column.key === 'app_name' ? '150px' :
                                      column.key === 'mode' ? '120px' : 
                                      column.key === 'timestamp' ? '180px' : '80px'
                          }}
                        >
                          {column.label}
                        </CTableHeaderCell>
                      ))}
                    </CTableRow>
                    <CTableRow className="filter-row">
                      <CTableHeaderCell style={{ width: '150px', minWidth: '150px' }}>
                        <SearchQuery
                          placeholder="Search by Session ID"
                          onSearchChange={(val) => {
                            setSessionIdFilter(val);
                            setCurrentPage(1);
                          }}
                          value={sessionIdFilter}
                          icon={true}
                        />
                      </CTableHeaderCell>
                      <CTableHeaderCell style={{ width: '120px', minWidth: '120px' }}>
                        {/* Empty for Agent call count - no filter needed */}
                      </CTableHeaderCell>
                      <CTableHeaderCell style={{ width: '200px', minWidth: '200px' }}>
                        <SearchQuery
                          placeholder="Search by email"
                          onSearchChange={handleSearchChange}
                          value={query}
                          icon={true}
                        />
                      </CTableHeaderCell>
                      <CTableHeaderCell style={{ width: '150px', minWidth: '150px' }}>
                        <CFormSelect
                          value={appNameFilter}
                          onChange={(e) => {
                            setAppNameFilter(e.target.value);
                            setCurrentPage(1);
                          }}
                          size="sm"
                        >
                          <option value="">All Apps</option>
                          {apps.map((app) => (
                            <option key={app} value={app}>
                              {app
                                .split('_')
                                .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                                .join(' ')}
                            </option>
                          ))}
                        </CFormSelect>
                      </CTableHeaderCell>
                      <CTableHeaderCell style={{ width: '120px', minWidth: '120px' }}>
                        <CFormSelect
                          value={modeFilter}
                          onChange={(e) => {
                            setModeFilter(e.target.value);
                            setCurrentPage(1);
                          }}
                          size="sm"
                        >
                          <option value="">All Modes</option>
                          <option value="whatsapp">WhatsApp</option>
                          <option value="slack">Slack</option>
                          <option value="postman">Postman</option>
                          <option value="web">Website</option>
                        </CFormSelect>
                      </CTableHeaderCell>
                      <CTableHeaderCell style={{ width: '180px', minWidth: '180px' }}>
                        {/* Last Activity column - no filter */}
                      </CTableHeaderCell>
                      <CTableHeaderCell style={{ width: '80px', minWidth: '80px' }}>
                        {/* ADK actions column - no filter */}
                      </CTableHeaderCell>
                    </CTableRow>
                  </CTableHead>
                  <CTableBody>
                    {items.map((item, index) => (
                      <CTableRow
                        key={index}
                        className="table-row clickable-row"
                        onClick={() => handleRowClick(sessionData[index].session_id)}
                        style={{ cursor: 'pointer' }}
                      >
                        {Object.keys(item).map((key, idx) => (
                          <CTableDataCell 
                            key={idx}
                            style={{ 
                              width: key === 'session_id' ? '150px' : 
                                     key === 'count' ? '120px' :
                                     key === 'email' ? '200px' :
                                     key === 'app_name' ? '150px' :
                                     key === 'mode' ? '120px' : 
                                     key === 'timestamp' ? '180px' : '80px',
                              minWidth: key === 'session_id' ? '150px' : 
                                        key === 'count' ? '120px' :
                                        key === 'email' ? '200px' :
                                        key === 'app_name' ? '150px' :
                                        key === 'mode' ? '120px' : 
                                        key === 'timestamp' ? '180px' : '80px'
                            }}
                          >
                            {item[key]}
                          </CTableDataCell>
                        ))}
                      </CTableRow>
                    ))}
                  </CTableBody>
                </CTable>
              </div>

              {/* Mobile Cards - Show on small screens */}
              <div className="d-block d-lg-none">
                {items.map((item, index) => (
                  <CCard 
                    key={index} 
                    className="mb-3 clickable-card" 
                    onClick={() => handleRowClick(sessionData[index].session_id)}
                    style={{ cursor: 'pointer' }}
                  >
                    <CCardBody className="p-3">
                      <CRow className="g-2">
                        <CCol xs={12}>
                          <div className="d-flex justify-content-between align-items-start">
                            <div>
                              <strong className="text-primary">Session ID:</strong>
                              <div className="fw-bold">{sessionData[index].session_id}</div>
                            </div>
                            <div className="text-end">
                              <small className="text-muted">
                                {new Date(sessionData[index].first_timestamp).toLocaleString()}
                              </small>
                            </div>
                          </div>
                        </CCol>
                        <CCol xs={6}>
                          <strong>Agent Calls:</strong>
                          <div>{sessionData[index].count}</div>
                        </CCol>
                        <CCol xs={6}>
                          <strong>Mode:</strong>
                          <div>{sessionData[index].mode}</div>
                        </CCol>
                        <CCol xs={12}>
                          <strong>Email:</strong>
                          <div className="text-break">{sessionData[index].user_id}</div>
                        </CCol>
                        <CCol xs={12}>
                          <strong>App Name:</strong>
                          <div>{sessionData[index].app_name}</div>
                        </CCol>
                      </CRow>
                    </CCardBody>
                  </CCard>
                ))}
              </div>

              <PaginationComponent
                currentPage={currentPage}
                totalPages={totalPages}
                onPageChange={handlePageChange}
              />
            </>
          )}
        </CCardBody>
      </CCard>
    </CContainer>
  );
};

export default Worklog;