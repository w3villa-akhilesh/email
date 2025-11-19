import React from 'react';
import {
  CButton,
  CButtonGroup,
  CTooltip
} from '@coreui/react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faEdit,
  faTrash,
  faToggleOn,
  faToggleOff
} from '@fortawesome/free-solid-svg-icons';

const LLMCredentialActionButtons = ({ 
  credential, 
  onEdit, 
  onDelete, 
  onToggleStatus,
  onToggleCrmFlow
}) => {
  const handleAction = (e, action) => {
    e.preventDefault();
    e.stopPropagation();
    action();
  };

  // Square icon button styles (matching image)
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

  const editButtonStyle = {
    ...buttonStyle,
    borderColor: '#1f94ff',
    color: '#1f94ff',
    backgroundColor: '#eff6ff'
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

  const crmActiveButtonStyle = {
    ...buttonStyle,
    borderColor: '#3b82f6',
    color: '#3b82f6',
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
      <CTooltip content={credential.is_active ? "Deactivate Status" : "Activate Status"}>
        <CButton
          variant="outline"
          size="sm"
          onClick={(e) => handleAction(e, () => onToggleStatus(credential))}
          style={credential.is_active ? activeToggleButtonStyle : inactiveToggleButtonStyle}
        >
          <FontAwesomeIcon 
            icon={credential.is_active ? faToggleOn : faToggleOff} 
          />
        </CButton>
      </CTooltip>

      <CTooltip content={credential.is_crm_flow_active ? "Disable CRM Flow" : "Enable CRM Flow"}>
        <CButton
          variant="outline"
          size="sm"
          onClick={(e) => handleAction(e, () => onToggleCrmFlow(credential))}
          style={credential.is_crm_flow_active ? crmActiveButtonStyle : inactiveToggleButtonStyle}
        >
          <FontAwesomeIcon 
            icon={credential.is_crm_flow_active ? faToggleOn : faToggleOff} 
          />
        </CButton>
      </CTooltip>

      <CTooltip content="Edit Credential">
        <CButton
          variant="outline"
          size="sm"
          onClick={(e) => handleAction(e, () => onEdit(credential))}
          style={editButtonStyle}
        >
          <FontAwesomeIcon icon={faEdit} />
        </CButton>
      </CTooltip>

      <CTooltip content="Delete Credential">
        <CButton
          variant="outline"
          size="sm"
          onClick={(e) => handleAction(e, () => onDelete(credential))}
          style={deleteButtonStyle}
        >
          <FontAwesomeIcon icon={faTrash} />
        </CButton>
      </CTooltip>
    </div>
  );
};

export default LLMCredentialActionButtons;

