/* prettier-ignore-start */

/* eslint-disable */

// @ts-nocheck

// noinspection JSUnusedGlobalSymbols

// This file is auto-generated by TanStack Router

// Import Routes

import { Route as rootRoute } from './routes/__root'
import { Route as F2x9b0o7kImport } from './routes/f2x9b0o7k'
import { Route as IndexImport } from './routes/index'

// Create/Update Routes

const F2x9b0o7kRoute = F2x9b0o7kImport.update({
  path: '/f2x9b0o7k',
  getParentRoute: () => rootRoute,
} as any)

const IndexRoute = IndexImport.update({
  path: '/',
  getParentRoute: () => rootRoute,
} as any)

// Populate the FileRoutesByPath interface

declare module '@tanstack/react-router' {
  interface FileRoutesByPath {
    '/': {
      id: '/'
      path: '/'
      fullPath: '/'
      preLoaderRoute: typeof IndexImport
      parentRoute: typeof rootRoute
    }
    '/f2x9b0o7k': {
      id: '/f2x9b0o7k'
      path: '/f2x9b0o7k'
      fullPath: '/f2x9b0o7k'
      preLoaderRoute: typeof F2x9b0o7kImport
      parentRoute: typeof rootRoute
    }
  }
}

// Create and export the route tree

export const routeTree = rootRoute.addChildren({ IndexRoute, F2x9b0o7kRoute })

/* prettier-ignore-end */

/* ROUTE_MANIFEST_START
{
  "routes": {
    "__root__": {
      "filePath": "__root.tsx",
      "children": [
        "/",
        "/f2x9b0o7k"
      ]
    },
    "/": {
      "filePath": "index.tsx"
    },
    "/f2x9b0o7k": {
      "filePath": "f2x9b0o7k.tsx"
    }
  }
}
ROUTE_MANIFEST_END */
