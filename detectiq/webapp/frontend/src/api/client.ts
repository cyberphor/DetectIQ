import axios from 'axios';
import { Rule, RuleFilters, PaginatedResponse, RuleType } from '@/types/rules';
import { Settings } from '@/types/settings';
import { RuleCreationResponse, RuleCreationRequest } from '@/types/api';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  }
});

export const settingsApi = {
  getSettings: async () => {
    try {
      const response = await fetch('/api/app-config/get-config/');
      if (!response.ok) {
        throw new Error('Failed to fetch settings');
      }
      return response.json();
    } catch (error) {
      console.error('Error fetching settings:', error);
      throw error;
    }
  },
  updateSettings: async (settings: Partial<Settings>): Promise<Settings> => {
    const response = await fetch('/api/app-config/update-config/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        ...settings,
        sigma_package_type: settings.sigma_package_type || 'core'
      }),
    });
    if (!response.ok) {
      throw new Error('Failed to update settings');
    }
    return response.json();
  },
  testIntegration: async (integration: string): Promise<{success: boolean; message: string}> => {
    const response = await fetch('/api/app-config/test-integration/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ integration }),
    });
    if (!response.ok) {
      throw new Error('Failed to test integration');
    }
    return response.json();
  },
  checkVectorstores: async () => {
    const response = await fetch('/api/app-config/check-vectorstores/');
    if (!response.ok) {
      throw new Error('Failed to check vectorstores');
    }
    return response.json();
  },
  createVectorstore: async (type: string) => {
    const response = await fetch('/api/app-config/create-vectorstore/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ type }),
    });
    if (!response.ok) {
      throw new Error('Failed to create vectorstore');
    }
    return response.json();
  },
  checkRulePackages: async () => {
    const response = await fetch('/api/app-config/check-rule-packages/');
    if (!response.ok) {
      throw new Error('Failed to check rule packages');
    }
    return response.json();
  },
  updateRulePackage: async (type: string, packageType?: string) => {
    const response = await fetch('/api/app-config/update-rule-package/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ type, package_type: packageType }),
    });
    if (!response.ok) {
      throw new Error('Failed to update rule package');
    }
    return response.json();
  },
  getSigmaPackages: async () => {
    const response = await fetch('/api/app-config/get-sigma-packages/');
    if (!response.ok) {
      throw new Error('Failed to fetch Sigma packages');
    }
    return response.json();
  },
};

export const rulesApi = {
  getRules: async (filters?: RuleFilters): Promise<PaginatedResponse<Rule>> => {
    const response = await apiClient.get<PaginatedResponse<Rule>>('/api/rules/', { 
      params: filters 
    });
    return response.data;
  },

  getRulesByType: async (type: RuleType): Promise<PaginatedResponse<Rule>> => {
    const response = await apiClient.get<PaginatedResponse<Rule>>(`/api/rules/${type}/`);
    return response.data;
  },

  searchRules: async (type: RuleType, query: string): Promise<PaginatedResponse<Rule>> => {
    const response = await apiClient.get<PaginatedResponse<Rule>>(`/api/rules/${type}/search/`, {
      params: { q: query }
    });
    return response.data;
  },

  updateRule: async (ruleId: string, updates: Partial<Rule>): Promise<Rule> => {
    const response = await apiClient.patch<Rule>(`/api/rules/${ruleId}/`, updates);
    return response.data;
  },

  deleteRule: async (ruleId: string): Promise<void> => {
    await apiClient.delete(`/api/rules/${ruleId}/`);
  },

  deployRule: async (ruleId: string, integration: string): Promise<{success: boolean; message: string}> => {
    const response = await apiClient.post<{success: boolean; message: string}>(
      `/api/rules/${ruleId}/deploy/`,
      { integration }
    );
    return response.data;
  },

  getRule: async (id: string): Promise<Rule> => {
    const response = await apiClient.get<Rule>(`/api/rules/${id}/`);
    return response.data;
  },
}; 


export const ruleCreatorApi = {
  createRule: async (formData: FormData): Promise<RuleCreationResponse> => {
    const response = await fetch('/api/rule-creator/create-with-llm/', {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      throw new Error('Failed to create rule');
    }
    
    return response.json();
  },
};