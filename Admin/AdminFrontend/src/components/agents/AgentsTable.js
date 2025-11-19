import React from 'react';
import {
  CTable,
  CTableHead,
  CTableBody,
  CTableRow,
  CTableHeaderCell,
  CFormSelect
} from '@coreui/react';
import AgentsRow from './AgentsRow';
import SearchQuery from '../../views/base/SearchBar/SearchQuery.jsx';

const AgentsTable = ({ 
  agentsData, 
  onAlert,
  filters,
  onFilterChange,
  onEdit,
  onDelete,
  onToggleStatus
}) => {
  const columns = [
    { key: 'name', label: 'Agent Name' },
    { key: 'display_name', label: 'Display Name' },
    { key: 'agent_type', label: 'Type' },
    { key: 'description', label: 'Description' },
    { key: 'default_model', label: 'Default Model' },
    { key: 'parent_agent_id', label: 'Parent ID' },
    { key: 'is_active', label: 'Status' },
    { key: 'actions', label: 'Actions' }
  ];

  return (
    <div 
      className="table-responsive" 
      style={{ 
        overflowX: 'auto',
        scrollbarWidth: 'none', /* Firefox */
        msOverflowStyle: 'none' /* IE and Edge */
      }}
    >
      <style dangerouslySetInnerHTML={{
        __html: `
          .table-responsive::-webkit-scrollbar {
            display: none; /* Chrome, Safari, Opera */
          }
        `
      }} />
      <CTable hover className="clean-table" style={{ minWidth: '1300px' }}>
        <CTableHead className="table-header">
          {/* Header Row - All column names in single line */}
          <CTableRow>
            <CTableHeaderCell 
              scope="col" 
              className="table-header-cell"
              style={{ width: '180px', minWidth: '180px' }}
            >
              Agent Name
            </CTableHeaderCell>
            <CTableHeaderCell 
              scope="col" 
              className="table-header-cell"
              style={{ width: '200px', minWidth: '200px' }}
            >
              Display Name
            </CTableHeaderCell>
            {columns.slice(2).map((column) => (
              <CTableHeaderCell 
                key={column.key} 
                scope="col" 
                className="table-header-cell"
                style={{ 
                  width: column.key === 'description' ? '250px' : 
                         column.key === 'default_model' ? '150px' :
                         column.key === 'agent_type' ? '120px' :
                         column.key === 'parent_agent_id' ? '100px' :
                         column.key === 'is_active' ? '100px' :
                         column.key === 'actions' ? '120px' : '150px',
                  minWidth: column.key === 'description' ? '250px' : 
                           column.key === 'default_model' ? '150px' :
                           column.key === 'agent_type' ? '120px' :
                           column.key === 'parent_agent_id' ? '100px' :
                           column.key === 'is_active' ? '100px' :
                           column.key === 'actions' ? '120px' : '150px',
                  textAlign: column.key === 'actions' ? 'center' : 'left'
                }}
              >
                {column.key === 'is_active' ? 'Status' : column.label}
              </CTableHeaderCell>
            ))}
          </CTableRow>
          {/* Filter Row - Search inputs and dropdowns */}
          <CTableRow>
            <CTableHeaderCell 
              scope="col" 
              className="table-header-cell"
              style={{ width: '180px', minWidth: '180px' }}
            >
              <SearchQuery
                placeholder="Search by name..."
                value={filters.name || ''}
                onSearchChange={(value) => onFilterChange('name', value)}
                icon={true}
              />
            </CTableHeaderCell>
            <CTableHeaderCell 
              scope="col" 
              className="table-header-cell"
              style={{ width: '200px', minWidth: '200px' }}
            >
              <SearchQuery
                placeholder="Search display name..."
                value={filters.display_name || ''}
                onSearchChange={(value) => onFilterChange('display_name', value)}
                icon={true}
              />
            </CTableHeaderCell>
            {columns.slice(2).map((column) => (
              <CTableHeaderCell 
                key={`filter-${column.key}`} 
                scope="col" 
                className="table-header-cell"
                style={{ 
                  width: column.key === 'description' ? '250px' : 
                         column.key === 'default_model' ? '150px' :
                         column.key === 'agent_type' ? '120px' :
                         column.key === 'parent_agent_id' ? '100px' :
                         column.key === 'is_active' ? '100px' :
                         column.key === 'actions' ? '120px' : '150px',
                  minWidth: column.key === 'description' ? '250px' : 
                           column.key === 'default_model' ? '150px' :
                           column.key === 'agent_type' ? '120px' :
                           column.key === 'parent_agent_id' ? '100px' :
                           column.key === 'is_active' ? '100px' :
                           column.key === 'actions' ? '120px' : '150px',
                  textAlign: column.key === 'actions' ? 'center' : 'left'
                }}
              >
                {column.key === 'agent_type' ? (
                  <CFormSelect
                    size="sm"
                    value={filters.agent_type || ''}
                    onChange={(e) => onFilterChange('agent_type', e.target.value)}
                    className="type-filter"
                  >
                    <option value="">All Types</option>
                    <option value="primary">Primary</option>
                    <option value="sub_agent">Sub Agent</option>
                    <option value="tool">Tool</option>
                  </CFormSelect>
                ) : column.key === 'is_active' ? (
                  <CFormSelect
                    size="sm"
                    value={filters.status || ''}
                    onChange={(e) => onFilterChange('status', e.target.value)}
                    className="status-filter"
                  >
                    <option value="">All Status</option>
                    <option value="true">Active</option>
                    <option value="false">Inactive</option>
                  </CFormSelect>
                ) : null}
              </CTableHeaderCell>
            ))}
          </CTableRow>
        </CTableHead>
        <CTableBody>
          {agentsData.map((agent) => (
            <AgentsRow
              key={agent.id}
              agent={agent}
              onAlert={onAlert}
              onEdit={onEdit}
              onDelete={onDelete}
              onToggleStatus={onToggleStatus}
            />
          ))}
        </CTableBody>
      </CTable>
    </div>
  );
};

export default AgentsTable;

