import React, { useState, useEffect, useRef } from 'react';
import {
  CRow,
  CCol,
  CTable,
  CTableHead,
  CTableBody,
  CTableRow,
  CTableHeaderCell,
  CTableDataCell,
  CSpinner,
  CContainer,
  CCard,
  CCardBody,
  CCardHeader,
  CFormInput,
  CFormSelect,
  CButton
} from '@coreui/react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faCalendarDays, faFilter, faTimes } from "@fortawesome/free-solid-svg-icons";
import 'react-date-range/dist/styles.css';
import 'react-date-range/dist/theme/default.css';
import AgentWeekChart from '../charts/BarChart';
import { LogChartStatic } from '../chartDashboard/LogChart';

const Dashboard = () => {
  const token = localStorage.getItem('access_token');


  return (
    <CContainer fluid>
      <CCard className="data-card">
        <CCardHeader className="data-card-header">
          <CRow className="align-items-center">
            <CCol xs={12} md={6} className="mb-3 mb-md-0">
              <h4 className="card-title mb-0">Analytics Overview</h4>
            </CCol>
            <CCol xs={12} md={6}>
              <div className="d-flex flex-column flex-sm-row align-items-stretch align-items-sm-center justify-content-md-end gap-2">
                {/* Future: Add any dashboard controls here if needed */}
              </div>
            </CCol>
          </CRow>
        </CCardHeader>

        <CCardBody className="data-card-body">
          <div className="chart-container">
            <LogChartStatic />
          </div>
        </CCardBody>
      </CCard>
    </CContainer>
  );
};

export default Dashboard;