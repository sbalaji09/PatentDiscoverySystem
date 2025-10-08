import axios from 'axios';

const API_BASE_URL = 'http://localhost:5000/api';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// API service methods
export const patentApi = {
  // Get list of patents with optional search
  getPatents: async (searchQuery = '') => {
    try {
      const response = await api.get('/patents', {
        params: { search: searchQuery },
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching patents:', error);
      throw error;
    }
  },

  // Get single patent by patent number
  getPatentDetail: async (patentNumber) => {
    try {
      const response = await api.get(`/patents/${patentNumber}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching patent detail:', error);
      throw error;
    }
  },

  // Search patents by user idea (fetches from USPTO)
  searchByIdea: async (userIdea, storeResults = false) => {
    try {
      const response = await api.post('/search', {
        user_idea: userIdea,
        store: storeResults,
      });
      return response.data;
    } catch (error) {
      console.error('Error searching patents:', error);
      throw error;
    }
  },

  // Get database statistics
  getStats: async () => {
    try {
      const response = await api.get('/stats');
      return response.data;
    } catch (error) {
      console.error('Error fetching stats:', error);
      throw error;
    }
  },
};

export default patentApi;
