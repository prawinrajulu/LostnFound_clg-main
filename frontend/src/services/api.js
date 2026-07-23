import axios from 'axios';

// CRA (react-scripts / craco) — must use REACT_APP_ prefix with process.env.
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'https://lostnfound-clg-main.onrender.com';
const API = `${BACKEND_URL}/api`;

/**
 * Safely extracts a string error message from any error object.
 * Handles Pydantic validation arrays/objects, response messages, and fallback text.
 */
export const getErrorMessage = (error, fallback = 'An unexpected error occurred') => {
  if (!error) return fallback;
  
  const detail = error?.response?.data?.detail;
  
  if (typeof detail === 'string') {
    return detail;
  }
  
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') return item;
        if (item && typeof item === 'object' && item.msg) return item.msg;
        if (item && typeof item === 'object') return JSON.stringify(item);
        return String(item);
      })
      .filter(Boolean)
      .join(', ') || fallback;
  }
  
  if (detail && typeof detail === 'object') {
    if (detail.msg) return String(detail.msg);
    if (detail.message) return String(detail.message);
    return JSON.stringify(detail);
  }
  
  const message = error?.response?.data?.message;
  if (typeof message === 'string') return message;
  
  if (typeof error.message === 'string' && error.message) {
    return error.message;
  }
  
  if (typeof error === 'string') return error;
  
  return fallback;
};

// Create axios instance with auth header
const createAuthAxios = () => {
  const instance = axios.create({
    baseURL: API
  });

  instance.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  instance.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status === 401) {
        localStorage.removeItem('token');
        window.location.href = '/';
      }
      if (error.response?.data?.detail) {
        error.response.data.detail = getErrorMessage(error);
      }
      return Promise.reject(error);
    }
  );

  return instance;
};

export const api = createAuthAxios();

// Student APIs
export const studentAPI = {
  getProfile: () => api.get('/profile'),
  uploadProfilePicture: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/profile/picture', formData);
  }
};

// Items APIs
export const itemsAPI = {
  /**
   * Public endpoint — no auth required.
   * Backend returns a plain JSON array: [{ id, item_type, description, ... }, ...]
   * We always resolve with { data: Array } so callers can safely do response.data.
   */
  getPublicItems: () =>
    axios
      .get(`${API}/items/public`)
      .then((response) => {
        // Normalise: ensure response.data is always an array
        const raw = response.data;
        if (Array.isArray(raw)) {
          return response; // already correct shape
        }
        // Defensive unwrap for unexpected wrapping
        if (raw && Array.isArray(raw.items)) {
          return { ...response, data: raw.items };
        }
        if (raw && Array.isArray(raw.data)) {
          return { ...response, data: raw.data };
        }
        console.error('[itemsAPI.getPublicItems] Unexpected response shape:', raw);
        return { ...response, data: [] };
      })
      .catch((error) => {
        console.error('[itemsAPI.getPublicItems] Request failed:', error);
        // Re-throw so the caller's catch block handles it gracefully
        return Promise.reject(error);
      }),

  getMyItems: () => api.get('/items/my'),
  getItems: (params) => api.get('/items', { params }),
  getItem: (id) => api.get(`/items/${id}`),
  createItem: (formData) => api.post('/items', formData),
  deleteItem: (id, reason) => api.delete(`/items/${id}`, { data: { reason } }),
  getDeletedItems: () => api.get('/items/deleted/all'),
  restoreItem: (id) => api.post(`/items/${id}/restore`),
  permanentDeleteItem: (id) => api.delete(`/items/${id}/permanent`)
};

// Claims APIs
export const claimsAPI = {
  getClaims: (params) => api.get('/claims', { params }),
  getClaim: (id) => api.get(`/claims/${id}`),
  createClaim: (itemId, message) => {
    if (typeof itemId === 'object' && itemId !== null) {
      const id = itemId.item_id || itemId.itemId || itemId.id;
      const msg = itemId.message || itemId.details || message || '';
      return api.post('/claims', { item_id: id, message: msg });
    }
    return api.post('/claims', { item_id: itemId, message: message || '' });
  },
  addVerificationQuestion: (claimId, question) =>
    api.post(`/claims/${claimId}/verification-question`, { claim_id: claimId, question }),
  answerVerification: (claimId, answer) =>
    api.post(`/claims/${claimId}/answer`, { claim_id: claimId, answer }),
  makeDecision: (claimId, status, notes) =>
    api.post(`/claims/${claimId}/decision`, { status, notes })
};

// Messages APIs
export const messagesAPI = {
  getMessages: () => api.get('/messages'),
  getUnreadCount: () => api.get('/messages/unread-count'),
  sendMessage: (recipientId, recipientType, content, itemId) =>
    api.post('/messages', { recipient_id: recipientId, recipient_type: recipientType, content, item_id: itemId }),
  markAsRead: (id) => api.post(`/messages/${id}/read`),
  markAllRead: () => api.post('/messages/mark-all-read')
};

// Students APIs (Admin)
export const studentsAPI = {
  getStudents: () => api.get('/students'),
  getStudent: (id) => api.get(`/students/${id}`),
  uploadExcel: (file, department, year) => {
    const formData = new FormData();
    formData.append('file', file);
    if (department) formData.append('department', department);
    if (year) formData.append('year', year);
    return api.post('/students/upload-excel', formData);
  },
  addNote: (studentId, note) =>
    api.post(`/students/${studentId}/admin-note`, { student_id: studentId, note }),
  deleteStudent: (id) => api.delete(`/students/${id}`),
  updateStudent: (id, data) => api.put(`/students/${id}`, data),
  renameFolder: (oldDepartment, newDepartment, oldYear = null, newYear = null) =>
    api.put('/students/rename-folder', {
      old_department: oldDepartment,
      new_department: newDepartment,
      old_year: oldYear,
      new_year: newYear,
    }),
  getFolderTree: () => api.get('/students/folder-tree'),
  getByFolder: (department, year) => api.get('/students/by-folder', { params: { department, year } }),
  moveStudent: (id, department, year) => api.put(`/students/${id}/move`, { department, year }),
  bulkMove: (studentIds, department, year) => api.post('/students/bulk-move', { student_ids: studentIds, department, year }),
  bulkDelete: (studentIds) => api.post('/students/bulk-delete', { student_ids: studentIds })
};

// Admin APIs
export const adminAPI = {
  getAdmins: () => api.get('/admins'),
  createAdmin: (username, password, fullName) =>
    api.post('/admins', { username, password, full_name: fullName }),
  deleteAdmin: (id) => api.delete(`/admins/${id}`),
  changePassword: (oldPassword, newPassword) =>
    api.post('/auth/admin/change-password', { old_password: oldPassword, new_password: newPassword })
};

// Stats APIs
export const statsAPI = {
  getStats: () => api.get('/stats')
};

// AI APIs
export const aiAPI = {
  getMatches: () => api.get('/ai/matches'),
  initiateVerification: (lostItemId, foundItemId, question) =>
    api.post('/ai/matches/initiate-verification', { lost_item_id: lostItemId, found_item_id: foundItemId, question })
};

// Verification APIs
export const verificationAPI = {
  getQueue: () => api.get('/verification/queue'),
  getSession: (matchId) => api.get(`/verification/session/${matchId}`),
  addQuestion: (matchId, question) => api.post(`/verification/session/${matchId}/question`, { question }),
  submitAnswer: (matchId, questionId, answer) => api.post(`/verification/session/${matchId}/answer`, { question_id: questionId, answer }),
  updateNotes: (matchId, notes) => api.post(`/verification/session/${matchId}/notes`, { notes }),
  makeDecision: (matchId, status) => api.post(`/verification/session/${matchId}/decision`, { status }),
  completeVerification: (matchId, handoverConfirmed) => api.post(`/verification/session/${matchId}/complete`, { handover_confirmed: handoverConfirmed }),
  getStudentVerifications: () => api.get('/student/verifications')
};
