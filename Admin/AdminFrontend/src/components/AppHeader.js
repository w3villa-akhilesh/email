import React, { useState, useEffect, useRef } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useSelector, useDispatch } from 'react-redux';
import {
  CContainer,
  CDropdown,
  CDropdownItem,
  CDropdownMenu,
  CDropdownToggle,
  CHeader,
  CHeaderNav,
  CHeaderToggler,
  CNavLink,
  CNavItem,
  useColorModes,
} from '@coreui/react';
import CIcon from '@coreui/icons-react';
import {
  cilBell,
  cilContrast,
  cilEnvelopeOpen,
  cilList,
  cilMenu,
  cilMoon,
  cilSun,
} from '@coreui/icons';

import { AppBreadcrumb } from './index';
import { AppHeaderDropdown } from './header/index';
import { getUser } from '../Api/Auth';

const AppHeader = () => {
  const headerRef = useRef();
  const { colorMode, setColorMode } = useColorModes('coreui-free-react-admin-template-theme');
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const sidebarShow = useSelector((state) => state.sidebarShow);

  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);


  const fetchUserDetails = async (accessToken) => {
    try {
      const response = await getUser(accessToken);
      setUser(response);
      setToken(response.data?.data?.access_token);
    } catch (error) {
      console.error('Error fetching user data:', error);
      // If user data fetch fails, we can still continue with the stored token
      // Set a default user object to prevent undefined errors
      setUser({
        data: {
          first_name: 'Admin',
          last_name: 'User',
          email: 'admin@example.com'
        }
      });
    }
  };

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const accessTokenFromUrl = urlParams.get('access_token');
    
    if (accessTokenFromUrl) {
      localStorage.setItem('access_token', accessTokenFromUrl);
      navigate("/dashboard");
    }
    
    const storedToken = localStorage.getItem('access_token') || localStorage.getItem('access_token');
    if (storedToken) {
      fetchUserDetails(storedToken);
    }
  }, []);

  useEffect(() => {
    if (token) {
      localStorage.setItem('access_token', token);
    }
  }, [token]);


  return (
    <CHeader position="sticky" className="mb-4 p-0" ref={headerRef}>
      <CContainer className="border-bottom px-4" fluid>
        <CHeaderToggler
          onClick={() => dispatch({ type: 'set', sidebarShow: !sidebarShow })}
          style={{ marginInlineStart: '-14px' }}
        >
          <CIcon icon={cilMenu} size="lg" />
        </CHeaderToggler>
        <CHeaderNav className="d-none d-md-flex">
          <CNavItem>
            <CNavLink to="/dashboard" as={NavLink}>
              Agent Dashboard
            </CNavLink>
          </CNavItem>
        </CHeaderNav>
        <CHeaderNav className="ms-auto"></CHeaderNav>
        <CHeaderNav>
          <li className="nav-item py-1">
            <div className="vr h-100 mx-2 text-body text-opacity-75"></div>
          </li>
          <CDropdown variant="nav-item" placement="bottom-end">
            <CDropdownToggle caret={false}>
              {colorMode === 'dark' ? (
                <CIcon icon={cilMoon} size="lg" />
              ) : colorMode === 'auto' ? (
                <CIcon icon={cilContrast} size="lg" />
              ) : (
                <CIcon icon={cilSun} size="lg" />
              )}
            </CDropdownToggle>
            <CDropdownMenu>
              <CDropdownItem
                active={colorMode === 'light'}
                className="d-flex align-items-center"
                as="button"
                type="button"
                onClick={() => setColorMode('light')}
              >
                <CIcon className="me-2" icon={cilSun} size="lg" /> Light
              </CDropdownItem>
              <CDropdownItem
                active={colorMode === 'dark'}
                className="d-flex align-items-center"
                as="button"
                type="button"
                onClick={() => setColorMode('dark')}
              >
                <CIcon className="me-2" icon={cilMoon} size="lg" /> Dark
              </CDropdownItem>
              <CDropdownItem
                active={colorMode === 'auto'}
                className="d-flex align-items-center"
                as="button"
                type="button"
                onClick={() => setColorMode('auto')}
              >
                <CIcon className="me-2" icon={cilContrast} size="lg" /> Auto
              </CDropdownItem>
            </CDropdownMenu>
          </CDropdown>
          <li className="nav-item py-1">
            <div className="vr h-100 mx-2 text-body text-opacity-75"></div>
          </li>
          <AppHeaderDropdown user={user?.data}/>
        </CHeaderNav>
      </CContainer>
      <CContainer className="px-4" fluid>
        <AppBreadcrumb />
      </CContainer>
    </CHeader>
  );
};

export default AppHeader;
