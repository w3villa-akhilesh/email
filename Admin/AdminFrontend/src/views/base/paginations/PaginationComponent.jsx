// src/components/common/PaginationComponent.jsx
// Enhanced pagination component with improved number display and better navigation

import React from 'react';
import { CPagination, CPaginationItem } from '@coreui/react';

const PaginationComponent = ({
  currentPage = 1,
  totalPages = 0,
  onPageChange,
  maxPagesToShow = 5,
}) => {
  // Ensure valid values
  const safeTotalPages = Math.max(0, parseInt(totalPages) || 0);
  const safeCurrentPage = Math.max(1, Math.min(parseInt(currentPage) || 1, safeTotalPages));
  const getPaginationItems = () => {
    const pages = [];
    
    // If there's only 1 page, show just page 1
    if (safeTotalPages === 1) {
      return [1];
    }
    
    // If there are no pages, return empty
    if (safeTotalPages <= 0) {
      return [];
    }
    
    // If total pages is small, show all pages
    if (safeTotalPages <= maxPagesToShow) {
      for (let i = 1; i <= safeTotalPages; i++) {
        pages.push(i);
      }
      return pages;
    }
    
    // For larger page counts, use ellipsis logic
    const startPage = Math.max(1, safeCurrentPage - 2);
    const endPage = Math.min(safeTotalPages, safeCurrentPage + 2);
    
    // Always show first page
    if (startPage > 1) {
      pages.push(1);
      if (startPage > 2) {
        pages.push('...');
      }
    }
    
    // Show pages around current page
    for (let i = startPage; i <= endPage; i++) {
      pages.push(i);
    }
    
    // Always show last page
    if (endPage < safeTotalPages) {
      if (endPage < safeTotalPages - 1) {
        pages.push('...');
      }
      pages.push(safeTotalPages);
    }
    
    return pages;
  };

  // Don't render pagination if there are no pages
  if (safeTotalPages <= 0) {
    return null;
  }

  const paginationItems = getPaginationItems();
  
  return (
    <CPagination align="center" className="py-3">
      <CPaginationItem
        disabled={safeCurrentPage === 1}
        onClick={() => onPageChange && onPageChange(safeCurrentPage - 1)}
      >
        Previous
      </CPaginationItem>

      {paginationItems.map((page, index) =>
        page === '...' ? (
          <CPaginationItem key={`ellipsis-${index}`} disabled>
            <span>...</span>
          </CPaginationItem>
        ) : (
          <CPaginationItem
            key={`page-${page}`}
            active={page === safeCurrentPage}
            onClick={() => onPageChange && onPageChange(page)}
            style={{ minWidth: '40px', textAlign: 'center' }}
          >
            {page}
          </CPaginationItem>
        )
      )}

      <CPaginationItem
        disabled={safeCurrentPage === safeTotalPages}
        onClick={() => onPageChange && onPageChange(safeCurrentPage + 1)}
      >
        Next
      </CPaginationItem>
    </CPagination>
  );
};

export default PaginationComponent;
