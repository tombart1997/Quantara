import { DatePipe, DecimalPipe } from '@angular/common';
import { Component, DestroyRef, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { EMPTY, Subject, catchError, interval, startWith, switchMap, takeWhile } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';

import { ApiService } from '../../core/api.service';
import { Asset, AssetType, EventType, FxMatrix, RefreshStatus, Signal } from '../../core/api.models';
import { SparklineComponent } from '../../shared/sparkline';

interface AssetGroup {
  type: AssetType;
  label: string;
  icon: string;
  assets: Asset[];
  leveragedAssets: Asset[];
}

const ASSET_TYPE_META: Record<AssetType, { label: string; icon: string }> = {
  STOCK: { label: 'Stocks', icon: 'show_chart' },
  COMMODITY: { label: 'Commodities', icon: 'eco' },
  ETF: { label: 'ETFs', icon: 'account_balance' },
  INDEX: { label: 'Indexes', icon: 'public' },
};

/** Leveraged products belong to the class of what they track, not "ETF". */
const LEVERAGED_SECTOR_PARENT: Record<string, AssetType> = {
  'Leveraged Single Stock': 'STOCK',
  'Leveraged Broad Market': 'INDEX',
  'Leveraged Energy': 'COMMODITY',
  'Leveraged Metals': 'COMMODITY',
};

@Component({
  selector: 'app-dashboard',
  imports: [
    DatePipe,
    DecimalPipe,
    RouterLink,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatExpansionModule,
    MatIconModule,
    MatListModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    MatTableModule,
    MatTooltipModule,
    SparklineComponent,
  ],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
})
export class DashboardComponent implements OnInit, OnDestroy {
  private readonly api = inject(ApiService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly destroyRef = inject(DestroyRef);

  private readonly reloadData = new Subject<void>();
  protected readonly data = toSignal(
    this.reloadData.pipe(
      startWith(void 0),
      switchMap(() => this.api.getDashboard()),
    ),
  );
  protected readonly allAssets = toSignal(this.api.getAssets(), { initialValue: [] });
  protected readonly sparklines = toSignal(this.api.getSparklines(30), {
    initialValue: {} as Record<string, number[]>,
  });

  // Data freshness: poll the refresh status, faster while a refresh is running.
  protected readonly status = signal<RefreshStatus | null>(null);
  protected readonly manualRefreshing = signal(false);
  protected readonly refreshing = computed(
    () => this.manualRefreshing() || (this.status()?.running ?? false),
  );

  ngOnInit(): void {
    this.loadStatus();
    // FX matrix: poll every second; on failure keep showing the last good
    // matrix. The backend caches 5s, so this is live without hammering Yahoo.
    interval(1_000)
      .pipe(
        startWith(0),
        takeUntilDestroyed(this.destroyRef),
        switchMap(() => this.api.getFxMatrix().pipe(catchError(() => EMPTY))),
      )
      .subscribe((matrix) => this.onFxMatrix(matrix));
  }

  // --- FX matrix ------------------------------------------------------------

  protected readonly fx = signal<FxMatrix | null>(null);
  /** Cells ("ROW:COL") currently flashing: direction + 0..1 intensity. */
  protected readonly fxFlash = signal<Record<string, { dir: 'up' | 'down'; intensity: number }>>({});
  private prevFxRates: Record<string, Record<string, number>> = {};
  private flashTimer: ReturnType<typeof setTimeout> | null = null;

  private onFxMatrix(matrix: FxMatrix): void {
    const changes: Record<string, { dir: 'up' | 'down'; intensity: number }> = {};
    for (const row of matrix.currencies) {
      for (const col of matrix.currencies) {
        if (row === col) continue;
        const prev = this.prevFxRates[row]?.[col];
        const next = matrix.rates[row]?.[col];
        if (prev !== undefined && next !== undefined && prev !== next) {
          // Intensity: 0.05% move between polls = full saturation.
          const deltaPct = Math.abs(next / prev - 1) * 100;
          changes[`${row}:${col}`] = {
            dir: next > prev ? 'up' : 'down',
            intensity: Math.min(1, deltaPct / 0.05),
          };
        }
      }
    }
    this.prevFxRates = matrix.rates;
    this.fx.set(matrix);
    if (Object.keys(changes).length > 0) {
      this.fxFlash.set(changes);
      if (this.flashTimer) clearTimeout(this.flashTimer);
      this.flashTimer = setTimeout(() => this.fxFlash.set({}), 900);
    }
  }

  ngOnDestroy(): void {
    if (this.flashTimer) clearTimeout(this.flashTimer);
  }

  protected fxRate(m: FxMatrix, row: string, col: string): number | undefined {
    return m.rates[row]?.[col];
  }

  protected formatFxRate(value: number | undefined): string {
    if (value === undefined) return '—';
    return value >= 100 ? value.toFixed(2) : value.toFixed(4);
  }

  protected fxMarker(m: FxMatrix, row: string, col: string): string {
    const change = m.changes_pct[row]?.[col];
    if (change == null || change === 0) return '';
    return change > 0 ? '▲' : '▼';
  }

  protected fxCellClass(m: FxMatrix, row: string, col: string): string {
    const classes: string[] = [];
    const change = m.changes_pct[row]?.[col];
    if (change != null && change > 0) classes.push('fx-up');
    if (change != null && change < 0) classes.push('fx-down');
    return classes.join(' ');
  }

  /** Flash background: direction color, alpha scaled by move intensity. */
  protected fxCellBg(row: string, col: string): string | null {
    const flash = this.fxFlash()[`${row}:${col}`];
    if (!flash) return null;
    const alpha = 0.1 + 0.35 * flash.intensity;
    return flash.dir === 'up'
      ? `rgba(74, 222, 128, ${alpha.toFixed(2)})`
      : `rgba(248, 113, 113, ${alpha.toFixed(2)})`;
  }

  // --- Refresh status ---------------------------------------------------------

  private loadStatus(): void {
    this.api
      .getRefreshStatus()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((status) => {
        const wasRunning = this.status()?.running ?? false;
        this.status.set(status);
        if (status.running) {
          this.startPolling();
        } else if (wasRunning) {
          // A running refresh (manual or the 30-min auto job) just finished.
          this.reloadData.next();
        }
      });
  }

  private polling = false;
  private startPolling(): void {
    if (this.polling) return;
    this.polling = true;
    interval(10_000)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        switchMap(() => this.api.getRefreshStatus()),
        // Inclusive: emit the final not-running status, then complete the stream.
        takeWhile((status) => status.running, true),
      )
      .subscribe((status) => {
        this.status.set(status);
        if (!status.running) {
          this.polling = false;
          this.reloadData.next();
        }
      });
  }

  protected refresh(): void {
    if (this.refreshing()) return;
    this.manualRefreshing.set(true);
    this.api.refreshAll().subscribe({
      next: () => {
        this.manualRefreshing.set(false);
        this.loadStatus();
        this.reloadData.next();
        this.snackBar.open('Data refreshed', undefined, { duration: 2500 });
      },
      error: () => {
        this.manualRefreshing.set(false);
        this.loadStatus();
        this.snackBar.open('Refresh failed', undefined, { duration: 3000 });
      },
    });
  }

  protected freshnessLabel(): string {
    const lastRun = this.status()?.last_run;
    if (!lastRun) return 'No refresh yet';
    const ageMs = Date.now() - new Date(lastRun).getTime();
    const minutes = Math.floor(ageMs / 60_000);
    if (minutes < 1) return 'Updated just now';
    if (minutes < 60) return `Updated ${minutes} min ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `Updated ${hours} h ago`;
    return `Updated ${new Date(lastRun).toLocaleDateString()}`;
  }

  protected readonly assetGroups = computed<AssetGroup[]>(() => {
    const assets = this.allAssets();
    // Leveraged products leave their asset_type group and join the class of
    // their underlying (e.g. UCO is an ETF structurally, a leveraged
    // commodity conceptually).
    const parentOf = (a: Asset): AssetType =>
      a.leverage !== 1 && a.sector && LEVERAGED_SECTOR_PARENT[a.sector]
        ? LEVERAGED_SECTOR_PARENT[a.sector]
        : a.asset_type;
    return (Object.keys(ASSET_TYPE_META) as AssetType[])
      .map((type) => ({
        type,
        ...ASSET_TYPE_META[type],
        assets: assets.filter((a) => a.leverage === 1 && a.asset_type === type),
        leveragedAssets: assets.filter((a) => a.leverage !== 1 && parentOf(a) === type),
      }))
      .filter((group) => group.assets.length > 0 || group.leveragedAssets.length > 0);
  });

  protected readonly watchlistColumns = ['ticker', 'name', 'latest_close', 'change_pct', 'watchlist'];

  protected toggleWatchlist(ticker: string): void {
    this.api.toggleWatchlist(ticker).subscribe(() => this.reloadData.next());
  }

  protected scoreColor(signal: Signal): string {
    if (signal.score >= 70) return 'score-high';
    if (signal.score >= 40) return 'score-mid';
    return 'score-low';
  }

  protected formatType(type: EventType): string {
    return type.replace(/_/g, ' ').toLowerCase();
  }
}
