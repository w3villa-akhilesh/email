import React from 'react';
import {
  CButton,
  CTooltip
} from '@coreui/react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faEdit,
  faTrash,
  faToggleOn,
  faToggleOff
} from '@fortawesome/free-solid-svg-icons';

const ActionButtons = ({ 
  agent, 
  onEdit, 
  onDelete, 
  onToggleStatus
}) => {
  const handleAction = (e, action) => {
    e.preventDefault();
    e.stopPropagation();
    action();
  };

  // Square icon button styles (matching companies)
  const buttonStyle = {
    borderRadius: '6px',
    fontWeight: '400',
    padding: '0',
    transition: 'all 0.2s ease',
    border: '1.5px solid',
    width: '30px',
    height: '30px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '13px'
  };

  const activeToggleButtonStyle = {
    ...buttonStyle,
    borderColor: '#22c55e',
    color: '#22c55e',
    backgroundColor: '#f0fdf4'
  };

  const inactiveToggleButtonStyle = {
    ...buttonStyle,
    borderColor: '#9ca3af',
    color: '#9ca3af',
    backgroundColor: '#f9fafb'
  };

  const editButtonStyle = {
    ...buttonStyle,
    borderColor: '#1f94ff',
    color: '#1f94ff',
    backgroundColor: '#eff6ff'
  };

  const deleteButtonStyle = {
    ...buttonStyle,
    borderColor: '#f53838',
    color: '#f53838',
    backgroundColor: '#fef2f2'
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexWrap: 'nowrap' }}>
      <CTooltip content={agent.is_active ? "Deactivate" : "Activate"}>
        <CButton
          variant="outline"
          size="sm"
          onClick={(e) => handleAction(e, () => onToggleStatus(agent))}
          style={agent.is_active ? activeToggleButtonStyle : inactiveToggleButtonStyle}
        >
          <FontAwesomeIcon 
            icon={agent.is_active ? faToggleOn : faToggleOff} 
          />
        </CButton>
      </CTooltip>

      <CTooltip content="Edit Agent">
        <CButton
          variant="outline"
          size="sm"
          onClick={(e) => handleAction(e, () => onEdit(agent))}
          style={editButtonStyle}
        >
          <FontAwesomeIcon icon={faEdit} />
        </CButton>
      </CTooltip>

      <CTooltip content="Delete Agent">
        <CButton
          variant="outline"
          size="sm"
          onClick={(e) => handleAction(e, () => onDelete(agent))}
          style={deleteButtonStyle}
        >
          <FontAwesomeIcon icon={faTrash} />
        </CButton>
      </CTooltip>
    </div>
  );
};

export default ActionButtons;

