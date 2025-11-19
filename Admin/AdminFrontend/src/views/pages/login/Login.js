import React from 'react';
import axios from 'axios';
import {
  CButton,
  CCard,
  CCardBody,
  CCardGroup,
  CCol,
  CContainer,
  CForm,
  CRow,
} from '@coreui/react';
import { kivo_sign_in } from '../../../Api/Auth';

const Login = () => {

  const handleKivoLogin = async () => {
    try {
      const data = await kivo_sign_in(); 
      console.log(data);
      
      if (data && data.authorization_url) {
        window.location.href = data.authorization_url;
      } else {
        console.error('Authorization URL not found in the response');
      }
    } catch (error) {
      console.error('Error fetching data:', error);
    }
  };
  
  
  return (
    <div className="bg-body-login min-vh-100 d-flex flex-row align-items-center">
      <CContainer>
        <CRow className="justify-content-center">
          <CCol md={8}>
            <CCardGroup>
              <CCard className="p-4">
                <CCardBody>
                  <CForm>
                    <h2 className="mb-3 fw-bold">Welcome Back</h2>
                    <p className="text-muted mb-4">Login to your Kivo Agent account</p>
                    <CRow>
                      <CCol xs={6}>
                        <CButton color="primary" className="px-4" onClick={handleKivoLogin}>
                          Login with Kivo
                        </CButton>
                      </CCol>
                    </CRow>
                  </CForm>
                </CCardBody>
              </CCard>
            </CCardGroup>
          </CCol>
        </CRow>
      </CContainer>
    </div>
  );
};

export default Login;
