import React, { useState } from 'react';
import {
  CFormCheck,
  CCollapse,
  CTooltip
} from '@coreui/react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faPlus,
  faMinus,
  faWrench,
  faRobot
} from '@fortawesome/free-solid-svg-icons';
import './AgentMappingList.scss';

const AgentMappingList = ({ agents, onConfigure, level = 0, expandedAgents, setExpandedAgents }) => {
  // Use local state only if not provided from parent
  const [localExpandedAgents, setLocalExpandedAgents] = useState({});
  const currentExpandedAgents = expandedAgents || localExpandedAgents;
  const currentSetExpandedAgents = setExpandedAgents || setLocalExpandedAgents;

  const toggleExpand = (agentId) => {
    currentSetExpandedAgents(prev => ({
      ...prev,
      [agentId]: !prev[agentId]
    }));
  };

  const expandAll = (agent) => {
    const getAllDescendantsByLevel = (agent, currentLevel = 0) => {
      let levelMap = {};
      
      if (agent.children && agent.children.length > 0) {
        // Add current agent to its level
        if (!levelMap[currentLevel]) levelMap[currentLevel] = [];
        levelMap[currentLevel].push(agent.agent_id);
        
        // Recursively get children by level
        agent.children.forEach(child => {
          const childLevels = getAllDescendantsByLevel(child, currentLevel + 1);
          Object.keys(childLevels).forEach(level => {
            if (!levelMap[level]) levelMap[level] = [];
            levelMap[level] = levelMap[level].concat(childLevels[level]);
          });
        });
      }
      return levelMap;
    };

    const levelMap = getAllDescendantsByLevel(agent);
    const isRootExpanded = currentExpandedAgents[agent.agent_id];
    
    if (isRootExpanded) {
      // Collapse all at once
      const allIds = Object.values(levelMap).flat();
      currentSetExpandedAgents(prev => {
        const newState = { ...prev };
        allIds.forEach(id => {
          newState[id] = false;
        });
        return newState;
      });
    } else {
      // Expand level by level with cascading animation
      const levels = Object.keys(levelMap).sort((a, b) => parseInt(a) - parseInt(b));
      
      levels.forEach((level, index) => {
        setTimeout(() => {
          currentSetExpandedAgents(prev => {
            const newState = { ...prev };
            levelMap[level].forEach(id => {
              newState[id] = true;
            });
            return newState;
          });
        }, index * 150); // 150ms delay between each level
      });
    }
  };

  // Helper function to determine if agent is a tool
  const isTool = (agent) => {
    return agent.agent_type && agent.agent_type.toLowerCase() === 'tool';
  };

  // Get appropriate icon for agent/tool
  const getAgentIcon = (agent) => {
    return isTool(agent) ? faWrench : faRobot;
  };

  const renderAgent = (agent) => {
    const hasChildren = agent.children && agent.children.length > 0;
    const isExpanded = currentExpandedAgents[agent.agent_id];
    const indent = level * 35;
    const isRootAgent = level === 0;

    return (
      <div key={agent.agent_id} className={`agent-item-wrapper ${isRootAgent ? 'root-agent-group' : ''}`}>
        <div 
          className={`agent-item ${isRootAgent ? 'root-agent-item' : 'child-agent-item'}`}
        >
          <div className="d-flex align-items-center">
            {/* Tree Lines and Indentation */}
            <div style={{ width: `${indent}px`, position: 'relative', flexShrink: 0 }}>
              {level > 0 && (
                <>
                  {/* Vertical dashed line from parent */}
                  <div
                    className="tree-connector vertical"
                    style={{
                      left: `${indent - 22}px`,
                      top: '-12px',
                      bottom: '50%'
                    }}
                  />
                  {/* Horizontal dashed line to item */}
                  <div
                    className="tree-connector horizontal"
                    style={{
                      left: `${indent - 22}px`,
                      top: '50%',
                      width: '18px'
                    }}
                  />
                </>
              )}
            </div>

            {/* Expand/Collapse Icon */}
            <div style={{ width: '24px', marginRight: '10px', flexShrink: 0 }}>
              {hasChildren && (
                <span
                  onClick={() => toggleExpand(agent.agent_id)}
                  className="expand-toggle"
                >
                  <FontAwesomeIcon
                    icon={isExpanded ? faMinus : faPlus}
                  />
                </span>
              )}
            </div>

            {/* Checkbox */}
            <div style={{ marginRight: '12px', flexShrink: 0 }}>
              <CFormCheck
                id={`agent-${agent.agent_id}`}
                checked={agent.is_mapped && agent.mapping_info?.is_active}
                onChange={() => onConfigure(agent)}
              />
            </div>

            {/* Agent Name */}
            <div 
              style={{ 
                flex: 1,
                cursor: hasChildren ? 'pointer' : 'default',
                padding: '4px 0'
              }}
              onClick={() => {
                if (hasChildren && isRootAgent) {
                  expandAll(agent);
                } else if (hasChildren) {
                  toggleExpand(agent.agent_id);
                }
              }}
            >
              <span
                style={{ 
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}
              >
                {agent.agent_description ? (
                  <CTooltip content={agent.agent_description}>
                    <span
                      style={{ 
                        color: (agent.is_mapped && agent.mapping_info?.is_active) ? '#212529' : '#6c757d',
                        fontSize: isRootAgent ? '15px' : '14px',
                        fontWeight: isRootAgent ? '600' : '500',
                        userSelect: 'none',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px'
                      }}
                    >
                      <FontAwesomeIcon 
                        icon={getAgentIcon(agent)} 
                        style={{ 
                          fontSize: isRootAgent ? '14px' : '12px',
                          color: isTool(agent) ? '#6c757d' : '#40518a'
                        }} 
                      />
                      {agent.agent_display_name || agent.agent_name}
                    </span>
                  </CTooltip>
                ) : (
                  <span
                    style={{ 
                      color: (agent.is_mapped && agent.mapping_info?.is_active) ? '#212529' : '#6c757d',
                      fontSize: isRootAgent ? '15px' : '14px',
                      fontWeight: isRootAgent ? '600' : '500',
                      userSelect: 'none',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px'
                    }}
                  >
                    <FontAwesomeIcon 
                      icon={getAgentIcon(agent)} 
                      style={{ 
                        fontSize: isRootAgent ? '14px' : '12px',
                        color: isTool(agent) ? '#6c757d' : '#40518a'
                      }} 
                    />
                    {agent.agent_display_name || agent.agent_name}
                  </span>
                )}
              </span>
            </div>
          </div>
        </div>

        {/* Render Children */}
        {hasChildren && (
          <CCollapse visible={isExpanded}>
            <div style={{ marginTop: '2px' }}>
              <AgentMappingList
                agents={agent.children}
                onConfigure={onConfigure}
                level={level + 1}
                expandedAgents={currentExpandedAgents}
                setExpandedAgents={currentSetExpandedAgents}
              />
            </div>
          </CCollapse>
        )}
      </div>
    );
  };

  return (
    <div className="agent-mapping-list">
      {agents && agents.map(agent => renderAgent(agent))}
    </div>
  );
};

export default AgentMappingList;

