import { Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute } from '@angular/router';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { DatePipe, DecimalPipe } from '@angular/common';
import { Subject, filter, map, shareReplay, startWith, switchMap } from 'rxjs';
import * as echarts from 'echarts';
import type { EChartsOption } from 'echarts';
import { NgxEchartsDirective, provideEchartsCore } from 'ngx-echarts';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatListModule } from '@angular/material/list';
import { MatProgressBarModule } from '@angular/material/progress-bar';

import { ApiService } from '../../core/api.service';
import { Asset, EventType, Signal } from '../../core/api.models';

@Component({
  selector: 'app-asset-detail',
  imports: [
    DatePipe,
    DecimalPipe,
    ReactiveFormsModule,
    NgxEchartsDirective,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatListModule,
    MatProgressBarModule,
  ],
  providers: [provideEchartsCore({ echarts })],
  templateUrl: './asset-detail.html',
  styleUrl: './asset-detail.scss',
})
export class AssetDetailComponent {
  private readonly api = inject(ApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly fb = inject(FormBuilder);

  private readonly asset$ = this.route.paramMap.pipe(
    map((p) => p.get('ticker') ?? ''),
    filter((ticker) => ticker.length > 0),
    switchMap((ticker) => this.api.getAsset(ticker)),
    shareReplay(1),
  );

  private readonly fetchedAsset = toSignal(this.asset$);
  // Holds the asset returned by the watchlist toggle so the button updates instantly.
  private readonly toggled = signal<Asset | null>(null);
  protected readonly asset = computed(() => this.toggled() ?? this.fetchedAsset());

  protected readonly prices = toSignal(
    this.route.paramMap.pipe(
      map((p) => p.get('ticker') ?? ''),
      filter((ticker) => ticker.length > 0),
      switchMap((ticker) => this.api.getPrices(ticker, 365)),
    ),
    { initialValue: [] },
  );

  protected readonly events = toSignal(
    this.asset$.pipe(
      switchMap((a) => this.api.getEvents({ assetId: a.id })),
      map((events) => [...events].sort((x, y) => x.date.localeCompare(y.date))),
    ),
    { initialValue: [] },
  );

  protected readonly news = toSignal(
    this.asset$.pipe(switchMap((a) => this.api.getNews(a.id))),
    { initialValue: [] },
  );

  protected readonly signals = toSignal(
    this.asset$.pipe(switchMap((a) => this.api.getSignals(a.id))),
    { initialValue: [] },
  );

  private readonly refreshJournal = new Subject<void>();
  protected readonly journal = toSignal(
    this.refreshJournal.pipe(
      startWith(void 0),
      switchMap(() => this.asset$),
      switchMap((a) => this.api.getJournal(a.id)),
    ),
    { initialValue: [] },
  );

  protected readonly chartOptions = computed<EChartsOption | null>(() => {
    const bars = this.prices();
    if (!bars.length) return null;
    return {
      backgroundColor: 'transparent',
      textStyle: { color: '#9aa7b8' },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross', label: { backgroundColor: '#2b3a4f' } },
        backgroundColor: '#1a2433',
        borderColor: 'rgba(255, 255, 255, 0.12)',
        textStyle: { color: '#e6edf5' },
      },
      grid: { left: 60, right: 20, top: 20, bottom: 60 },
      xAxis: {
        type: 'category',
        data: bars.map((b) => b.date),
        axisLine: { lineStyle: { color: '#3a4a5f' } },
        axisLabel: { color: '#9aa7b8' },
      },
      yAxis: {
        scale: true,
        axisLabel: { color: '#9aa7b8' },
        splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.06)' } },
      },
      dataZoom: [
        { type: 'inside' },
        {
          type: 'slider',
          backgroundColor: 'transparent',
          borderColor: '#3a4a5f',
          fillerColor: 'rgba(110, 193, 255, 0.12)',
          handleStyle: { color: '#6ec1ff' },
          moveHandleStyle: { color: '#6ec1ff' },
          dataBackground: {
            lineStyle: { color: '#3a4a5f' },
            areaStyle: { color: 'rgba(110, 193, 255, 0.08)' },
          },
          selectedDataBackground: {
            lineStyle: { color: '#6ec1ff' },
            areaStyle: { color: 'rgba(110, 193, 255, 0.15)' },
          },
          textStyle: { color: '#9aa7b8' },
        },
      ],
      series: [
        {
          name: 'Price',
          type: 'candlestick',
          data: bars.map((b) => [b.open, b.close, b.low, b.high]),
          // Up candles light blue, down candles pink (matches the app palette).
          itemStyle: {
            color: '#6ec1ff',
            color0: '#f48fb1',
            borderColor: '#6ec1ff',
            borderColor0: '#f48fb1',
          },
        },
      ],
    };
  });

  protected readonly form = this.fb.nonNullable.group({
    date: [new Date().toISOString().slice(0, 10), Validators.required],
    thesis: ['', Validators.required],
    expected_outcome: [''],
    risk: [''],
    confidence: [5, [Validators.required, Validators.min(1), Validators.max(10)]],
  });
  protected readonly submitting = signal(false);

  protected toggleWatchlist(): void {
    const asset = this.asset();
    if (!asset) return;
    this.api.toggleWatchlist(asset.ticker).subscribe((updated) => this.toggled.set(updated));
  }

  protected submitJournal(): void {
    const asset = this.asset();
    if (!asset || this.form.invalid || this.submitting()) return;
    this.submitting.set(true);
    const value = this.form.getRawValue();
    this.api
      .createJournalEntry({
        asset_id: asset.id,
        date: value.date,
        thesis: value.thesis,
        expected_outcome: value.expected_outcome || null,
        risk: value.risk || null,
        confidence: value.confidence,
      })
      .subscribe({
        next: () => {
          this.submitting.set(false);
          this.form.reset();
          this.refreshJournal.next();
        },
        error: () => this.submitting.set(false),
      });
  }

  protected formatType(type: EventType): string {
    return type.replace(/_/g, ' ').toLowerCase();
  }

  protected scoreColor(signal: Signal): string {
    if (signal.score >= 70) return 'score-high';
    if (signal.score >= 40) return 'score-mid';
    return 'score-low';
  }
}
