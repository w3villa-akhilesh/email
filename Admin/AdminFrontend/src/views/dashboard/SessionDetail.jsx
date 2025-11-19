import { useState, useEffect } from "react";
import {
  CTable,
  CSpinner,
  CTableHead,
  CTableRow,
  CTableDataCell,
  CTableBody,
  CContainer,
  CCard,
  CCardBody,
  CCardHeader,
} from "@coreui/react";
import { GetSessionDetails, GetContentDetails, GetContentSessionDetails } from "../../Api/Auth";
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import PaginationComponent from "../base/paginations/PaginationComponent";
import { Link } from 'react-router-dom';
import ContentModal from './ContentModal';
import ViewAllModal from "./ViewAllmodal";
import ADKButton from '../../components/ADKButton';

const SessionDetail = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { session_id } = useParams();
  
  // Extract app_name and user_id from session data for ADK integration
  const [appName, setAppName] = useState(null);
  const [userIdForADK, setUserIdForADK] = useState(null);
  
  // Get page from URL parameters
  const queryParams = new URLSearchParams(location.search);
  const pageFromUrl = parseInt(queryParams.get('page')) || 1;
  
  const [sessionData, setSessionData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(pageFromUrl);
  const [totalPages, setTotalPages] = useState(1);
  const [showModal, setShowModal] = useState(false);
  const [modalContent, setModalContent] = useState(null);
  const [showViewAllModal, setShowViewAllModal] = useState(false);
  const [allContent, setAllContent] = useState(null);

  // Helper function to get token from localStorage
  const getAuthToken = () => {
    const token = localStorage.getItem('access_token');
    return token;
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        const token = getAuthToken();
        
        const response = await GetSessionDetails(token, session_id, currentPage);
        if (response && Array.isArray(response.data)) {
          setSessionData(response.data);
          setTotalPages(response.total_pages);
          
          // Extract app_name and user_id for ADK integration (from first event)
          if (response.data.length > 0 && response.data[0].app_name) {
            setAppName(response.data[0].app_name);
          }
          if (response.data.length > 0 && response.data[0].user_id) {
            setUserIdForADK(response.data[0].user_id);
          }
        } else {
          console.error("Failed to fetch session details:", response?.message || "No data found.");
        }
      } catch (error) {
        console.error("Error fetching session details:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [session_id, currentPage]);

  const handleViewAllClick = async () => {
    try {
      const token = getAuthToken();
      
      const allContent = await GetContentSessionDetails(token, session_id);
      setAllContent(allContent);
      setShowViewAllModal(true);
    } catch (error) {
      console.error("Error fetching all content:", error);
    }
  };

  const columns = [
    { key: "id", label: "ID"},
    { key: "author", label: "Author" },
    { key: "call_type", label: "Call type" },
    { key: "content", label: "Content"},
    { key: "timestamp", label: "created At" },
  ];

  const items = Array.isArray(sessionData) ? sessionData.map((session, index) => ({
    id: (
      <div className="cell-content">
        <span className="cell-value">{session.id}</span>
      </div>
    ),
    author: (
      <div className="cell-content">
        <span className="cell-value emphasized">{session.author}</span>
      </div>
    ),
    call_type: (
      <div className="cell-content">
        <span>
          {session.call_type && session.call_type.map((type, i) => (
            <span key={i} className="app-badge mr-2">
              {type}
            </span>
          ))}
        </span>
      </div>
    ),
    content: (
      <div className="cell-content">
        <Link className='link_btn'
          key="view-btn"
          onClick={() => handleContentClick(session.id)}
          title="View content details"
        >
          <span className="btn-text">View</span>
        </Link>
      </div>
    ),
    timestamp: (
      <div className="cell-content">
        <span className="cell-value muted">
          {new Date(session.timestamp).toLocaleString()}
        </span>
      </div>
    ),
  })) : [];

  const handleContentClick = async (eventId) => {
    try {
      const token = getAuthToken();
      
      const content = await GetContentDetails(token, eventId);
      setModalContent(content);
      setShowModal(true);
    } catch (error) {
      console.error("Error fetching content:", error);
    }
  };

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

  return (
    <CContainer fluid>
      <CCard className="data-card">
        <CCardHeader className="data-card-header">
          <div className="d-flex justify-content-between align-items-center">
            <div>
              <h4 className="card-title">Session Details</h4>
              <p className="card-subtitle">
                Session ID: <span className="highlight">{session_id}</span>
              </p>
            </div>
            {!loading && sessionData.length > 0 && (
              <div className="text-end d-flex gap-2">
                {appName && userIdForADK && (
                  <ADKButton
                    appName={appName}
                    userId={userIdForADK}
                    sessionId={session_id}
                    text="Open in ADK UI"
                    color="info"
                    variant="outline"
                  />
                )}
                <button
                  className="btn btn-primary"
                  onClick={handleViewAllClick}
                >
                  View All
                </button>
              </div>
            )}
          </div>
        </CCardHeader>

        <CCardBody className="data-card-body">
          {loading ? (
            <div className="loading-container">
              <CSpinner color="primary" size="lg" />
              <p className="loading-text">Loading session details...</p>
            </div>
          ) : sessionData.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">
                <i className="fas fa-inbox"></i>
              </div>
              <h5 className="empty-title">No Data Found</h5>
              <p className="empty-description">
                No session details available for this session ID.
              </p>
            </div>
          ) : (
            <div className="table-responsive-wrapper">
              <CTable hover className="clean-table">
                <CTableHead className="table-header">
                  <CTableRow>
                    {columns.map((column) => (
                      <CTableDataCell
                        key={column.key}
                        scope="col"
                        className={column.className || ''}
                      >
                        {column.label}
                      </CTableDataCell>
                    ))}
                  </CTableRow>
                </CTableHead>
                <CTableBody>
                  {items.map((item, index) => (
                    <CTableRow key={index} className="table-row">
                      {Object.values(item).map((value, idx) => (
                        <CTableDataCell key={idx}>
                          {value}
                        </CTableDataCell>
                      ))}
                    </CTableRow>
                  ))}
                </CTableBody>
              </CTable>
            </div>
          )}
        </CCardBody>
      </CCard>

      <ContentModal
        showModal={showModal}
        handleClose={() => setShowModal(false)}
        content={modalContent?.content}
      />

      <PaginationComponent
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={handlePageChange}
      />

      {showViewAllModal && (
        <ViewAllModal
          showModal={showViewAllModal}
          handleClose={() => setShowViewAllModal(false)}
          content={allContent}
        />
      )}
    </CContainer>
  );
};

export default SessionDetail;
