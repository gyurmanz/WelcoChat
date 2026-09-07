import 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    public?: boolean
    layout?: 'auth' | 'dashboard'
  }
}
