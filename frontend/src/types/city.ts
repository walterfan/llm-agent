/**
 * City types for API requests and responses
 */

export interface City {
  location_id: string
  location_name_zh: string
  location_name_en?: string
  ad_code: string
  province_zh?: string
  city_zh?: string
  display_name: string
}

export interface CityDetail extends City {
  province_en?: string
  city_en?: string
  latitude?: number
  longitude?: number
  timezone?: string
}

export interface CitySearchResponse {
  cities: City[]
  total: number
}
