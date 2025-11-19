import { useState, useEffect } from 'react';
import { companiesAPI } from '../Api/Auth';

export const useCompanies = (token, initialPage = 1) => {
  const [companiesData, setCompaniesData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(initialPage);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [pageSize] = useState(10);

  // Fetch companies data
  const fetchCompanies = async (nameFilter = null, originFilter = null, statusFilter = null, page = currentPage) => {
    setLoading(true);
    try {
      const response = await companiesAPI.getList(
        token,
        nameFilter,
        originFilter,
        statusFilter,
        page,
        pageSize
      );

      if (response.data) {
        setCompaniesData(response.data);
        if (response.pagination) {
          setTotalCount(response.pagination.total_items || 0);
          setTotalPages(response.pagination.total_pages || 1);
        } else {
          // Fallback for old response format
          setTotalCount(response.total || response.data.length);
          setTotalPages(Math.ceil((response.total || response.data.length) / pageSize));
        }
      } else {
        setCompaniesData([]);
        setTotalCount(0);
        setTotalPages(1);
      }
    } catch (error) {
      console.error('Error fetching companies:', error);
      setCompaniesData([]);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  // Create company
  const createCompany = async (formData) => {
    try {
      const response = await companiesAPI.create(token, formData);
      
      // Add new company to local state instead of refetching all data
      if (response.data) {
        setCompaniesData(prevData => [response.data, ...prevData]);
        setTotalCount(prev => prev + 1);
      }
      
      return { success: true };
    } catch (error) {
      console.error('Error creating company:', error);
      throw error;
    }
  };

  // Update company
  const updateCompany = async (id, formData) => {
    try {
      const response = await companiesAPI.update(token, id, formData);
      
      // Update local state instead of refetching all data
      setCompaniesData(prevData => 
        prevData.map(company => 
          company.id === id 
            ? { ...company, ...formData, ...response.data }
            : company
        )
      );
      
      return { success: true };
    } catch (error) {
      console.error('Error updating company:', error);
      throw error;
    }
  };

  // Delete company
  const deleteCompany = async (id) => {
    try {
      await companiesAPI.delete(token, id);
      
      // Remove company from local state instead of refetching all data
      setCompaniesData(prevData => prevData.filter(company => company.id !== id));
      setTotalCount(prev => prev - 1);
      
      return { success: true };
    } catch (error) {
      console.error('Error deleting company:', error);
      throw error;
    }
  };

  // Toggle status
  const toggleCompanyStatus = async (id) => {
    try {
      const response = await companiesAPI.toggleStatus(token, id);
      
      // Update local state instead of refetching all data
      setCompaniesData(prevData => 
        prevData.map(company => 
          company.id === id 
            ? { ...company, is_active: response.data.is_active }
            : company
        )
      );
      
      return response;
    } catch (error) {
      console.error('Error toggling status:', error);
      throw error;
    }
  };

  // Get company by ID
  const getCompanyById = async (id) => {
    try {
      const response = await companiesAPI.getById(token, id);
      return response.data;
    } catch (error) {
      console.error('Error fetching company:', error);
      throw error;
    }
  };

  return {
    companiesData,
    loading,
    currentPage,
    setCurrentPage,
    totalPages,
    totalCount,
    pageSize,
    fetchCompanies,
    createCompany,
    updateCompany,
    deleteCompany,
    toggleCompanyStatus,
    getCompanyById
  };
};
