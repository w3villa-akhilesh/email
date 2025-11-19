import React, { useState, useRef } from 'react';
import { CFormInput, CButton } from '@coreui/react';
import { faTimes, faSearch } from '@fortawesome/free-solid-svg-icons';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';

function SearchQuery({ onSearchChange, placeholder, value = '', icon }) {
  const [searchTerm, setSearchTerm] = useState(value);
  const inputRef = useRef(null);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      onSearchChange(searchTerm.trim());
    }
  };

  const handleClear = () => {
    setSearchTerm('');
    onSearchChange('');
    inputRef.current.focus();
  };

  const handleSearchClick = () => {
    onSearchChange(searchTerm.trim());
  };

  return (
    <div className="search-query-container d-flex align-items-center">
      <div className="position-relative">
        <CFormInput
          ref={inputRef}
          type="text"
          size="sm"
          placeholder={placeholder}
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          onKeyDown={handleKeyDown}
        />

        {searchTerm && (
          <CButton
            color="link"
            className="position-absolute end-0 top-50 translate-middle-y p-0 me-2"
            onClick={handleClear}
            aria-label="Clear search"
          >
            <FontAwesomeIcon icon={faTimes} />
          </CButton>
        )}
      </div>

      {icon && (
        <CButton
          color="primary"
          size="sm"
          className="search-button"
          onClick={handleSearchClick}
          disabled={!searchTerm.trim()}
        >
          <FontAwesomeIcon icon={faSearch} />
        </CButton>
      )}
    </div>
  );
}

export default SearchQuery;
