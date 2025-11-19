import sendRequest from "./SendRequest";
import endpoints from "../Constants/endpoints";
import { format } from 'date-fns';



export const GetSessionDetails = (token, sessionId, page) => {
  const url = endpoints.session_detail(sessionId, page);
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  };

  return sendRequest({
    url,
    headers,
    method: 'GET',
  });
};

export const GetSessionCounts = (token, currentPage, pageSize, query, startDate, endDate, appName,session_id,mode) => {
  const formattedStartDate = format(startDate, "yyyy-MM-dd");
  const formattedEndDate = format(endDate, "yyyy-MM-dd");
  const url = endpoints.session_counts(currentPage, pageSize, query, formattedStartDate, formattedEndDate, appName,session_id,mode);
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  };
  return sendRequest({
    url,
    headers,
    method: 'GET',
  });
};


export const GetContentDetails = (token, eventId) => {
  const url = endpoints.content_detail(eventId);
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  };

  return sendRequest({
    url,
    headers,
    method: 'GET',
  });
};


export const GetContentSessionDetails = (token, session_id) => {
  const url = endpoints.content_session_detail(session_id);
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  };

  return sendRequest({
    url,
    headers,
    method: 'GET',
  });
};

export const getUser = (token) => {
  const url = endpoints.User_detail(token);
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  };

  return sendRequest({
    url,
    headers,
    method: 'GET',
  });
};

export const kivo_sign_in = () => {
  const url = endpoints.kivo_sign_in();
  const headers = {
    'Content-Type': 'application/json',
  };

  return sendRequest({
    url,
    headers,
    method: 'GET',
  });
};

// Agent Keys API (Updated to use new routes)
export const agentKeysAPI = {
  create: (token, payload) => {
    const url = endpoints.agentKeys.create();
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };
    return sendRequest({
      url,
      headers,
      method: 'POST',
      body: payload,
    });
  },
  getList: (token, page = 1, page_size = 10, app_name = '', status = '') => {
    const url = endpoints.agentKeys.list(page, page_size, app_name, status);
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };
    return sendRequest({ url, headers, method: 'GET' });
  },
  delete: (token, id) => {
    const url = endpoints.agentKeys.delete(id);
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };
    return sendRequest({ url, headers, method: 'DELETE' });
  }
};

// Backward compatibility - deprecated, use agentKeysAPI.create instead
export const generateAgentApiKey = (token, payload) => {
  return agentKeysAPI.create(token, payload);
};

export const CharLogData = (token, payload) => {
  console.log("App Name:", payload.app_name, "Start Date:", payload.start_date, "End Date:", payload.end_date); // Correct logging

  const url = endpoints.Chartlog(payload.end_date, payload.start_date, payload.app_name);

  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  };

  return sendRequest({
    url,
    headers,
    method: 'GET',
  });
};

export const availableAppname = (token) => {
  const url = endpoints.available_app_names();
  const headers = {
    'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
  };

  return sendRequest({
    url,
    headers,
    method: 'GET',
  });
};


// Companies API
export const companiesAPI = {
  getList: (token, name = null, origin = null, is_active = null, page = 1, page_size = 10) => {
    const url = endpoints.companies.list(name, origin, is_active, page, page_size);
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };

    return sendRequest({
      url,
      headers,
      method: 'GET',
    });
  },

  getById: (token, id) => {
    const url = endpoints.companies.getById(id);
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };

    return sendRequest({
      url,
      headers,
      method: 'GET',
    });
  },

  create: (token, companyData) => {
    const url = endpoints.companies.create();
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };

    return sendRequest({
      url,
      headers,
      method: 'POST',
      body: companyData,
    });
  },

  update: (token, id, companyData) => {
    const url = endpoints.companies.update(id);
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };

    return sendRequest({
      url,
      headers,
      method: 'PUT',
      body: companyData,
    });
  },

  delete: (token, id) => {
    const url = endpoints.companies.delete(id);
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };

    return sendRequest({
      url,
      headers,
      method: 'DELETE',
    });
  },

  toggleStatus: (token, id) => {
    const url = endpoints.companies.toggleStatus(id);
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };

    return sendRequest({
      url,
      headers,
      method: 'PUT',
    });
  },
};

// LLM Credentials API (New)
export const llmCredentialAPI = {
  getList: (token, company_id = null, provider = null, is_active = null, page = 1, page_size = 10) => {
    const url = endpoints.llm_credential.list(company_id, provider, is_active, page, page_size);
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };

    return sendRequest({
      url,
      headers,
      method: 'GET',
    });
  },

  getById: (token, id) => {
    const url = endpoints.llm_credential.getById(id);
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };

    return sendRequest({
      url,
      headers,
      method: 'GET',
    });
  },

  create: (token, credentialData) => {
    const url = endpoints.llm_credential.create();
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };

    return sendRequest({
      url,
      headers,
      method: 'POST',
      body: credentialData, // Don't stringify here, SendRequest will handle it
    });
  },

  update: (token, id, credentialData) => {
    const url = endpoints.llm_credential.update(id);
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };

    return sendRequest({
      url,
      headers,
      method: 'PUT',
      body: credentialData, // Don't stringify here, SendRequest will handle it
    });
  },

  delete: (token, id) => {
    const url = endpoints.llm_credential.delete(id);
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };

    return sendRequest({
      url,
      headers,
      method: 'DELETE',
    });
  },

  toggleStatus: (token, id) => {
    const url = endpoints.llm_credential.toggleStatus(id);
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };

    return sendRequest({
      url,
      headers,
      method: 'PUT',
    });
  },

  toggleCrmFlow: (token, id) => {
    const url = endpoints.llm_credential.toggleCrmFlow(id);
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };

    return sendRequest({
      url,
      headers,
      method: 'PUT',
    });
  },
};

// Agents API
export const agentsAPI = {
  getList: (token, name = null, display_name = null, agent_type = null, parent_agent_id = null, is_active = null, page = 1, page_size = 10) => {
    const url = endpoints.agents.list(name, display_name, agent_type, parent_agent_id, is_active);
    const params = new URLSearchParams();
    params.append('page', page);
    params.append('page_size', page_size);
    const fullUrl = `${url}${url.includes('?') ? '&' : '?'}${params.toString()}`;
    
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };

    return sendRequest({
      url: fullUrl,
      headers,
      method: 'GET',
    });
  },

  getById: (token, id) => {
    const url = endpoints.agents.getById(id);
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };

    return sendRequest({
      url,
      headers,
      method: 'GET',
    });
  },

  create: (token, agentData) => {
    const url = endpoints.agents.create();
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };

    return sendRequest({
      url,
      headers,
      method: 'POST',
      body: agentData,
    });
  },

  update: (token, id, agentData) => {
    const url = endpoints.agents.update(id);
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };

    return sendRequest({
      url,
      headers,
      method: 'PUT',
      body: agentData,
    });
  },

  delete: (token, id) => {
    const url = endpoints.agents.delete(id);
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };

    return sendRequest({
      url,
      headers,
      method: 'DELETE',
    });
  },

  toggleStatus: (token, id) => {
    const url = endpoints.agents.toggleStatus(id);
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };

    return sendRequest({
      url,
      headers,
      method: 'PUT',
    });
  },
};

// Agent Mappings API
export const agentMappingsAPI = {
  getList: (token, company_id = null, agent_id = null, is_active = null) => {
    const url = endpoints.agentMappings.list(company_id, agent_id, is_active);
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };

    return sendRequest({
      url,
      headers,
      method: 'GET',
    });
  },

  getById: (token, id) => {
    const url = endpoints.agentMappings.getById(id);
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };

    return sendRequest({
      url,
      headers,
      method: 'GET',
    });
  },

  getCompanyHierarchy: (token, company_id, page = 1, page_size = 10) => {
    const url = `${endpoints.agentMappings.getCompanyHierarchy(company_id)}?page=${page}&page_size=${page_size}`;
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };

    return sendRequest({
      url,
      headers,
      method: 'GET',
    });
  },

  create: (token, mappingData) => {
    const url = endpoints.agentMappings.create();
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };

    return sendRequest({
      url,
      headers,
      method: 'POST',
      body: mappingData,
    });
  },

  update: (token, id, mappingData) => {
    const url = endpoints.agentMappings.update(id);
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };

    return sendRequest({
      url,
      headers,
      method: 'PUT',
      body: mappingData,
    });
  },

  delete: (token, id) => {
    const url = endpoints.agentMappings.delete(id);
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };

    return sendRequest({
      url,
      headers,
      method: 'DELETE',
    });
  },

  toggleStatus: (token, id) => {
    const url = endpoints.agentMappings.toggleStatus(id);
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };

    return sendRequest({
      url,
      headers,
      method: 'PUT',
    });
  },

  bulkCreate: (token, mappingsArray) => {
    const url = endpoints.agentMappings.bulkCreate();
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };

    return sendRequest({
      url,
      headers,
      method: 'POST',
      body: mappingsArray,
    });
  },
};
