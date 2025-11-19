import React from 'react';
import { CModal, CModalHeader, CModalTitle, CModalBody, CModalFooter } from '@coreui/react';

const ViewAllModal = ({ showModal, handleClose, content }) => {
  
  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleString();  // Convert to human-readable format
  };

  return (
    <CModal
      visible={showModal}
      onClose={handleClose}
      size="xl"
      scrollable
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        margin: 0,
      }}
    >
      <CModalHeader>
        <CModalTitle>View All Content Details</CModalTitle>
      </CModalHeader>
      <CModalBody
        style={{
          flexGrow: 1,
          overflowY: 'auto',
          padding: '2rem',
        }}
      >
        <div className="content-part">
          {content && content.length > 0 ? (
            content.map((part, index) => (
              <div key={index} className="content-part-section" style={{ marginBottom: '1rem' }}>
                <h4>Content Block {index + 1}</h4> {/* Indexing the content */}
                
                <div style={{ marginBottom: '0.5rem' }}>
                  <strong>Author:</strong> <span className="author-name">{part.author || 'Unknown'}</span>
                </div>
                <div style={{ marginBottom: '0.5rem' }}>
                  <strong>Timestamp:</strong> <span>{formatTimestamp(part.timestamp)}</span>
                </div>
                <div style={{ marginBottom: '0.5rem' }}>
                  <strong>Content ID:</strong> <span>{part.id}</span>
                </div>

                {part?.content?.parts?.map((subPart, subIndex) => (
                  <div key={subIndex} style={{ marginBottom: '0.5rem' }}>
                    {subPart?.text ? (
                      <div>
                        <strong>Text Content ({subIndex + 1}):</strong>
                        <pre>{subPart.text}</pre> {/* Display text content */}
                      </div>
                    ) : subPart.function_call ? (
                      <div>
                        <strong>Function Call ({subIndex + 1}):</strong>
                        <pre>{JSON.stringify(subPart.function_call, null, 2)}</pre> {/* Format JSON */}
                      </div>
                    ) : subPart.function_response ? (
                      <div>
                        <strong>Function Response ({subIndex + 1}):</strong>
                        <pre>{JSON.stringify(subPart.function_response, null, 2)}</pre> {/* Format JSON */}
                      </div>
                    ) : (
                      <div className="unknown-content">
                        <strong>Unknown Content ({subIndex + 1}):</strong>
                        <pre>{JSON.stringify(subPart, null, 2)}</pre> {/* Format JSON */}
                        <p style={{ color: 'red' }}>This content type could not be identified. Please check the data format.</p>
                      </div>
                    )}
                    <hr style={{ margin: '1rem 0', borderTop: '1px solid grey' }} />
                  </div>
                ))}
              </div>
            ))
          ) : (
            <div>No content available</div>
          )}
        </div>
      </CModalBody>
      <CModalFooter>
        {/* <CButton color="secondary" onClick={handleClose}>Close</CButton> */}
      </CModalFooter>
    </CModal>
  );
};

export default ViewAllModal;
