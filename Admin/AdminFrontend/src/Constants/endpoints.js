// Get base URL from environment variable
const baseUrl = import.meta.env.VITE_BACKEND_URL;
const apiUrl = `${baseUrl}`;

const endpoints = {
  available_app_names:()=> `${apiUrl}/available_app_names`,
  session_detail: (session_id, page) => `${apiUrl}/events/${session_id}?page=${page}&page_size=15`,
  session_counts: (page, pageSize, query, date_from, date_to, appName,session_id,mode) => `${apiUrl}/session_counts?page=${page}&page_size=${pageSize}&email=${query}&date_from=${date_from}&date_to=${date_to}&app_name=${appName}&session_id=${session_id}&mode=${mode || ""}`,
  content_detail: (eventid) => `${apiUrl}/event/content?event_id=${eventid}`,
  content_session_detail: (session_id) => `${apiUrl}/event/content?session_id=${session_id}`,
  kivo_sign_in: () => `${baseUrl}/kivo-sign-in`,
  User_detail: (token) => `${baseUrl}/user?access_token=${token}`,
  Chartlog: (end_date, start_date, app_name) => `${baseUrl}/dashboard_data?app_name=${app_name}&start_date=${start_date}&end_date=${end_date}`,
  
  // Agent API Keys endpoints
  agentKeys: {
    create: () => `${apiUrl}/agent-keys`,
    list: (page = 1, page_size = 10, app_name = '', status = '') => {
      let url = `${apiUrl}/agent-keys?page=${page}&page_size=${page_size}`;
      if (app_name) url += `&app_name=${encodeURIComponent(app_name)}`;
      if (status) url += `&status=${encodeURIComponent(status)}`;
      return url;
    },
    delete: (id) => `${apiUrl}/agent-keys/${id}`,
  },
  

  // LLM Credentials endpoints (new API)
  llm_credential: {
    list: (company_id, provider, is_active, page = 1, page_size = 10) => {
      let url = `${apiUrl}/llm-credential`;
      const params = new URLSearchParams();
      if (company_id !== undefined && company_id !== null && company_id !== '') {
        params.append('company_id', company_id);
      }
      if (provider) params.append('provider', provider);
      if (is_active !== undefined && is_active !== null && is_active !== '') {
        params.append('is_active', is_active);
      }
      params.append('page', page);
      params.append('page_size', page_size);
      return params.toString() ? `${url}?${params.toString()}` : url;
    },
    getById: (id) => `${apiUrl}/llm-credential/${id}`,
    create: () => `${apiUrl}/llm-credential`,
    update: (id) => `${apiUrl}/llm-credential/${id}`,
    delete: (id) => `${apiUrl}/llm-credential/${id}`,
    toggleStatus: (id) => `${apiUrl}/llm-credential/${id}/toggle-status`,
    toggleCrmFlow: (id) => `${apiUrl}/llm-credential/${id}/toggle-crm-flow`,
  },

  // Companies endpoints
  companies: {
    list: (name, origin, is_active, page = 1, page_size = 10) => {
      let url = `${apiUrl}/companies`;
      const params = new URLSearchParams();
      if (name) params.append('name', name);
      if (origin) params.append('origin', origin);
      if (is_active !== undefined && is_active !== null && is_active !== '') {
        params.append('is_active', is_active);
      }
      params.append('page', page);
      params.append('page_size', page_size);
      return params.toString() ? `${url}?${params.toString()}` : url;
    },
    getById: (id) => `${apiUrl}/companies/${id}`,
    create: () => `${apiUrl}/companies`,
    update: (id) => `${apiUrl}/companies/${id}`,
    delete: (id) => `${apiUrl}/companies/${id}`,
    toggleStatus: (id) => `${apiUrl}/companies/${id}/toggle-status`,
  },

  // Agents endpoints
  agents: {
    list: (name, display_name, agent_type, parent_agent_id, is_active) => {
      let url = `${apiUrl}/agents`;
      const params = new URLSearchParams();
      if (name) params.append('name', name);
      if (display_name) params.append('display_name', display_name);
      if (agent_type) params.append('agent_type', agent_type);
      if (parent_agent_id !== undefined && parent_agent_id !== null && parent_agent_id !== '') {
        params.append('parent_agent_id', parent_agent_id);
      }
      if (is_active !== undefined && is_active !== null && is_active !== '') {
        params.append('is_active', is_active);
      }
      return params.toString() ? `${url}?${params.toString()}` : url;
    },
    getById: (id) => `${apiUrl}/agents/${id}`,
    create: () => `${apiUrl}/agents`,
    update: (id) => `${apiUrl}/agents/${id}`,
    delete: (id) => `${apiUrl}/agents/${id}`,
    toggleStatus: (id) => `${apiUrl}/agents/${id}/toggle-status`,
    hierarchy: () => `${apiUrl}/agents/hierarchy/tree`,
    typesSummary: () => `${apiUrl}/agents/types/summary`,
  },

  // Agent Mappings endpoints
  agentMappings: {
    list: (company_id, agent_id, is_active) => {
      let url = `${apiUrl}/agent-mappings`;
      const params = new URLSearchParams();
      if (company_id !== undefined && company_id !== null && company_id !== '') {
        params.append('company_id', company_id);
      }
      if (agent_id !== undefined && agent_id !== null && agent_id !== '') {
        params.append('agent_id', agent_id);
      }
      if (is_active !== undefined && is_active !== null && is_active !== '') {
        params.append('is_active', is_active);
      }
      return params.toString() ? `${url}?${params.toString()}` : url;
    },
    getById: (id) => `${apiUrl}/agent-mappings/${id}`,
    getCompanyHierarchy: (company_id) => `${apiUrl}/agent-mappings/company/${company_id}/hierarchy`,
    create: () => `${apiUrl}/agent-mappings`,
    update: (id) => `${apiUrl}/agent-mappings/${id}`,
    delete: (id) => `${apiUrl}/agent-mappings/${id}`,
    toggleStatus: (id) => `${apiUrl}/agent-mappings/${id}/toggle-status`,
    bulkCreate: () => `${apiUrl}/agent-mappings/bulk-create`,
  },
  
  // Network Activity endpoints
  network_activity: {
    list: (page, page_size, filters = {}) => {
      let url = `${apiUrl}/network-activity-logs?page=${page}&page_size=${page_size}`;
      if (filters.endpoint) url += `&endpoint=${encodeURIComponent(filters.endpoint)}`;
      if (filters.method) url += `&method=${filters.method}`;
      if (filters.ip_address) url += `&ip_address=${encodeURIComponent(filters.ip_address)}`;
      if (filters.device_type) url += `&device_type=${filters.device_type}`;
      if (filters.user_id) url += `&user_id=${encodeURIComponent(filters.user_id)}`;
      if (filters.company_id) url += `&company_id=${filters.company_id}`;
      if (filters.date_from) url += `&date_from=${filters.date_from}`;
      if (filters.date_to) url += `&date_to=${filters.date_to}`;
      return url;
    },
    stats: () => `${apiUrl}/network-activity-stats`,
  },

};

export default endpoints;
