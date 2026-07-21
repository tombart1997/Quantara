import { Component, DestroyRef, OnInit, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { DecimalPipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { EMPTY, Subject, catchError, debounceTime, distinctUntilChanged, switchMap } from 'rxjs';
import * as echarts from 'echarts';
import type { EChartsOption } from 'echarts';
import { NgxEchartsDirective, provideEchartsCore } from 'ngx-echarts';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';

import { ApiService } from '../../core/api.service';
import { GeoPlace, TemperatureAnalysis } from '../../core/api.models';

interface HotspotPlace {
  name: string;
  lat: number;
  lon: number;
}

interface HotspotGroup {
  id: string;
  label: string;
  color: string;
  places: HotspotPlace[];
}

interface PlaceSelection {
  label: string;
  detail: string;
  lat: number;
  lon: number;
  group?: string;
}

interface MarkerDatum {
  value: number[];
  placeLabel: string;
  group: string;
  groupLabel: string;
}

interface MarkerSeries {
  name: string;
  type: string;
  coordinateSystem: string;
  symbolSize: number;
  itemStyle: { color: string; borderColor?: string; borderWidth?: number };
  label: {
    show: boolean;
    position: string;
    fontSize: number;
    color: string;
    formatter: (p: unknown) => string;
  };
  data: MarkerDatum[];
}

const HOTSPOT_GROUPS: HotspotGroup[] = [
  {
    id: 'cocoa',
    label: 'Cocoa',
    color: '#6ec1ff',
    places: [
      { name: 'Abidjan', lat: 5.35, lon: -4.0 },
      { name: 'Kumasi', lat: 6.69, lon: -1.62 },
      { name: 'San Pedro', lat: 4.75, lon: -6.64 },
    ],
  },
  {
    id: 'coffee',
    label: 'Coffee',
    color: '#f48fb1',
    places: [
      { name: 'Minas Gerais', lat: -18.5, lon: -46.0 },
      { name: 'Dak Lak', lat: 12.7, lon: 108.2 },
    ],
  },
  {
    id: 'sugar',
    label: 'Sugar',
    color: '#fbbf24',
    places: [{ name: 'São Paulo', lat: -23.55, lon: -46.63 }],
  },
  {
    id: 'grains',
    label: 'Grains',
    color: '#4ade80',
    places: [
      { name: 'Iowa', lat: 41.88, lon: -93.6 },
      { name: 'Kansas', lat: 38.5, lon: -98.0 },
      { name: 'Odesa', lat: 46.48, lon: 30.72 },
    ],
  },
  {
    id: 'energy',
    label: 'Energy',
    color: '#a78bfa',
    places: [{ name: 'Houston', lat: 29.76, lon: -95.37 }],
  },
];

@Component({
  selector: 'app-temperature',
  imports: [
    DecimalPipe,
    NgxEchartsDirective,
    MatAutocompleteModule,
    MatButtonModule,
    MatCardModule,
    MatCheckboxModule,
    MatChipsModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
  ],
  providers: [provideEchartsCore({ echarts })],
  templateUrl: './temperature.html',
  styleUrl: './temperature.scss',
})
export class TemperatureComponent implements OnInit {
  private readonly api = inject(ApiService);
  private readonly http = inject(HttpClient);
  private readonly snackBar = inject(MatSnackBar);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly groups = HOTSPOT_GROUPS;
  protected readonly activeGroups = signal<Set<string>>(
    new Set(HOTSPOT_GROUPS.map((g) => g.id)),
  );

  protected readonly mapReady = signal(false);
  protected readonly mapOptions = computed<EChartsOption | null>(() => {
    if (!this.mapReady()) return null;
    const series: MarkerSeries[] = HOTSPOT_GROUPS.filter((g) => this.activeGroups().has(g.id)).map((g) => ({
      name: g.label,
      type: 'scatter',
      coordinateSystem: 'geo',
      symbolSize: 10,
      itemStyle: { color: g.color },
      label: {
        show: true,
        position: 'right',
        fontSize: 10,
        color: 'rgba(255, 255, 255, 0.75)',
        formatter: (p: unknown) => (p as { data: { placeLabel: string } }).data.placeLabel,
      },
      data: g.places.map((p) => ({
        value: [p.lon, p.lat],
        placeLabel: p.name,
        group: g.id,
        groupLabel: g.label,
      })),
    }));
    if (this.userCities().length) {
      series.push({
        name: 'Cities',
        type: 'scatter',
        coordinateSystem: 'geo',
        symbolSize: 10,
        itemStyle: { color: '#6ec1ff', borderColor: '#e8eef4', borderWidth: 1 },
        label: {
          show: true,
          position: 'right',
          fontSize: 10,
          color: '#6ec1ff',
          formatter: (p: unknown) => (p as { data: { placeLabel: string } }).data.placeLabel,
        },
        data: this.userCities().map((c) => ({
          value: [c.lon, c.lat],
          placeLabel: c.name,
          group: '',
          groupLabel: '',
        })),
      });
    }
    return {
      backgroundColor: '#0c121b',
      tooltip: {
        backgroundColor: '#1a2433',
        borderColor: 'rgba(255, 255, 255, 0.12)',
        textStyle: { color: '#e6edf5' },
        formatter: (params: unknown) => {
          const p = params as { seriesType?: string; name?: string; data?: unknown };
          if (p.seriesType === 'scatter' && p.data) {
            const d = p.data as { placeLabel: string; groupLabel?: string };
            return d.groupLabel ? `${d.placeLabel} (${d.groupLabel})` : d.placeLabel;
          }
          return p.name ?? '';
        },
      },
      geo: {
        map: 'world',
        roam: true,
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
      series: series as EChartsOption['series'],
    } as EChartsOption;
  });

  // --- City search -------------------------------------------------------------

  protected readonly geocodeResults = signal<GeoPlace[]>([]);
  protected readonly userCities = signal<{ name: string; lat: number; lon: number }[]>([]);
  private readonly querySubject = new Subject<string>();

  // --- Analysis panel -------------------------------------------------------------

  protected readonly selected = signal<PlaceSelection | null>(null);
  protected readonly analysis = signal<TemperatureAnalysis | null>(null);
  protected readonly analysisLoading = signal(false);

  protected readonly analysisOptions = computed<EChartsOption | null>(() => {
    const a = this.analysis();
    return a ? this.buildAnalysisOptions(a) : null;
  });

  ngOnInit(): void {
    this.http.get('assets/countries.geo.json').subscribe((geo) => {
      echarts.registerMap('world', geo as Parameters<typeof echarts.registerMap>[1]);
      this.mapReady.set(true);
    });

    this.querySubject
      .pipe(
        debounceTime(300),
        distinctUntilChanged(),
        takeUntilDestroyed(this.destroyRef),
        switchMap((q) =>
          q.trim().length >= 2
            ? this.api.geocodePlace(q.trim()).pipe(catchError(() => EMPTY))
            : EMPTY,
        ),
      )
      .subscribe((places) => this.geocodeResults.set(places));
  }

  protected onQuery(value: string): void {
    if (value.trim().length < 2) this.geocodeResults.set([]);
    this.querySubject.next(value);
  }

  protected onPlaceSelected(place: GeoPlace): void {
    if (!this.userCities().some((c) => c.lat === place.lat && c.lon === place.lon)) {
      this.userCities.update((cities) => [
        ...cities,
        { name: place.name, lat: place.lat, lon: place.lon },
      ]);
    }
    this.loadAnalysis({
      label: place.name,
      detail: [place.admin1, place.country].filter(Boolean).join(', '),
      lat: place.lat,
      lon: place.lon,
    });
  }

  protected removeCity(city: { name: string; lat: number; lon: number }): void {
    this.userCities.update((cities) => cities.filter((c) => c !== city));
  }

  protected placeLabel(place: GeoPlace): string {
    return [place.name, place.admin1, place.country].filter(Boolean).join(', ');
  }

  protected toggleGroup(id: string, checked: boolean): void {
    this.activeGroups.update((groups) => {
      const next = new Set(groups);
      if (checked) {
        next.add(id);
      } else {
        next.delete(id);
      }
      return next;
    });
  }

  protected onMapClick(params: unknown): void {
    const p = params as { seriesType?: string; data?: unknown };
    if (p.seriesType !== 'scatter' || !p.data) return;
    const d = p.data as { value: number[]; placeLabel: string; groupLabel?: string };
    this.loadAnalysis({
      label: d.placeLabel,
      detail: d.groupLabel ?? 'pinned city',
      lat: d.value[1],
      lon: d.value[0],
      group: d.groupLabel,
    });
  }

  protected closeAnalysis(): void {
    this.selected.set(null);
    this.analysis.set(null);
  }

  private loadAnalysis(place: PlaceSelection): void {
    this.selected.set(place);
    this.analysis.set(null);
    this.analysisLoading.set(true);
    this.api.getTemperatureAnalysis(place.lat, place.lon).subscribe({
      next: (a) => {
        this.analysis.set(a);
        this.analysisLoading.set(false);
      },
      error: () => {
        this.analysisLoading.set(false);
        this.snackBar.open('Failed to load temperature analysis', undefined, { duration: 3000 });
      },
    });
  }

  // --- Analysis chart --------------------------------------------------------------

  private buildAnalysisOptions(a: TemperatureAnalysis): EChartsOption {
    const pair = (date: string, value: number): [string, number] => [date, value];
    const band = (
      name: string,
      stack: string,
      lower: [string, number][],
      delta: [string, number][],
      color: string,
      opacity: number,
    ) => [
      {
        name: `${name} band`,
        type: 'line',
        stack,
        data: lower,
        symbol: 'none',
        silent: true,
        lineStyle: { opacity: 0 },
      },
      {
        name: `${name} band`,
        type: 'line',
        stack,
        data: delta,
        symbol: 'none',
        silent: true,
        lineStyle: { opacity: 0 },
        areaStyle: { color, opacity },
      },
    ];
    const today = new Date().toISOString().slice(0, 10);
    return {
      backgroundColor: 'transparent',
      textStyle: { color: '#9aa7b8' },
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#1a2433',
        borderColor: 'rgba(255, 255, 255, 0.12)',
        textStyle: { color: '#e6edf5' },
        formatter: (params: unknown) => {
          const list = params as { seriesName: string; marker: string; value: [string, number] }[];
          const date = list[0]?.value?.[0] ?? '';
          const lines = list
            .filter((p) => !p.seriesName.endsWith(' band') && p.value?.[1] != null)
            .map((p) => `${p.marker} ${p.seriesName}: ${p.value[1].toFixed(1)}°C`);
          return [date, ...lines].join('<br>');
        },
      },
      legend: {
        data: ['History', 'Forecast ±1σ', 'Climatology ±1σ'],
        bottom: 0,
        textStyle: { color: '#9aa7b8' },
      },
      grid: { left: 50, right: 20, top: 20, bottom: 50 },
      xAxis: { type: 'time', axisLine: { lineStyle: { color: '#3a4a5f' } } },
      yAxis: {
        type: 'value',
        scale: true,
        axisLabel: { formatter: '{value}°C', color: '#9aa7b8' },
        splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.06)' } },
      },
      series: [
        ...band(
          'History',
          'hb',
          a.history.map((h) => pair(h.date, h.min)),
          a.history.map((h) => pair(h.date, h.max - h.min)),
          '#6ec1ff',
          0.15,
        ),
        ...band(
          'Forecast ±1σ',
          'fb',
          a.forecast.map((f) => pair(f.date, f.mean - f.spread)),
          a.forecast.map((f) => pair(f.date, 2 * f.spread)),
          '#fbbf24',
          0.2,
        ),
        ...band(
          'Climatology ±1σ',
          'cb',
          a.climatology.map((c) => pair(c.date, c.mean - c.std)),
          a.climatology.map((c) => pair(c.date, 2 * c.std)),
          '#9aa7b8',
          0.1,
        ),
        {
          name: 'History',
          type: 'line',
          data: a.history.map((h) => pair(h.date, h.mean)),
          symbol: 'none',
          lineStyle: { color: '#6ec1ff', width: 2 },
          itemStyle: { color: '#6ec1ff' },
          markLine: {
            symbol: 'none',
            silent: true,
            label: { show: false },
            lineStyle: { color: 'rgba(255, 255, 255, 0.35)', type: 'dashed' },
            data: [{ xAxis: today }],
          },
        },
        {
          name: 'Forecast ±1σ',
          type: 'line',
          data: a.forecast.map((f) => pair(f.date, f.mean)),
          symbol: 'none',
          lineStyle: { color: '#fbbf24', width: 2, type: 'dashed' },
          itemStyle: { color: '#fbbf24' },
        },
        {
          name: 'Climatology ±1σ',
          type: 'line',
          data: a.climatology.map((c) => pair(c.date, c.mean)),
          symbol: 'none',
          lineStyle: { color: '#9aa7b8', width: 1.5, type: 'dotted' },
          itemStyle: { color: '#9aa7b8' },
        },
      ] as EChartsOption['series'],
    } as EChartsOption;
  }
}
