// TypeScript mirrors of the backend schemas (backend/app/schemas/__init__.py).
// Keep these in sync when the API changes.

export type AssetType = 'STOCK' | 'COMMODITY' | 'ETF' | 'INDEX';

export type AssetRegion = 'US' | 'EUROPE' | 'ASIA' | 'GLOBAL';
export type EventType =
  | 'EARNINGS'
  | 'ECONOMIC_RELEASE'
  | 'COMPANY_ANNOUNCEMENT'
  | 'COMMODITY_REPORT'
  | 'WEATHER';

export type Recurrence = 'NONE' | 'WEEKLY' | 'MONTHLY' | 'QUARTERLY' | 'YEARLY';

export interface Asset {
  id: number;
  ticker: string;
  name: string;
  exchange: string;
  asset_type: AssetType;
  sector: string | null;
  region: AssetRegion | null;
  leverage: number;
  in_watchlist: boolean;
}

export interface PriceBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number | null;
}

// Named MarketEvent because `Event` is a built-in DOM type in TypeScript.
export interface MarketEvent {
  id: number;
  asset_id: number | null;
  asset_ticker: string | null;
  event_type: EventType;
  date: string;
  title: string;
  description: string | null;
  importance: number;
  recurrence: Recurrence;
  series_id: string | null;
}

export interface EventCreate {
  asset_id: number | null;
  event_type: EventType;
  date: string; // ISO datetime, e.g. 2026-08-01T14:00:00
  title: string;
  description: string | null;
  importance: number;
  recurrence?: Recurrence;
}

export interface NewsArticle {
  id: number;
  source: string;
  headline: string;
  url: string;
  summary: string | null;
  published_at: string;
  sentiment: number | null;
  tickers: string[];
}

export interface JournalEntry {
  id: number;
  asset_id: number;
  asset_ticker: string | null;
  date: string;
  thesis: string;
  expected_outcome: string | null;
  risk: string | null;
  confidence: number;
}

export interface JournalCreate {
  asset_id: number;
  date: string;
  thesis: string;
  expected_outcome?: string | null;
  risk?: string | null;
  confidence: number;
}

export interface Signal {
  id: number;
  asset_id: number;
  asset_ticker: string | null;
  name: string;
  reasons: string[];
  score: number;
  created_at: string;
}

export interface WatchlistItem {
  asset: Asset;
  latest_close: number | null;
  change_pct: number | null;
}

export interface DashboardResponse {
  watchlist: WatchlistItem[];
  upcoming_events: MarketEvent[];
  recent_news: NewsArticle[];
  active_signals: Signal[];
}

export interface AiStatus {
  configured: boolean;
  model: string;
  base_url: string;
}

export interface AiConsultResponse {
  prompt: string;
  configured: boolean;
  model: string;
  response: string | null;
  error?: string | null;
}
