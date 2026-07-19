import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import {
  AiConsultResponse,
  AiStatus,
  Asset,
  DashboardResponse,
  JournalCreate,
  JournalEntry,
  MarketEvent,
  NewsArticle,
  PriceBar,
  Signal,
} from './api.models';

/** Single access point for every backend call. Components never build URLs. */
@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiUrl;

  getDashboard(): Observable<DashboardResponse> {
    return this.http.get<DashboardResponse>(`${this.base}/dashboard`);
  }

  getAssets(watchlistOnly = false): Observable<Asset[]> {
    const params = new HttpParams().set('watchlist_only', watchlistOnly);
    return this.http.get<Asset[]>(`${this.base}/assets`, { params });
  }

  getAsset(ticker: string): Observable<Asset> {
    return this.http.get<Asset>(`${this.base}/assets/${ticker}`);
  }

  toggleWatchlist(ticker: string): Observable<Asset> {
    return this.http.post<Asset>(`${this.base}/assets/${ticker}/watchlist`, {});
  }

  getPrices(ticker: string, days = 365): Observable<PriceBar[]> {
    const params = new HttpParams().set('days', days);
    return this.http.get<PriceBar[]>(`${this.base}/assets/${ticker}/prices`, { params });
  }

  getEvents(options: { upcomingOnly?: boolean; assetId?: number } = {}): Observable<MarketEvent[]> {
    let params = new HttpParams();
    if (options.upcomingOnly) params = params.set('upcoming_only', true);
    if (options.assetId != null) params = params.set('asset_id', options.assetId);
    return this.http.get<MarketEvent[]>(`${this.base}/events`, { params });
  }

  getNews(assetId?: number, limit = 20): Observable<NewsArticle[]> {
    let params = new HttpParams().set('limit', limit);
    if (assetId != null) params = params.set('asset_id', assetId);
    return this.http.get<NewsArticle[]>(`${this.base}/news`, { params });
  }

  getJournal(assetId?: number): Observable<JournalEntry[]> {
    let params = new HttpParams();
    if (assetId != null) params = params.set('asset_id', assetId);
    return this.http.get<JournalEntry[]>(`${this.base}/journal`, { params });
  }

  createJournalEntry(entry: JournalCreate): Observable<JournalEntry> {
    return this.http.post<JournalEntry>(`${this.base}/journal`, entry);
  }

  getSignals(assetId?: number): Observable<Signal[]> {
    let params = new HttpParams();
    if (assetId != null) params = params.set('asset_id', assetId);
    return this.http.get<Signal[]>(`${this.base}/signals`, { params });
  }

  recomputeSignals(): Observable<Signal[]> {
    return this.http.post<Signal[]>(`${this.base}/signals/recompute`, {});
  }

  getAiStatus(): Observable<AiStatus> {
    return this.http.get<AiStatus>(`${this.base}/ai/status`);
  }

  aiConsult(ticker: string | null, question: string | null): Observable<AiConsultResponse> {
    return this.http.post<AiConsultResponse>(`${this.base}/ai/consult`, { ticker, question });
  }
}
