import axios from "axios";

const apiBase = import.meta.env.VITE_API_BASE_URL;

const api = axios.create({
  baseURL: apiBase,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  const jwtToken = localStorage.getItem("jwtToken");
  if (jwtToken) {
    config.headers["Authorization"] = `Bearer ${jwtToken}`;
    
    try {
      const payload = JSON.parse(atob(jwtToken.split(".")[1]));
      console.log('Token payload:', payload);
      config.realmRoles = payload.realm_roles;
    } catch (error) {
      console.error('Error parsing JWT:', error);
      return Promise.reject(error);
    }
  }
  return config;
});

export const documentService = {
  async getAllDocuments() {
    try {
      const token = localStorage.getItem("jwtToken");
      const payload = JSON.parse(atob(token.split(".")[1]));
      const realmIds = Object.keys(payload.realm_roles);
      
      const promises = realmIds.map(realmId => 
        api.get(`/flow/documents/${realmId}`)
          .then(response => ({
            realmId,
            documents: response.data
          }))
          .catch(error => ({
            realmId,
            error: error.message,
            documents: []
          }))
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

      return allDocuments;
    } catch (error) {
      console.error('Error fetching documents:', error);
      throw error;
    }
  },

  createDocument(realmId, data) {
    return api.post(`/flow/documents/${realmId}`, data);
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
