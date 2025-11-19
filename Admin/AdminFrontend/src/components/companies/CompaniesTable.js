import React from 'react';
import {
  CTable,
  CTableHead,
  CTableBody,
  CTableRow,
  CTableHeaderCell,
  CFormSelect
} from '@coreui/react';
import CompaniesRow from './CompaniesRow';
import SearchQuery from '../../views/base/SearchBar/SearchQuery.jsx';

const CompaniesTable = ({ 
  companiesData, 
  onAlert,
  filters,
  onFilterChange,
  onRowClick,
  onEdit,
  onDelete,
  onToggleStatus
}) => {
  const columns = [
    { key: 'name', label: 'Company Name' },
    { key: 'origin', label: 'Origin' },
    { key: 'description', label: 'Description' },
    { key: 'id', label: 'Company ID' },
    { key: 'active_agent_mappings_count', label: 'Active Agents' },
    { key: 'is_active', label: 'Status' },
    { key: 'created_by', label: 'Created By' },
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
      <CTable hover className="clean-table" style={{ minWidth: '1420px' }}>
        <CTableHead className="table-header">
          {/* Header Row - All column names in single line */}
          <CTableRow>
            <CTableHeaderCell 
              scope="col" 
              className="table-header-cell"
              style={{ width: '200px', minWidth: '200px' }}
            >
              Company Name
            </CTableHeaderCell>
            <CTableHeaderCell 
              scope="col" 
              className="table-header-cell"
              style={{ width: '200px', minWidth: '200px' }}
            >
              Origin
            </CTableHeaderCell>
            {columns.slice(2).map((column) => (
              <CTableHeaderCell 
                key={column.key} 
                scope="col" 
                className="table-header-cell"
                style={{ 
                  width: column.key === 'description' ? '250px' : 
                         column.key === 'id' ? '130px' :
                         column.key === 'active_agent_mappings_count' ? '130px' :
                         column.key === 'is_active' ? '120px' :
                         column.key === 'created_by' ? '130px' :
                         column.key === 'actions' ? '120px' : '150px',
                  minWidth: column.key === 'description' ? '250px' : 
                           column.key === 'id' ? '130px' :
                           column.key === 'active_agent_mappings_count' ? '130px' :
                           column.key === 'is_active' ? '120px' :
                           column.key === 'created_by' ? '130px' :
                           column.key === 'actions' ? '120px' : '150px',
                  textAlign: column.key === 'actions' || column.key === 'active_agent_mappings_count' || column.key === 'id' ? 'center' : 'left'
                }}
              >
                {column.label}
              </CTableHeaderCell>
            ))}
          </CTableRow>
          {/* Filter Row - Search inputs and dropdowns */}
          <CTableRow>
            <CTableHeaderCell 
              scope="col" 
              className="table-header-cell"
              style={{ width: '200px', minWidth: '200px' }}
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
                placeholder="Search by origin..."
                value={filters.origin || ''}
                onSearchChange={(value) => onFilterChange('origin', value)}
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
                         column.key === 'id' ? '130px' :
                         column.key === 'active_agent_mappings_count' ? '130px' :
                         column.key === 'is_active' ? '120px' :
                         column.key === 'created_by' ? '130px' :
                         column.key === 'actions' ? '120px' : '150px',
                  minWidth: column.key === 'description' ? '250px' : 
                           column.key === 'id' ? '130px' :
                           column.key === 'active_agent_mappings_count' ? '130px' :
                           column.key === 'is_active' ? '120px' :
                           column.key === 'created_by' ? '130px' :
                           column.key === 'actions' ? '120px' : '150px',
                  textAlign: column.key === 'actions' || column.key === 'active_agent_mappings_count' || column.key === 'id' ? 'center' : 'left'
                }}
              >
                {column.key === 'is_active' ? (
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
          {companiesData.map((company) => (
            <CompaniesRow
              key={company.id}
              company={company}
              onAlert={onAlert}
              onRowClick={onRowClick}
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

export default CompaniesTable;
