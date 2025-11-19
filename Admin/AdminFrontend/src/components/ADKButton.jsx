import React from 'react';
import { CButton, CTooltip } from '@coreui/react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faExternalLinkAlt, faEye } from '@fortawesome/free-solid-svg-icons';
import { openSessionInADK } from '../utils/adkIntegration';

/**
 * ADK Button Component
 * 
 * A button that opens a session in the ADK Web UI
 * Can be used in session tables, detail views, etc.
 */
const ADKButton = ({
  appName,
  userId,
  sessionId,
  variant = 'ghost',
  size = 'sm',
  text = 'Open in ADK',
  icon = faExternalLinkAlt,
  showIcon = true,
  showText = true,
  color = 'primary',
  className = ''
}) => {
  const handleClick = (e) => {
    e.stopPropagation(); 
    openSessionInADK(appName, userId, sessionId);
  };

  const buttonContent = (
    <>
      {showIcon && <FontAwesomeIcon icon={icon} className={showText ? 'me-2' : ''} />}
      {showText && <span>{text}</span>}
    </>
  );

  return (
    <CTooltip content="Open this session in ADK Web UI for advanced debugging">
      <CButton
        color={color}
        variant={variant}
        size={size}
        onClick={handleClick}
        className={`d-inline-flex align-items-center ${className}`}
        style={{
          cursor: 'pointer',
          whiteSpace: 'nowrap'
        }}
      >
        {buttonContent}
      </CButton>
    </CTooltip>
  );
};

/**
 * Compact ADK Icon Button (icon only, no text)
 */
export const ADKIconButton = (props) => {
  return (
    <ADKButton
      {...props}
      showText={false}
      icon={faEye}
      variant="ghost"
    />
  );
};

export default ADKButton;

