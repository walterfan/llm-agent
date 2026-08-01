/**
 * City API service
 */

import api from './api'
import type { CityDetail, CitySearchResponse } from '@/types/city'

export const cityService = {
  /**
   * Search cities by name (Chinese or English)
   */
  async searchCities(query: string, limit: number = 20): Promise<CitySearchResponse> {
    const response = await api.get<CitySearchResponse>('/cities/search', {
      params: { q: query, limit },
    })
    return response.data
  },

  /**
   * Get city details by AD code
   */
  async getCityByCode(adCode: string): Promise<CityDetail> {
    const response = await api.get<CityDetail>(`/cities/${adCode}`)
    return response.data
  },
}

export default cityService
