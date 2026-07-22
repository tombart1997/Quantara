import { Component, DestroyRef, OnInit, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { DecimalPipe } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import {
  EMPTY,
  Subject,
  catchError,
  debounceTime,
  interval,
  map,
  merge,
  of,
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
import { MatCheckboxModule } from '@angular/material/checkbox';
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
    MatCheckboxModule,
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
  protected readonly finalLatest = signal<string | null>(null);
  protected readonly cachedDates = signal<Set<string>>(new Set());
  protected readonly mapReady = signal(false);
  protected readonly loadingInit = signal(true);

  /** Days back from `latest` (0 = latest, max 944 — the full precache window). */
  protected readonly dayOffset = signal(0);
  protected readonly selectedDate = computed(() => this.dateForOffset(this.dayOffset()));
  /** What the label shows: the actually loaded grid date, falling back to the slider. */
  protected readonly displayedDate = computed(
    () => this.sst()?.date ?? this.selectedDate(),
  );

  /** Long-form dates for the readouts. */
  protected readonly bigDate = computed(() => this.formatLong(this.displayedDate()));
  protected readonly scrollerDate = computed(() => this.formatLong(this.selectedDate()));

  /** Month/year ruler ticks above the timeline (label every 3rd month). */
  protected readonly rulerTicks = computed(() => {
    const latest = this.latest();
    if (!latest) return [];
    const MONTHS = ['Jan.', 'Feb.', 'Mar.', 'Apr.', 'May', 'Jun.', 'Jul.',
                    'Aug.', 'Sep.', 'Oct.', 'Nov.', 'Dec.'];
    const end = new Date(`${latest}T00:00:00Z`);
    const cursor = new Date(Date.UTC(end.getUTCFullYear(), end.getUTCMonth(), 1));
    const ticks: { pct: number; label: string; offset: number; showLabel: boolean }[] = [];
    let i = 0;
    while (cursor <= end) {
      const offset = Math.round((end.getTime() - cursor.getTime()) / 86_400_000);
      if (offset >= 0 && offset <= 944) {
        ticks.push({
          pct: ((944 - offset) / 944) * 100,
          label: `${MONTHS[cursor.getUTCMonth()]} ${cursor.getUTCFullYear()}`,
          offset,
          showLabel: i % 2 === 0,
        });
        i++;
      }
      cursor.setUTCMonth(cursor.getUTCMonth() + 1);
    }
    return ticks;
  });

  private formatLong(iso: string): string {
    if (!iso) return '';
    const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
                    'August', 'September', 'October', 'November', 'December'];
    const [y, m, d] = iso.split('-').map(Number);
    return `${d} ${MONTHS[m - 1]} ${y}`;
  }

  protected readonly sst = signal<SstGrid | null>(null);

  /** Grid store keyed by date — powers the compare-years panels. */
  protected readonly grids = signal<Record<string, SstGrid>>({});
  /** Dates currently being downloaded. */
  protected readonly loadingDates = signal<Set<string>>(new Set());
  protected readonly loadingGrid = computed(() => this.loadingDates().size > 0);

  protected readonly compareMode = signal(false);
  /** Dates shown as panels in compare mode (primary first). */
  protected readonly compareDates = signal<string[]>([]);

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
    return this.buildOptions(grid, this.viewMode() === 'anom');
  });

  /** Per-date options for compare mode; rebuilt instantly on viewMode change. */
  protected readonly panelOptions = computed(() => {
    const anomView = this.viewMode() === 'anom';
    const ready = this.mapReady();
    const options: Record<string, EChartsOption> = {};
    if (ready) {
      for (const [day, grid] of Object.entries(this.grids())) {
        options[day] = this.buildOptions(grid, anomView);
      }
    }
    return options;
  });

  private buildOptions(grid: SstGrid, anomView: boolean): EChartsOption {
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
  }

  /** Selected date plus the same month/day 1 and 2 years earlier (>= 1981-09-01). */
  private comparisonDatesFor(day: string): string[] {
    const dates = [day];
    for (const years of [1, 2]) {
      const earlier = this.yearsEarlier(day, years);
      if (earlier >= '1981-09-01') dates.push(earlier);
    }
    return dates;
  }

  private yearsEarlier(day: string, years: number): string {
    const date = new Date(`${day}T00:00:00Z`);
    date.setUTCFullYear(date.getUTCFullYear() - years);
    return date.toISOString().slice(0, 10);
  }

  protected onCompareToggle(checked: boolean): void {
    this.compareMode.set(checked);
    // Re-run the debounced stream; grids already in the store are reused.
    this.dateRequests.next(this.selectedDate());
  }

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
    // latest selection (in-flight NOAA downloads are abandoned, not stacked).
    // Compare mode fans out to one request per comparison year, in parallel.
    this.dateRequests
      .pipe(
        debounceTime(300),
        takeUntilDestroyed(this.destroyRef),
        switchMap((day) => {
          const dates = this.compareMode() ? this.comparisonDatesFor(day) : [day];
          this.compareDates.set(dates);
          const missing = dates.filter((d) => !this.grids()[d]);
          this.loadingDates.set(new Set(missing));
          // Grids already in the store apply instantly.
          const cachedGrid = this.grids()[day];
          if (cachedGrid) this.sst.set(cachedGrid);
          if (!missing.length) return EMPTY;
          return merge(
            ...missing.map((d) =>
              this.api.getSst(d).pipe(
                map((grid) => ({ day: d, grid })),
                catchError((err: HttpErrorResponse) => {
                  this.snackBar.open(
                    err.status === 404 ? `No SST data for ${d}` : 'Failed to load SST data',
                    undefined,
                    { duration: 3000 },
                  );
                  // Single mode: stay on the last good date.
                  if (!this.compareMode() && d === day) {
                    const good = this.sst()?.date;
                    if (good && this.latest()) {
                      this.dayOffset.set(this.offsetForDate(good));
                    }
                  }
                  return of({ day: d, grid: null });
                }),
              ),
            ),
          );
        }),
      )
      .subscribe(({ day, grid }) => {
        this.loadingDates.update((dates) => {
          const next = new Set(dates);
          next.delete(day);
          return next;
        });
        if (grid) {
          this.grids.update((grids) => ({ ...grids, [day]: grid }));
          this.cachedDates.update((dates) => new Set(dates).add(grid.date));
          // The primary date (first in the list) drives the readouts below the map.
          if (day === this.compareDates()[0]) this.sst.set(grid);
        }
      });
  }

  /** Snap-to-end tolerance: ~6 days. Pixel precision at 945 steps ≈ 1.4
      days/px, so near-extreme drags land exactly on the ends. */
  private static readonly END_SNAP = 6;

  protected onSlider(value: number): void {
    // Slider runs left=oldest -> right=newest (timeline convention);
    // dayOffset stays days-back-from-latest internally, so invert.
    if (value >= 944 - WeatherComponent.END_SNAP) value = 944;
    else if (value <= WeatherComponent.END_SNAP) value = 0;
    this.dayOffset.set(944 - value);
    this.dateRequests.next(this.selectedDate());
  }

  protected jumpToLatest(): void {
    this.dayOffset.set(0);
    this.dateRequests.next(this.selectedDate());
  }

  /** Deterministic single-day step (delta in slider days, + = newer). */
  protected stepDays(delta: number): void {
    const next = Math.min(944, Math.max(0, this.dayOffset() - delta));
    this.dayOffset.set(next);
    this.dateRequests.next(this.selectedDate());
  }

  /** Jump straight to a ruler tick (offset = days back from latest). */
  protected jumpToOffset(offset: number): void {
    this.dayOffset.set(offset);
    this.dateRequests.next(this.selectedDate());
  }

  /** Slider position for the current offset (inverted: 0 = oldest). */
  protected readonly sliderValue = computed(() => 944 - this.dayOffset());

  protected onDatePicked(value: string): void {
    if (!value) return;
    const offset = this.offsetForDate(value);
    // Within slider range -> sync the slider; older -> leave it, show the map anyway.
    if (offset >= 0 && offset <= 944) this.dayOffset.set(offset);
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
    // The timeline anchors on the NRT (near-real-time, preliminary) latest —
    // that is the freshest data NOAA publishes, ~1 day back.
    this.latest.set(info.latest_nrt);
    this.finalLatest.set(info.latest);
    this.cachedDates.set(new Set(info.cached));
  }

  /** True for dates newer than the final product — shown as NRT/preliminary. */
  protected readonly isPreliminary = computed(() => {
    const day = this.displayedDate();
    const final = this.finalLatest();
    return !!day && !!final && day > final;
  });

  protected readonly sliderLabel = (value: number): string => this.dateForOffset(944 - value);

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
