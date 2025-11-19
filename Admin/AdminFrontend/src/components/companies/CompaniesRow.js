import React from 'react';
import {
  CTableRow,
  CTableDataCell,
  CBadge,
  CTooltip
} from '@coreui/react';
import ActionButtons from './ActionButtons';

const CompaniesRow = ({ 
  company, 
  onAlert,
  onRowClick,
  onEdit,
  onDelete,
  onToggleStatus
}) => {

  // Truncate text with tooltip
  const TruncatedText = ({ text, maxLength = 50, className = '' }) => {
    if (!text) return <span className="text-muted">N/A</span>;
    
    const displayText = text.toString();
    
    if (displayText.length <= maxLength) {
      return <span className={className}>{displayText}</span>;
    }

    return (
      <CTooltip content={displayText}>
        <span style={{ cursor: 'pointer' }} className={className}>
          {displayText.substring(0, maxLength)}...
        </span>
      </CTooltip>
    );
  };

  return (
    <CTableRow 
      className="table-row clickable-row" 
      onClick={() => onRowClick(company)}
      style={{ cursor: 'pointer' }}
    >
      <CTableDataCell 
        className="table-cell"
        style={{ width: '200px', minWidth: '200px', maxWidth: '200px' }}
      >
        <div className="cell-content" style={{ 
          overflow: 'hidden', 
          textOverflow: 'ellipsis', 
          whiteSpace: 'nowrap' 
        }}>
          <TruncatedText text={company.name} maxLength={30} />
        </div>
      </CTableDataCell>
      
      <CTableDataCell 
        className="table-cell"
        style={{ width: '200px', minWidth: '200px', maxWidth: '200px' }}
      >
        <div className="cell-content" style={{ 
          overflow: 'hidden', 
          textOverflow: 'ellipsis', 
          whiteSpace: 'nowrap' 
        }}>
          <TruncatedText text={company.origin} maxLength={25} className="origin-code" />
        </div>
      </CTableDataCell>
      
      <CTableDataCell 
        className="table-cell"
        style={{ width: '250px', minWidth: '250px', maxWidth: '250px' }}
      >
        <div className="cell-content" style={{ 
          overflow: 'hidden', 
          textOverflow: 'ellipsis', 
          whiteSpace: 'nowrap' 
        }}>
          <TruncatedText text={company.description} maxLength={40} />
        </div>
      </CTableDataCell>
      
      <CTableDataCell 
        className="table-cell"
        style={{ 
          width: '130px', 
          minWidth: '130px', 
          maxWidth: '130px',
          textAlign: 'center'
        }}
      >
        <div className="cell-content" style={{ 
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center'
        }}>
          {company.id ? (
            <span className="company-id-code">{company.id}</span>
          ) : (
            <span className="text-muted">N/A</span>
          )}
        </div>
      </CTableDataCell>
      
      <CTableDataCell 
        className="table-cell"
        style={{ 
          width: '130px', 
          minWidth: '130px', 
          maxWidth: '130px',
          textAlign: 'center'
        }}
      >
        <div className="cell-content" style={{ 
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center'
        }}>
          <CBadge 
            color="primary"
            className="agent-count-badge"
            style={{
              fontSize: '0.875rem',
              padding: '0.35rem 0.65rem',
              fontWeight: '600'
            }}
          >
            {company.active_agent_mappings_count || 0}
          </CBadge>
        </div>
      </CTableDataCell>
      
      <CTableDataCell 
        className="table-cell"
        style={{ width: '120px', minWidth: '120px', maxWidth: '120px' }}
      >
        <div className="cell-content">
          <CBadge 
            color={company.is_active ? 'success' : 'danger'}
            className="status-badge"
          >
            {company.is_active ? 'Active' : 'Inactive'}
          </CBadge>
        </div>
      </CTableDataCell>
      
      <CTableDataCell 
        className="table-cell"
        style={{ width: '130px', minWidth: '130px', maxWidth: '130px' }}
      >
        <div className="cell-content" style={{ 
          overflow: 'hidden', 
          textOverflow: 'ellipsis', 
          whiteSpace: 'nowrap' 
        }}>
          <TruncatedText 
            text={company.created_by || 'N/A'} 
            maxLength={15} 
            className="text-muted" 
          />
        </div>
      </CTableDataCell>
      
      <CTableDataCell 
        onClick={(e) => e.stopPropagation()} 
        style={{ 
          textAlign: 'center', 
          width: '120px',
          minWidth: '120px',
          maxWidth: '120px'
        }}
      >
        <div style={{ 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center',
          gap: '4px',
          flexWrap: 'nowrap'
        }}>
          <ActionButtons
            company={company}
            onEdit={onEdit}
            onDelete={onDelete}
            onToggleStatus={onToggleStatus}
          />
        </div>
      </CTableDataCell>
    </CTableRow>
  );
};

export default CompaniesRow;
