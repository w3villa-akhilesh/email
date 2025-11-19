import React from 'react'
import { useLocation } from 'react-router-dom'

import routes from '../routes'

import { CBreadcrumb, CBreadcrumbItem } from '@coreui/react'

import { matchPath } from 'react-router-dom'
const AppBreadcrumb = () => {
  const currentLocation = useLocation().pathname


  const getRouteName = (pathname, routes) => {
    for (let i = 0; i < routes.length; i++) {
      const match = matchPath({ path: routes[i].path, end: true }, pathname)
      if (match) return routes[i].name
    }
    return false
  }
  

  const getBreadcrumbs = (location) => {
    const breadcrumbs = []
    location.split('/').reduce((prev, curr, index, array) => {
      const currentPathname = `${prev}/${curr}`
      const routeName = getRouteName(currentPathname, routes)
      routeName &&
        breadcrumbs.push({
          pathname: currentPathname,
          name: routeName,
          active: index + 1 === array.length ? true : false,
        })
      return currentPathname
    })
    return breadcrumbs
  }

  const breadcrumbs = getBreadcrumbs(currentLocation)

  const worlog= localStorage.getItem("win_loc")

  return (
    <CBreadcrumb className="my-0">
      <CBreadcrumbItem href="/">Home</CBreadcrumbItem>
      {breadcrumbs.map((breadcrumb, index) => {
        return (
          <CBreadcrumbItem
          {...(
            breadcrumb.active
              ? { active: true }
              : { href: breadcrumb.name === 'WorkLog' ? worlog : breadcrumb.pathname }
          )}
          key={index}
        >
          {breadcrumb.name}
        </CBreadcrumbItem>
        
        )
      })}
    </CBreadcrumb>
  )
}

export default React.memo(AppBreadcrumb)



