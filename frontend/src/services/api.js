import axios from "axios";

const apiBase = import.meta.env.VITE_API_BASE_URL;

const api = axios.create({
  baseURL: apiBase,
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true
});

api.interceptors.request.use((config) => {
  const jwtToken = localStorage.getItem("jwtToken");
  if (jwtToken) {
    // Remove any existing Bearer prefix to avoid duplication
    const token = jwtToken.replace('Bearer ', '');
    config.headers.Authorization = `Bearer ${token}`;
    
    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      console.log('Request with token:', {
        headers: config.headers,
        payload: payload
      });
    } catch (error) {
      console.error('Error parsing JWT:', error);
    }
  }
  return config;
});

// api.interceptors.response.use(
//   (response) => response,
//   (error) => {
//     console.error('API Error:', {
//       status: error.response?.status,
//       url: error.config?.url,
//       method: error.config?.method,
//       headers: error.config?.headers
//     });

//     if (error.response?.status === 401) {
//       // Only redirect if not already on login page
//       if (!window.location.pathname.includes('/login')) {
//         localStorage.removeItem('jwtToken');
//         window.location.href = '/login';
//       }
//     }
//     return Promise.reject(error);
//   }
// );

export const documentService = {
  async getAllDocuments() {
    try {
      const token = localStorage.getItem("jwtToken");
      if (!token) {
        throw new Error('No authentication token');
      }

      const payload = JSON.parse(atob(token.split(".")[1]));
      console.log('Getting documents with payload:', payload);
      
      // For admin users, fetch all documents
      if (payload.global_role === 'admin') {
        const response = await api.get('/flow/documents/1'); // Use default realm for admin
        return { data: response.data };
      }

      // For regular users, fetch by realm
      const realmIds = Object.keys(payload.realm_roles || {});
      if (realmIds.length === 0) {
        console.warn('No realm IDs found in token');
        return { data: [] };
      }

      const promises = realmIds.map(realmId => 
        api.get(`/flow/documents/${realmId}`)
          .then(response => ({
            realmId,
            documents: response.data
          }))
          .catch(error => {
            console.error(`Error fetching documents for realm ${realmId}:`, error);
            return {
              realmId,
              documents: []
            };
          })
      );

      const results = await Promise.all(promises);
      const allDocuments = results.reduce((acc, result) => {
        if (result.documents) {
          acc.push(...result.documents.map(doc => ({
            ...doc,
            realmId: result.realmId
          })));
        }
        return acc;
      }, []);

      return { data: allDocuments };
    } catch (error) {
      console.error('Error fetching documents:', error);
      throw error;
    }
  },

  async createDocument(data) {
    try {
      return api.post(`/flow/documents/${data.realmId}`, {
        title: data.title,
        description: data.description
      });
    } catch (error) {
      console.error('Error creating document:', error);
      throw error;
    }
  },

  updateDocument(id, data) {
    return api.put(`/flow/documents/${id}`, data);
  },

  submitForReview(id, reviewerId) {
    return api.post(`/flow/documents/${id}/submit-for-review`, {
      reviewer_id: reviewerId,
    });
  },

  reviewDocument(id, action, rejectionReason = null) {
    return api.post(`/flow/documents/${id}/review`, {
      action,
      rejection_reason: rejectionReason,
    });
  },
};

export const notificationService = {
  getNotifications() {
    return api.get("/flow/notifications/");
  },

  markAsRead(notificationId) {
    return api.patch(`/flow/notifications/${notificationId}/mark-as-read`);
  },
};
