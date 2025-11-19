import React from 'react';
import { CModal, CModalHeader, CModalTitle, CModalBody } from '@coreui/react';

const ContentModal = ({ showModal, handleClose, content }) => {
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
        margin: 0 
      }}
    >
      <CModalHeader>
        <CModalTitle>Content Details</CModalTitle>
      </CModalHeader>
      <CModalBody 
        style={{
          flexGrow: 1, 
          overflowY: 'auto', 
          padding: '2rem'
        }}
      >
        <div className="content-part">
          {content && content.parts && content.parts.length > 0 ? (
            content.parts.map((part, index) => (
              <div key={index} className="content-part-section">
                {part.text ? (
                  <div>
                    <strong>Text Content:</strong>
                    <pre>{part.text}</pre>
                  </div>
                ) : part.function_call ? (
                  <div>
                    <strong>Function Call:</strong>
                    <pre>{JSON.stringify(part.function_call, null, 2)}</pre>
                  </div>
                ) : part.function_response ? (
                  <div>
                    <strong>Function Response:</strong>
                    <pre>{JSON.stringify(part.function_response, null, 2)}</pre>
                  </div>
                ) : (
                  <div>Unknown content type</div>
                )}
              </div>
            ))
          ) : (
            <div>No content available</div>
          )}
        </div>
      </CModalBody>
    </CModal>
  );
};

export default ContentModal;
