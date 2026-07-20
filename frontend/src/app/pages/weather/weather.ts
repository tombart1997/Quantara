import { Component, DestroyRef, OnInit, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { DecimalPipe } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import {
  EMPTY,
  Subject,
  catchError,
  debounceTime,
  distinctUntilChanged,
  interval,
  startWith,
  switchMap,
  takeWhile,
} from 'rxjs';
import * as echarts from 'echarts';
import type { EChartsOption } from 'echarts';
import { NgxEchartsDirective, provideEchartsCore } from 'ngx-echarts';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSliderModule } from '@angular/material/slider';
import { MatSnackBar } from '@angular/material/snack-bar';

import { ApiService } from '../../core/api.service';
import { PrecacheStatus, SstGrid, SstLatest } from '../../core/api.models';

const NINO34: [number, number][] = [
  [-170, -5],
  [-120, -5],
  [-120, 5],
  [-170, 5],
  [-170, -5], // closed loop
];

@Component({
  selector: 'app-weather',
  imports: [
    DecimalPipe,
    NgxEchartsDirective,
    MatButtonModule,
    MatButtonToggleModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    MatSliderModule,
  ],
  providers: [provideEchartsCore({ echarts })],
  templateUrl: './weather.html',
  styleUrl: './weather.scss',
})
export class WeatherComponent implements OnInit {
  private readonly api = inject(ApiService);
  private readonly http = inject(HttpClient);
  private readonly snackBar = inject(MatSnackBar);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly latest = signal<string | null>(null);
  protected readonly cachedDates = signal<Set<string>>(new Set());
  protected readonly mapReady = signal(false);
  protected readonly loadingInit = signal(true);

  /** Days back from `latest` (0 = latest, max 364). */
  protected readonly dayOffset = signal(0);
  protected readonly selectedDate = computed(() => this.dateForOffset(this.dayOffset()));
  /** What the label shows: the actually loaded grid date, falling back to the slider. */
  protected readonly displayedDate = computed(
    () => this.sst()?.date ?? this.selectedDate(),
  );

  protected readonly sst = signal<SstGrid | null>(null);
  protected readonly loadingGrid = signal(false);

  /** Anomaly is the default: absolute SST looks the same every day. */
  protected readonly viewMode = signal<'anom' | 'abs'>('anom');

  private readonly dateRequests = new Subject<string>();

  protected readonly stats = computed(() => {
    const grid = this.sst();
    if (!grid) return null;
    const anomView = this.viewMode() === 'anom';
    const cells = anomView ? grid.anom : grid.grid;
    let count = 0;
    let sum = 0;
    let min = Infinity;
    let max = -Infinity;
    for (const row of cells) {
      for (const value of row) {
        if (value != null) {
          count++;
          sum += value;
          if (value < min) min = value;
          if (value > max) max = value;
        }
      }
    }
    return { count, sum, min, max, anomView, source: grid.source };
  });

  /** Mean anomaly inside the Niño 3.4 box (5°S–5°N, 170°W–120°W). */
  protected readonly nino34 = computed(() => {
    const grid = this.sst();
    if (!grid) return null;
    let sum = 0;
    let count = 0;
    grid.lats.forEach((lat, i) => {
      if (lat < -5 || lat > 5) return;
      grid.lons.forEach((lon, j) => {
        if (lon < -170 || lon > -120) return;
        const value = grid.anom[i][j];
        if (value != null) {
          sum += value;
          count++;
        }
      });
    });
    return count > 0 ? sum / count : null;
  });

  protected readonly chartOptions = computed<EChartsOption | null>(() => {
    const grid = this.sst();
    if (!grid || !this.mapReady()) return null;
    const anomView = this.viewMode() === 'anom';
    const cells = anomView ? grid.anom : grid.grid;
    const data: number[][] = [];
    cells.forEach((row, i) => {
      row.forEach((value, j) => {
        if (value != null) data.push([grid.lons[j], grid.lats[i], value]);
      });
    });
    // The geo scatter/custom combo doesn't match ECharts 6's strict series
    // union; the shape is correct at runtime, so assert the option type.
    return {
      backgroundColor: '#0c121b',
      tooltip: {
        backgroundColor: '#1a2433',
        borderColor: 'rgba(255, 255, 255, 0.12)',
        textStyle: { color: '#e6edf5' },
        formatter: (params: unknown) => {
          const p = params as { seriesType?: string; name?: string; value?: number[] };
          // Ocean point -> temperature; landmass -> country name.
          if (p.seriesType === 'scatter' && p.value) {
            const value = p.value;
            const formatted = anomView
              ? `${value[2] > 0 ? '+' : ''}${value[2].toFixed(1)}°C anomaly`
              : `${value[2].toFixed(1)}°C`;
            return `${value[1].toFixed(1)}°, ${value[0].toFixed(1)}°: ${formatted}`;
          }
          return p.name ?? '';
        },
      },
      geo: {
        map: 'world',
        roam: false,
        silent: false,
        itemStyle: {
          areaColor: '#1a2433',
          borderColor: 'rgba(255, 255, 255, 0.15)',
          borderWidth: 0.5,
        },
        emphasis: {
          itemStyle: { areaColor: '#26374e' },
          label: { show: false },
        },
      },
      visualMap: anomView
        ? {
            type: 'continuous',
            dimension: 2,
            min: -3,
            max: 3,
            calculable: false,
            text: ['+3°', '−3°'],
            textStyle: { color: '#9aa7b8' },
            left: 10,
            bottom: 10,
            inRange: {
              color: ['#08306b', '#6ec1ff', '#e8eef4', '#fdae61', '#d73027'],
            },
          }
        : {
            type: 'continuous',
            dimension: 2,
            min: -2,
            max: 33,
            calculable: false,
            text: ['33°C', '-2°C'],
            textStyle: { color: '#9aa7b8' },
            left: 10,
            bottom: 10,
            inRange: {
              color: ['#08306b', '#2b8cbe', '#4eb3d3', '#7fcdbb', '#fee08b', '#fdae61', '#d73027'],
            },
          },
      series: [
        {
          name: 'SST',
          type: 'scatter',
          coordinateSystem: 'geo',
          data,
          symbolSize: 3.5,
          itemStyle: { opacity: 0.75 },
          progressive: 4000,
        },
        {
          // ECharts 6 dropped geo support for line/markArea — draw the Niño
          // 3.4 box with a custom series that projects lon/lat itself.
          name: 'Niño 3.4',
          type: 'custom',
          coordinateSystem: 'geo',
          silent: true,
          renderItem: (_params: unknown, api: unknown) => {
            const coord = (api as { coord: (c: number[]) => number[] }).coord;
            const pts = NINO34.slice(0, 4).map((c) => coord(c));
            return {
              type: 'group',
              children: [
                {
                  type: 'polygon',
                  shape: { points: pts },
                  style: { stroke: '#6ec1ff', lineWidth: 1.5, lineDash: [4, 4], fill: 'transparent' },
                },
                {
                  type: 'text',
                  x: pts[2][0] - 50,
                  y: pts[2][1] - 6,
                  style: { text: 'Niño 3.4', fill: '#6ec1ff', fontSize: 11 },
                },
              ],
            };
          },
          data: [0],
        },
      ] as EChartsOption['series'],
    } as EChartsOption;
  });

  ngOnInit(): void {
    this.http.get('assets/countries.geo.json').subscribe((geo) => {
      echarts.registerMap('world', geo as Parameters<typeof echarts.registerMap>[1]);
      this.mapReady.set(true);
    });

    this.api.getSstLatest().subscribe((info) => {
      this.applyLatest(info);
      this.loadingInit.set(false);
      this.dateRequests.next(info.latest);
    });

    // A pre-cache started elsewhere (another tab, an earlier visit) still shows progress.
    this.api.getPrecacheStatus().subscribe((status) => {
      if (status.running) {
        this.precache.set(status);
        this.pollPrecache();
      }
    });

    // Scrubbing the slider emits dates here; debounce + switchMap keeps only the
    // latest request (an in-flight NOAA download is abandoned, not stacked).
    this.dateRequests
      .pipe(
        debounceTime(300),
        distinctUntilChanged(),
        takeUntilDestroyed(this.destroyRef),
        switchMap((day) => {
          this.loadingGrid.set(true);
          return this.api.getSst(day).pipe(
            catchError((err: HttpErrorResponse) => {
              this.loadingGrid.set(false);
              this.snackBar.open(
                err.status === 404 ? 'No SST data for this date' : 'Failed to load SST data',
                undefined,
                { duration: 3000 },
              );
              // Stay on the last good date.
              const good = this.sst()?.date;
              if (good && this.latest()) {
                this.dayOffset.set(this.offsetForDate(good));
              }
              return EMPTY;
            }),
          );
        }),
      )
      .subscribe((grid) => {
        this.sst.set(grid);
        this.loadingGrid.set(false);
        this.cachedDates.update((dates) => new Set(dates).add(grid.date));
      });
  }

  protected onSlider(value: number): void {
    this.dayOffset.set(value);
    this.dateRequests.next(this.selectedDate());
  }

  protected onDatePicked(value: string): void {
    if (!value) return;
    const offset = this.offsetForDate(value);
    // Within slider range -> sync the slider; older -> leave it, show the map anyway.
    if (offset >= 0 && offset <= 364) this.dayOffset.set(offset);
    this.dateRequests.next(value);
  }

  // --- Pre-cache ---------------------------------------------------------------

  protected readonly precache = signal<PrecacheStatus | null>(null);
  private pollingPrecache = false;

  protected readonly precachePct = computed(() => {
    const status = this.precache();
    return status && status.total > 0 ? (status.done / status.total) * 100 : 0;
  });

  protected startPrecache(): void {
    // Whether this starts a run or one is already running, just poll the status.
    this.api.precacheSst(90).subscribe(() => this.pollPrecache());
  }

  private pollPrecache(): void {
    if (this.pollingPrecache) return;
    this.pollingPrecache = true;
    interval(3_000)
      .pipe(
        startWith(0),
        takeUntilDestroyed(this.destroyRef),
        switchMap(() => this.api.getPrecacheStatus().pipe(catchError(() => EMPTY))),
        // Inclusive: emit the final not-running status, then complete the stream.
        takeWhile((status) => status.running, true),
      )
      .subscribe((status) => {
        if (status.running) {
          this.precache.set(status);
        } else {
          this.pollingPrecache = false;
          this.precache.set(null);
          this.snackBar.open('Pre-cache complete', undefined, { duration: 2500 });
          this.api.getSstLatest().subscribe((info) => this.applyLatest(info));
        }
      });
  }

  private applyLatest(info: SstLatest): void {
    this.latest.set(info.latest);
    this.cachedDates.set(new Set(info.cached));
  }

  protected readonly sliderLabel = (value: number): string => this.dateForOffset(value);

  private dateForOffset(offset: number): string {
    const latest = this.latest();
    if (!latest) return '';
    const date = new Date(`${latest}T00:00:00Z`);
    date.setUTCDate(date.getUTCDate() - offset);
    return date.toISOString().slice(0, 10);
  }

  private offsetForDate(day: string): number {
    const latest = this.latest();
    if (!latest) return 0;
    const ms = new Date(`${latest}T00:00:00Z`).getTime() - new Date(`${day}T00:00:00Z`).getTime();
    return Math.round(ms / 86_400_000);
  }
}
