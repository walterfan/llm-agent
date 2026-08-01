/**
 * Weather types for API requests and responses
 */

export type WeatherCondition = '晴' | '多云' | '阴' | '雨' | '雪' | '雾' | '霾' | '沙尘暴' | string // fallback for other conditions

export interface ForecastCast {
  date: string // YYYY-MM-DD
  week: string // Day of week
  dayweather: string
  nightweather: string
  daytemp: string
  nighttemp: string
  daywind: string
  nightwind: string
  daypower: string
  nightpower: string
}

export interface ForecastData {
  city: string
  province: string
  adcode: string
  reporttime: string
  casts: ForecastCast[]
}

export interface WeatherData {
  city: string
  province?: string
  ad_code: string
  weather: WeatherCondition
  temperature: string
  temperature_float: number
  humidity: string
  humidity_float: number
  wind_direction: string
  wind_power: string
  report_time: string
  cached: boolean
  forecast?: ForecastData // Optional forecast data (when extensions=all)
}

export interface WeatherResponse {
  success: boolean
  data?: WeatherData
  error?: string
}

export interface WeatherQuery {
  city: string // City name or AD code
  extensions?: 'base' | 'all' // Weather type: base (current) or all (forecast)
}
