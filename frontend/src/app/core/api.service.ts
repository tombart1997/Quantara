import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import {
  AiConsultResponse,
  AiStatus,
  Asset,
  DashboardResponse,
  EventCreate,
  Indicator,
  JournalCreate,
  JournalEntry,
  MarketEvent,
  NewsArticle,
  PriceBar,
  RefreshStatus,
  Signal,
  ThesisReviewItem,
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

  createEvent(payload: EventCreate): Observable<MarketEvent[]> {
    // The API expands recurring events into a series: the response is always an array.
    return this.http.post<MarketEvent[]>(`${this.base}/events`, payload);
  }

  deleteEvent(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/events/${id}`);
  }

  deleteEventSeries(seriesId: string): Observable<{ deleted: number }> {
    return this.http.delete<{ deleted: number }>(`${this.base}/events/series/${seriesId}`);
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

  deleteJournalEntry(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/journal/${id}`);
  }

  getThesisReview(): Observable<ThesisReviewItem[]> {
    return this.http.get<ThesisReviewItem[]>(`${this.base}/journal/review`);
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

  getIndicators(): Observable<Indicator[]> {
    return this.http.get<Indicator[]>(`${this.base}/ai/indicators`);
  }

  getRefreshStatus(): Observable<RefreshStatus> {
    return this.http.get<RefreshStatus>(`${this.base}/refresh-status`);
  }

  /** Latest close prices per ticker (oldest first), one call for all assets. */
  getSparklines(days = 30): Observable<Record<string, number[]>> {
    const params = new HttpParams().set('days', days);
    return this.http.get<Record<string, number[]>>(`${this.base}/assets/sparklines`, { params });
  }

  refreshAll(): Observable<unknown> {
    return this.http.post<unknown>(`${this.base}/refresh-all`, {});
  }

  aiConsult(
    ticker: string | null,
    question: string | null,
    indicators?: string[] | null,
  ): Observable<AiConsultResponse> {
    const body: { ticker: string | null; question: string | null; indicators?: string[] } = {
      ticker,
      question,
    };
    if (indicators?.length) body.indicators = indicators;
    return this.http.post<AiConsultResponse>(`${this.base}/ai/consult`, body);
  }
}
