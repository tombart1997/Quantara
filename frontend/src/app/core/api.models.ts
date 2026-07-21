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

export interface ThesisReviewItem {
  entry: JournalEntry;
  asset_ticker: string | null;
  entry_close: number | null;
  current_close: number | null;
  change_pct: number | null;
  days_open: number;
  review_due: boolean;
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

export interface Indicator {
  id: string;
  name: string;
  watch: string;
}

export interface AiConsultResponse {
  prompt: string;
  configured: boolean;
  model: string;
  response: string | null;
  error?: string | null;
}

export interface RefreshStatus {
  last_run: string | null;
  last_result: unknown;
  running: boolean;
}

export interface FxMatrix {
  currencies: string[];
  /** rates[row][col] = units of COL per 1 ROW. */
  rates: Record<string, Record<string, number>>;
  /** Daily % change per cross, same shape as rates. */
  changes_pct: Record<string, Record<string, number>>;
  missing: string[];
  updated_at: string;
}

// --- Ripple Engine ------------------------------------------------------------

export interface RipplePositioning {
  ticker: string;
  report_date: string;
  net_contracts: number;
  net_pct_oi: number;
  wow_change: number;
  z_score_52w: number;
  source: string;
}

export interface RippleExposure {
  ticker: string;
  direction: 1 | -1;
  impact: number;
  magnitude_pct: number;
  lag: string;
  confidence: number; // 0-1
  order: 1 | 2 | 3;
  decay: number;
  provenance: string;
  priced_in: number | null; // 0-1
  crowd_source: string | null; // data source behind priced_in, e.g. "CFTC COT"
  positioning?: RipplePositioning | null;
}

export interface RippleSignal {
  id: string;
  name: string;
  description: string;
  activation: number; // 0-100
  activation_detail: string;
  active: boolean;
  propagation_strength: number;
  exposure: RippleExposure[];
}

export interface RippleContribution {
  signal_id: string;
  signal_name: string;
  activation: number;
  impact: number;
  order: number;
  lag: string;
  confidence: number;
  magnitude_pct: number;
  provenance: string;
}

export interface RippleAssetCard {
  ticker: string;
  name: string;
  net_score: number;
  dominant_signal: string;
  conflict: boolean;
  contributions: RippleContribution[];
}

export interface RippleImplicitBet {
  signal: string;
  net_impact: number;
}

export interface RipplePortfolio {
  positions: RippleAssetCard[];
  implicit_bets: RippleImplicitBet[];
}

export interface RippleState {
  mode: string; // 'live' | 'scenario'
  signals: RippleSignal[];
  assets: RippleAssetCard[];
  portfolio: RipplePortfolio;
}

// --- Weather (NOAA OISST) -------------------------------------------------------

export interface SstLatest {
  latest: string;
  cached: string[];
}

export interface SstGrid {
  date: string;
  /** 90 latitudes, ascending. */
  lats: number[];
  /** 180 longitudes, -180..180. */
  lons: number[];
  /** Row-major [lat][lon]; null = land/ice. */
  grid: (number | null)[][];
  /** SST anomaly vs climatology (°C), same shape/nulls as grid. */
  anom: (number | null)[][];
  source: string;
}

export interface PrecacheStartResponse {
  started: boolean;
  reason?: string;
}

export interface PrecacheStatus {
  running: boolean;
  done: number;
  total: number;
  current: string | null;
  cached_total: number;
}

// --- Backtest ------------------------------------------------------------------

export interface HorizonStats {
  n: number;
  hit_rate: number;
  mean: number;
  median: number;
  baseline_mean: number;
  delta_vs_baseline: number;
}

export interface BacktestRule {
  rule: string;
  title: string;
  fires: number;
  /** Keyed by horizon in days, e.g. "5" | "10" | "20". */
  per_horizon: Record<string, HorizonStats>;
}

export interface BacktestAsset {
  ticker: string;
  name: string;
  /** Only rules with >= 3 fires for this asset. */
  rules: Record<string, Record<string, HorizonStats>>;
}

export interface BacktestResult {
  window: { from: string; to: string };
  horizons: number[];
  baseline_mean_returns: Record<string, number>;
  baseline_note: string;
  method_note: string;
  total_fires: number;
  rules: BacktestRule[];
  assets: BacktestAsset[];
}

// --- Temperature ---------------------------------------------------------------

export interface GeoPlace {
  name: string;
  country: string;
  admin1: string | null;
  lat: number;
  lon: number;
}

export interface TempHistoryPoint {
  date: string;
  mean: number;
  max: number;
  min: number;
  /** Present on fresh cache entries; null on older ones. */
  wind_max?: number | null;
  humidity?: number | null;
  cloud?: number | null;
}

export interface TempForecastPoint {
  date: string;
  mean: number;
  spread: number;
}

export interface TempClimatologyPoint {
  date: string;
  mean: number;
  std: number;
}

export interface CurrentConditions {
  temperature: number;
  humidity: number;
  cloud: number;
  wind_speed: number;
  wind_dir: number;
  gusts: number;
}

export interface ConditionsPoint {
  date: string;
  precip_prob: number;
  wind_max: number;
  gusts_max: number;
  wind_dir: number;
  humidity: number;
  cloud: number;
}

export interface TemperatureAnalysis {
  location: { lat: number; lon: number; elevation: number };
  current: CurrentConditions;
  history: TempHistoryPoint[];
  forecast: TempForecastPoint[];
  climatology: TempClimatologyPoint[];
  /** 16 days, date-parallel to forecast. */
  conditions: ConditionsPoint[];
  sources: string;
}
