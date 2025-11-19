import React from 'react';
import {
  CTableRow,
  CTableDataCell,
  CBadge,
  CTooltip
} from '@coreui/react';
import ActionButtons from './ActionButtons';

const AgentsRow = ({ 
  agent, 
  onAlert,
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

  // Get badge color based on agent type - using same style for all types
  const getAgentTypeBadge = (type) => {
    // All agent types use the same primary color for consistent, non-colorful UI
    return 'primary';
  };

  return (
    <CTableRow 
      className="table-row clickable-row" 
      style={{ cursor: 'pointer' }}
    >
      <CTableDataCell 
        className="table-cell"
        style={{ width: '180px', minWidth: '180px', maxWidth: '180px' }}
      >
        <div className="cell-content" style={{ 
          overflow: 'hidden', 
          textOverflow: 'ellipsis', 
          whiteSpace: 'nowrap' 
        }}>
          <TruncatedText text={agent.name} maxLength={25} className="agent-name-code" />
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
          <TruncatedText text={agent.display_name} maxLength={30} />
        </div>
      </CTableDataCell>
      
      <CTableDataCell 
        className="table-cell"
        style={{ width: '120px', minWidth: '120px', maxWidth: '120px' }}
      >
        <div className="cell-content">
          <CBadge 
            color={getAgentTypeBadge(agent.agent_type)}
            className="agent-type-badge"
          >
            {agent.agent_type === 'sub_agent' ? 'Sub Agent' : 
             agent.agent_type === 'tool' ? 'Tool' : 'Primary'}
          </CBadge>
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
          <TruncatedText text={agent.description} maxLength={40} />
        </div>
      </CTableDataCell>
      
      <CTableDataCell 
        className="table-cell"
        style={{ width: '150px', minWidth: '150px', maxWidth: '150px' }}
      >
        <div className="cell-content" style={{ 
          overflow: 'hidden', 
          textOverflow: 'ellipsis', 
          whiteSpace: 'nowrap' 
        }}>
          <TruncatedText text={agent.default_model} maxLength={20} />
        </div>
      </CTableDataCell>
      
      <CTableDataCell 
        className="table-cell"
        style={{ width: '100px', minWidth: '100px', maxWidth: '100px' }}
      >
        <div className="cell-content">
          {agent.parent_agent_id ? (
            <TruncatedText text={agent.parent_agent_id} maxLength={10} className="text-muted" />
          ) : (
            <span className="text-muted">None</span>
          )}
        </div>
      </CTableDataCell>
      
      <CTableDataCell 
        className="table-cell"
        style={{ width: '100px', minWidth: '100px', maxWidth: '100px' }}
      >
        <div className="cell-content">
          <CBadge 
            color={agent.is_active ? 'success' : 'danger'}
            className="status-badge"
          >
            {agent.is_active ? 'Active' : 'Inactive'}
          </CBadge>
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
            agent={agent}
            onEdit={onEdit}
            onDelete={onDelete}
            onToggleStatus={onToggleStatus}
          />
        </div>
      </CTableDataCell>
    </CTableRow>
  );
};

export default AgentsRow;

