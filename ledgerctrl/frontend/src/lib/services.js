import { callApi, M } from './api'

const cc = 'ledgerctrl.ledgerctrl.api.command_center_api'

export const services = {
  // command center
  summary: (frm, to, company, branch) =>
    callApi(M.commandCenter, { frm, to, company, branch }),
  liveRiders: () => callApi(M.liveRiders),
  activeDeliveries: () => callApi(M.activeDeliveries),
  availableRiders: () => callApi(M.availableRiders),
  dispatchBoard: () => callApi(M.dispatchBoard),

  // snapshots
  riderSnapshot: (rider) => callApi(M.riderSnapshot, { rider }),
  riderPerformance: (rider, frm, to) => callApi(M.riderPerformance, { rider, frm, to }),
  riderEarnings: (rider, frm, to) => callApi(M.riderEarnings, { rider, frm, to }),
  riderHistory: (rider, start = 0, limit = 50, status) =>
    callApi(M.riderHistory, { rider, start, limit, status }),
  riderTimeline: (rider, limit = 100) => callApi(M.riderTimeline, { rider, limit }),
  vehicleSnapshot: (vehicle) => callApi(M.vehicleSnapshot, { vehicle }),
  vehiclePerformance: (vehicle, frm, to) => callApi(M.vehiclePerformance, { vehicle, frm, to }),
  deliverySnapshot: (delivery_job) => callApi(M.deliverySnapshot, { delivery_job }),
  deliveryRoute: (delivery_job) => callApi(M.deliveryRoute, { delivery_job }),

  // dispatch actions
  assignDelivery: (delivery_job, rider, vehicle) =>
    callApi(M.assignDelivery, { delivery_job, rider, vehicle }),
  unassignDelivery: (delivery_job, reason) =>
    callApi(M.unassignDelivery, { delivery_job, reason }),

  // analytics
  deliveryAnalytics: (frm, to, filters = {}) =>
    callApi(M.deliveryAnalytics, { frm, to, ...filters }),
  riderAnalytics: (frm, to, filters = {}) =>
    callApi(M.riderAnalytics, { frm, to, ...filters }),
  fleetAnalytics: (frm, to, filters = {}) =>
    callApi(M.fleetAnalytics, { frm, to, ...filters }),
  geographicAnalytics: (frm, to, filters = {}) =>
    callApi(M.geographicAnalytics, { frm, to, ...filters }),

  // generic lists
  listDoctype: ({ doctype, filters, fields, orderBy, start = 0, limit = 50, orFilters }) =>
    callApi(M.listDoctype, {
      doctype,
      filters: filters ? JSON.stringify(filters) : undefined,
      fields,
      order_by: orderBy,
      limit_start: start,
      limit_page_length: limit,
      or_filters: orFilters ? JSON.stringify(orFilters) : undefined,
    }),
  doctypeFields: (doctype) => callApi(M.doctypeFields, { doctype }),
  filterOptions: (doctype, field) => callApi(M.filterOptions, { doctype, field }),

  // auth
  login: (usr, passwd) =>
    callApi(M.login, { usr, passwd, use_jwt: true, device_info: 'Fleet Command Center Web' }, { auth: false }),
  sessionLogin: () =>
    callApi(M.sessionLogin, { device_info: 'Fleet Command Center Web' }, { auth: false }),
  logout: (refresh_token_str) =>
    callApi(M.logout, { refresh_token_str, logout_all: false }, { auth: false }),
}
