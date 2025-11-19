import React from 'react'
import CIcon from '@coreui/icons-react'
import {
  cilDrop,
  cilSpeedometer,
  cilBuilding,
  cilUser,
  cilLockLocked,
  cilShieldAlt
} from '@coreui/icons'
import {CNavItem } from '@coreui/react'

const _nav = [
  {
    component: CNavItem,
    name: 'Dashboard',
    to: '/dashboard',
    icon: <CIcon icon={cilSpeedometer} customClassName="nav-icon" />,
  },
  {
    component: CNavItem,
    name: 'Worklog',
    to: '/worklog',
    icon: <CIcon icon={cilDrop} customClassName="nav-icon" />,
  },
  {
    component: CNavItem,
    name: 'Companies',
    to: '/companies',
    icon: <CIcon icon={cilBuilding} customClassName="nav-icon" />,
  },
  {
    component: CNavItem,
    name: 'Agents',
    to: '/agents',
    icon: <CIcon icon={cilUser} customClassName="nav-icon" />,
  },
  {
    component: CNavItem,
    name: 'Authenticate Agent',
    to: '/authenticate-agent',
    icon: <CIcon icon={cilLockLocked} customClassName="nav-icon" />,
  },
  { 
    component: CNavItem,
    name: 'Network Activity',
    to: '/network-activity',
    icon: <CIcon icon={cilShieldAlt} customClassName="nav-icon" />,
  },
]

export default _nav
