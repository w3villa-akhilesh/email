import React, { useState } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faChevronRight,
  faChevronDown,
  faFolder,
  faFolderOpen,
  faFile,
  faCog,
  faCheckCircle,
  faTimesCircle,
  faExclamationCircle
} from '@fortawesome/free-solid-svg-icons';
import { CBadge } from '@coreui/react';
import './AgentTreeNode.scss';

const AgentTreeNode = ({ node, onNodeClick, selectedNode, level = 0 }) => {
  const [isExpanded, setIsExpanded] = useState(level === 0); // Root nodes expanded by default
  
  const hasChildren = node.children && node.children.length > 0;
  const isSelected = selectedNode?.agent_id === node.agent_id;
  
  // Determine icon based on agent type and mapping status
  const getAgentIcon = () => {
    if (hasChildren) {
      return isExpanded ? faFolderOpen : faFolder;
    }
    return faFile;
  };

  // Determine status badge
  const getStatusBadge = () => {
    if (!node.is_mapped) {
      return (
        <CBadge color="secondary" className="ms-2 agent-badge">
          Not Mapped
        </CBadge>
      );
    }
    
    if (node.mapping_info?.is_active) {
      return (
        <CBadge color="success" className="ms-2 agent-badge">
          Active
        </CBadge>
      );
    }
    
    return (
      <CBadge color="danger" className="ms-2 agent-badge">
        Inactive
      </CBadge>
    );
  };

  // Determine status icon color
  const getStatusIcon = () => {
    if (!node.is_mapped) {
      return <FontAwesomeIcon icon={faExclamationCircle} className="status-icon text-secondary" />;
    }
    
    if (node.mapping_info?.is_active) {
      return <FontAwesomeIcon icon={faCheckCircle} className="status-icon text-success" />;
    }
    
    return <FontAwesomeIcon icon={faTimesCircle} className="status-icon text-danger" />;
  };

  const handleToggle = (e) => {
    e.stopPropagation();
    setIsExpanded(!isExpanded);
  };

  const handleClick = () => {
    onNodeClick(node);
  };

  return (
    <div className="agent-tree-node">
      <div 
        className={`node-content ${isSelected ? 'selected' : ''}`}
        style={{ paddingLeft: `${level * 20 + 8}px` }}
        onClick={handleClick}
      >
        <div className="node-left">
          {hasChildren ? (
            <span className="chevron" onClick={handleToggle}>
              <FontAwesomeIcon 
                icon={isExpanded ? faChevronDown : faChevronRight} 
                className="chevron-icon"
              />
            </span>
          ) : (
            <span className="chevron-placeholder"></span>
          )}
          
          <FontAwesomeIcon 
            icon={getAgentIcon()} 
            className={`agent-icon ${hasChildren ? 'folder-icon' : 'file-icon'}`}
          />
          
          <span className="agent-name">{node.agent_display_name || node.agent_name}</span>
          
          {getStatusBadge()}
        </div>
        
        <div className="node-right">
          {getStatusIcon()}
          {node.is_mapped && (
            <FontAwesomeIcon 
              icon={faCog} 
              className="config-icon"
              title="Configure Agent"
            />
          )}
        </div>
      </div>
      
      {hasChildren && isExpanded && (
        <div className="node-children">
          {node.children.map((child, index) => (
            <AgentTreeNode
              key={child.agent_id || index}
              node={child}
              onNodeClick={onNodeClick}
              selectedNode={selectedNode}
              level={level + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default AgentTreeNode;

