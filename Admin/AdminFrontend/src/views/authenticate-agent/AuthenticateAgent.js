import React, { useEffect, useMemo, useState } from 'react'
import {
  CButton,
  CCard,
  CCardBody,
  CCardHeader,
  CCol,
  CContainer,
  CFormInput,
  CRow,
  CInputGroupText,
  CTable,
  CTableHead,
  CTableRow,
  CTableHeaderCell,
  CTableBody,
  CTableDataCell,
  CBadge,
  CModal,
  CModalHeader,
  CModalTitle,
  CModalBody,
  CModalFooter,
  CTooltip,
  CSpinner,
} from '@coreui/react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faCopy,
  faCheck,
  faTrash,
  faSave
} from '@fortawesome/free-solid-svg-icons'
import { copyToClipboard, maskKey, formatDate } from '../../utils/credentialsHelpers'
import { generateAgentApiKey, agentKeysAPI } from '../../Api/Auth'
import Toast from '../../components/Toast'
import PaginationComponent from '../base/paginations/PaginationComponent'
import { useButtonHover } from '../../hooks/useButtonHover'

const AuthenticateAgent = () => {
  // Listing state
  const [rows, setRows] = useState([])
  const [page, setPage] = useState(1)
  const [pageSize] = useState(10)
  const [totalPages, setTotalPages] = useState(1)
  const [totalCount, setTotalCount] = useState(0)

  // Modal state
  const [showModal, setShowModal] = useState(false)
  const [modalAppName, setModalAppName] = useState('')
  const [modalGeneratedKey, setModalGeneratedKey] = useState('')
  const [loading, setLoading] = useState(false)

  const [toast, setToast] = useState({ message: '', type: 'success' })
  const isGenerateDisabled = useMemo(() => !modalAppName, [modalAppName])
  const [deleteId, setDeleteId] = useState(null)
  const [deleteKeyInfo, setDeleteKeyInfo] = useState(null)
  const [showDelete, setShowDelete] = useState(false)
  const [copiedKeyId, setCopiedKeyId] = useState(null)

  // Button styles matching CompaniesModals
  const buttonStyle = {
    borderRadius: '10px',
    fontWeight: '600',
    padding: '8px 16px',
    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
    position: 'relative',
    overflow: 'hidden'
  }

  const primaryButtonStyle = {
    ...buttonStyle,
    border: '2px solid #40518a',
    color: 'white',
    background: 'linear-gradient(135deg, #40518a 0%, #2d3a61 100%)',
    boxShadow: '0 3px 10px rgba(64, 81, 138, 0.25)'
  }

  const secondaryButtonStyle = {
    ...buttonStyle,
    border: '2px solid #6c757d',
    color: '#6c757d',
    backgroundColor: 'rgba(108, 117, 125, 0.08)',
    boxShadow: '0 3px 10px rgba(108, 117, 125, 0.15)'
  }

  const dangerButtonStyle = {
    ...buttonStyle,
    border: '2px solid #dc3545',
    color: 'white',
    background: 'linear-gradient(135deg, #dc3545 0%, #b02a37 100%)',
    boxShadow: '0 3px 10px rgba(220, 53, 69, 0.25)'
  }

  // Color configurations for hover effects
  const primaryColors = {
    normal: {
      background: 'linear-gradient(135deg, #40518a 0%, #2d3a61 100%)',
      color: 'white',
      borderColor: '#40518a',
      boxShadow: '0 3px 10px rgba(64, 81, 138, 0.25)'
    },
    hover: {
      background: 'linear-gradient(135deg, #2d3a61 0%, #1e2a45 100%)',
      color: 'white',
      borderColor: '#1e2a45',
      boxShadow: '0 6px 20px rgba(64, 81, 138, 0.4)'
    }
  }

  const secondaryColors = {
    normal: {
      background: 'rgba(108, 117, 125, 0.08)',
      color: '#6c757d',
      borderColor: '#6c757d',
      boxShadow: '0 3px 10px rgba(108, 117, 125, 0.15)'
    },
    hover: {
      background: 'linear-gradient(135deg, #6c757d 0%, #545b62 100%)',
      color: 'white',
      borderColor: '#545b62',
      boxShadow: '0 6px 20px rgba(108, 117, 125, 0.35)'
    }
  }

  const dangerColors = {
    normal: {
      background: 'linear-gradient(135deg, #dc3545 0%, #b02a37 100%)',
      color: 'white',
      borderColor: '#dc3545',
      boxShadow: '0 3px 10px rgba(220, 53, 69, 0.25)'
    },
    hover: {
      background: 'linear-gradient(135deg, #b02a37 0%, #8b1e2b 100%)',
      color: 'white',
      borderColor: '#8b1e2b',
      boxShadow: '0 6px 20px rgba(220, 53, 69, 0.4)'
    }
  }

  const primaryHover = useButtonHover(primaryColors)
  const secondaryHover = useButtonHover(secondaryColors)
  const dangerHover = useButtonHover(dangerColors)

  const fetchKeys = async () => {
    try {
      const token = localStorage.getItem('access_token')
      const res = await agentKeysAPI.getList(token, page, pageSize)
      const data = res?.data || res
      setRows(data.data || [])
      setTotalPages(data.total_pages || 1)
      setTotalCount(data.total_count || 0)
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error(err)
    }
  }

  useEffect(() => { fetchKeys() }, [page])

  const handleGenerate = async (e) => {
    e?.preventDefault?.()
    if (!modalAppName) return
    setLoading(true)
    try {
      const token = localStorage.getItem('access_token')
      if (!token) {
        setToast({ message: 'Not authenticated. Please log in.', type: 'error' })
        setLoading(false)
        return
      }
      const res = await generateAgentApiKey(token, { app_name: modalAppName })
      const key = res?.data?.api_key
      if (!key) throw new Error('No key returned')
      setModalGeneratedKey(key)
      setToast({ message: 'API key generated successfully.', type: 'success' })
      await fetchKeys()
    } catch (err) {
      setToast({ message: err.message || 'Failed to generate key', type: 'error' })
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = async (keyToCopy, keyId) => {
    if (!keyToCopy) return
    try {
      await navigator.clipboard.writeText(keyToCopy)
      setCopiedKeyId(keyId)
      setToast({ message: 'API Key copied!', type: 'success' })
      setTimeout(() => setCopiedKeyId(null), 2000)
    } catch (err) {
      console.error('Failed to copy: ', err)
      setToast({ message: 'Failed to copy to clipboard', type: 'danger' })
    }
  }

  const handleDelete = async () => {
    if (!deleteId) return
    try {
      const token = localStorage.getItem('access_token')
      await agentKeysAPI.delete(token, deleteId)
      setToast({ message: 'Key deleted successfully.', type: 'success' })
      setShowDelete(false)
      setDeleteId(null)
      await fetchKeys()
    } catch (e) {
      setToast({ message: e.message || 'Failed to delete key', type: 'error' })
    }
  }

  return (
    <CContainer fluid>
      <Toast
        message={toast.message}
        type={toast.type}
        onClose={() => setToast({ message: '', type: 'success' })}
        duration={3000}
      />
      <CCard className="data-card">
        <CCardHeader className="data-card-header">
          <div className="d-flex justify-content-between align-items-center">
            <h4 className="card-title">Agent API Keys Management</h4>
            <CButton 
              variant="outline"
              onClick={() => { setShowModal(true); setModalAppName(''); setModalGeneratedKey('') }}
              style={primaryButtonStyle}
              onMouseEnter={primaryHover.onMouseEnter}
              onMouseLeave={primaryHover.onMouseLeave}
            >
              Generate New Key
            </CButton>
          </div>
        </CCardHeader>
        <CCardBody className="data-card-body">
          <CRow>
            <CCol xs={12}>
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
                      style={{ width: '250px', minWidth: '250px' }}
                    >
                      Client App Name
                    </CTableHeaderCell>
                    <CTableHeaderCell 
                      scope="col" 
                      className="table-header-cell"
                      style={{ width: '300px', minWidth: '300px' }}
                    >
                      API Key
                    </CTableHeaderCell>
                    <CTableHeaderCell 
                      scope="col" 
                      className="table-header-cell"
                      style={{ width: '120px', minWidth: '120px', textAlign: 'center' }}
                    >
                      Status
                    </CTableHeaderCell>
                    <CTableHeaderCell 
                      scope="col" 
                      className="table-header-cell"
                      style={{ width: '180px', minWidth: '180px' }}
                    >
                      Created
                    </CTableHeaderCell>
                    <CTableHeaderCell 
                      scope="col" 
                      className="table-header-cell"
                      style={{ width: '100px', minWidth: '100px', textAlign: 'center' }}
                    >
                      Actions
                    </CTableHeaderCell>
                  </CTableRow>
                </CTableHead>
                <CTableBody>
                  {rows.map((r) => (
                    <CTableRow key={r.id} className="table-row">
                      <CTableDataCell className="table-cell">
                        <div className="cell-content">
                          <span style={{ fontSize: '14px' }}>{r.client_app_name}</span>
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
                              maxWidth: '220px'
                            }}>
                              {r.api_key ? maskKey(r.api_key) : 'N/A'}
                            </code>
                            {r.api_key && (
                              <CButton
                                variant="ghost"
                                size="sm"
                                onClick={() => handleCopy(r.api_key, r.id)}
                                title="Copy API Key"
                                style={{
                                  borderRadius: '6px',
                                  padding: '4px 6px',
                                  border: '1px solid #dee2e6',
                                  color: copiedKeyId === r.id ? '#28a745' : '#6c757d',
                                  backgroundColor: 'transparent',
                                  minWidth: 'auto',
                                  height: 'auto',
                                  flexShrink: 0
                                }}
                              >
                                <FontAwesomeIcon 
                                  icon={copiedKeyId === r.id ? faCheck : faCopy} 
                                  size="xs" 
                                />
                              </CButton>
                            )}
                          </div>
                        </div>
                      </CTableDataCell>
                      <CTableDataCell className="table-cell" style={{ textAlign: 'center' }}>
                        <div className="cell-content" style={{ justifyContent: 'center' }}>
                          <CBadge 
                            color={r.is_active ? 'success' : 'danger'}
                            className="status-badge"
                          >
                            {r.is_active ? 'Active' : 'Inactive'}
                          </CBadge>
                        </div>
                      </CTableDataCell>
                      <CTableDataCell className="table-cell">
                        <div className="cell-content">
                          <span className="text-muted" style={{ fontSize: '13px' }}>
                            {formatDate(r.created_at)}
                          </span>
                        </div>
                      </CTableDataCell>
                      <CTableDataCell className="table-cell" style={{ textAlign: 'center' }}>
                        <div className="cell-content" style={{ justifyContent: 'center' }}>
                          <CTooltip content="Delete API Key">
                            <CButton
                              variant="outline"
                              size="sm"
                              onClick={() => { 
                                setDeleteId(r.id)
                                setDeleteKeyInfo({ name: r.client_app_name, key: r.api_key })
                                setShowDelete(true) 
                              }}
                              style={{
                                borderRadius: '6px',
                                fontWeight: '400',
                                padding: '0',
                                transition: 'all 0.2s ease',
                                border: '1.5px solid',
                                borderColor: '#f53838',
                                color: '#f53838',
                                backgroundColor: '#fef2f2',
                                width: '30px',
                                height: '30px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                fontSize: '13px'
                              }}
                            >
                              <FontAwesomeIcon icon={faTrash} />
                            </CButton>
                          </CTooltip>
                        </div>
                      </CTableDataCell>
                    </CTableRow>
                  ))}
                  {rows.length === 0 && (
                    <CTableRow>
                      <CTableDataCell colSpan={6} className="text-center text-muted">No keys found</CTableDataCell>
                    </CTableRow>
                  )}
                </CTableBody>
              </CTable>
              </div>
              {totalCount > 0 && (
                <PaginationComponent
                  currentPage={page}
                  totalPages={totalPages}
                  onPageChange={setPage}
                />
              )}
            </CCol>
          </CRow>

          <CModal 
            visible={showModal} 
            onClose={() => setShowModal(false)}
            size="lg"
            backdrop="static"
          >
            <CModalHeader>
              <CModalTitle>Generate Agent API Key</CModalTitle>
            </CModalHeader>
            <CModalBody>
              <div className="mb-3">
                <label className="form-label">
                  Client App Name <span className="text-danger">*</span>
                </label>
                <CFormInput
                  placeholder="e.g. rexnord, vedica etc"
                  value={modalAppName}
                  onChange={(e) => {
                    const v = e.target.value
                    if (v.includes('|')) {
                      setToast({ message: "'|' character is not allowed in app name", type: 'warning' })
                    }
                    setModalAppName(v.replaceAll('|', '-'))
                  }}
                  required
                />
                <small className="text-muted">This is the application that will use this key to call your service.</small>
              </div>

              {modalGeneratedKey && (
                <div className="alert alert-success">
                  <label className="form-label"><strong>Generated API Key</strong></label>
                  <p className="small text-muted mb-2">
                    Please copy this key now. You won't be able to see it again.
                  </p>
                  <div className="d-flex align-items-center gap-2">
                    <code style={{ 
                      flex: 1,
                      padding: '10px 12px',
                      backgroundColor: '#fff',
                      border: '1px solid #dee2e6',
                      borderRadius: '6px',
                      fontSize: '0.85rem',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis'
                    }}>
                      {modalGeneratedKey}
                    </code>
                    <CButton
                      variant="ghost"
                      size="sm"
                      onClick={() => handleCopy(modalGeneratedKey, 'modal')}
                      title="Copy API Key"
                      style={{
                        borderRadius: '6px',
                        padding: '8px 12px',
                        border: '1px solid #dee2e6',
                        color: copiedKeyId === 'modal' ? '#28a745' : '#6c757d',
                        backgroundColor: 'white',
                        minWidth: 'auto',
                        height: 'auto',
                        flexShrink: 0
                      }}
                    >
                      <FontAwesomeIcon 
                        icon={copiedKeyId === 'modal' ? faCheck : faCopy} 
                        className="me-1"
                        size="sm"
                      />
                      {copiedKeyId === 'modal' ? 'Copied!' : 'Copy'}
                    </CButton>
                  </div>
                </div>
              )}
            </CModalBody>
            <CModalFooter>
              <CButton
                variant="outline"
                onClick={() => setShowModal(false)}
                disabled={loading}
                style={secondaryButtonStyle}
                onMouseEnter={secondaryHover.onMouseEnter}
                onMouseLeave={secondaryHover.onMouseLeave}
              >
                {modalGeneratedKey ? 'Close' : 'Cancel'}
              </CButton>
              {!modalGeneratedKey && (
                <CButton
                  variant="outline"
                  onClick={handleGenerate}
                  disabled={isGenerateDisabled || loading}
                  style={primaryButtonStyle}
                  onMouseEnter={primaryHover.onMouseEnter}
                  onMouseLeave={primaryHover.onMouseLeave}
                >
                  {loading ? (
                    <>
                      <CSpinner size="sm" className="me-2" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <FontAwesomeIcon icon={faSave} className="me-2" />
                      Generate Key
                    </>
                  )}
                </CButton>
              )}
            </CModalFooter>
          </CModal>

          <CModal 
            visible={showDelete} 
            onClose={() => setShowDelete(false)}
            size="md"
          >
            <CModalHeader>
              <CModalTitle>Delete Agent API Key</CModalTitle>
            </CModalHeader>
            <CModalBody>
              <div className="text-center">
                <div className="mb-3">
                  <i className="fas fa-exclamation-triangle text-warning" style={{ fontSize: '3rem' }}></i>
                </div>
                <h5>Are you sure?</h5>
                <p className="text-muted">
                  You are about to delete the API key for <strong>"{deleteKeyInfo?.name}"</strong>.
                  This action cannot be undone.
                </p>
                {deleteKeyInfo && (
                  <div className="alert alert-warning">
                    <small>
                      <strong>Warning:</strong> Any applications using this API key will 
                      immediately lose access to the service.
                    </small>
                  </div>
                )}
              </div>
            </CModalBody>
            <CModalFooter>
              <CButton
                variant="outline"
                onClick={() => setShowDelete(false)}
                style={secondaryButtonStyle}
                onMouseEnter={secondaryHover.onMouseEnter}
                onMouseLeave={secondaryHover.onMouseLeave}
              >
                Cancel
              </CButton>
              <CButton
                variant="outline"
                onClick={handleDelete}
                style={dangerButtonStyle}
                onMouseEnter={dangerHover.onMouseEnter}
                onMouseLeave={dangerHover.onMouseLeave}
              >
                <FontAwesomeIcon icon={faTrash} className="me-2" />
                Delete Key
              </CButton>
            </CModalFooter>
          </CModal>

        </CCardBody>
      </CCard>
    </CContainer>
  )
}

export default AuthenticateAgent
