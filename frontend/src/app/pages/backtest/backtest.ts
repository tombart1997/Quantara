import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';

import { ApiService } from '../../core/api.service';
import { BacktestAsset, BacktestResult, HorizonStats } from '../../core/api.models';

interface AssetRuleRow {
  rule: string;
  title: string;
  per: Record<string, HorizonStats>;
}

@Component({
  selector: 'app-backtest',
  imports: [
    DecimalPipe,
    RouterLink,
    MatCardModule,
    MatChipsModule,
    MatFormFieldModule,
    MatProgressSpinnerModule,
    MatSelectModule,
  ],
  templateUrl: './backtest.html',
  styleUrl: './backtest.scss',
})
export class BacktestComponent implements OnInit {
  private readonly api = inject(ApiService);
  private readonly snackBar = inject(MatSnackBar);

  protected readonly result = signal<BacktestResult | null>(null);
  protected readonly loading = signal(true);

  protected readonly tickerFilter = signal<string | null>(null);

  protected readonly horizons = computed(() => this.result()?.horizons ?? []);

  /** Rule with the best delta at the longest horizon — the "strongest" badge. */
  protected readonly strongestRule = computed(() => {
    const rules = this.result()?.rules ?? [];
    const last = String(this.horizons().at(-1) ?? 20);
    let best: string | null = null;
    let bestDelta = -Infinity;
    for (const rule of rules) {
      const delta = rule.per_horizon[last]?.delta_vs_baseline;
      if (delta != null && delta > bestDelta) {
        bestDelta = delta;
        best = rule.rule;
      }
    }
    return best;
  });

  protected readonly assetTickers = computed(
    () => (this.result()?.assets ?? []).map((a) => a.ticker),
  );

  protected readonly filteredAssets = computed(() => {
    const assets = this.result()?.assets ?? [];
    const ticker = this.tickerFilter();
    return ticker ? assets.filter((a) => a.ticker === ticker) : assets;
  });

  ngOnInit(): void {
    this.api.getBacktest().subscribe({
      next: (result) => {
        this.result.set(result);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.snackBar.open('Failed to load backtest', undefined, { duration: 3000 });
      },
    });
  }

  protected hkey(horizon: number): string {
    return String(horizon);
  }

  protected lastHorizon(): string {
    return String(this.horizons().at(-1) ?? 20);
  }

  protected assetRules(asset: BacktestAsset): AssetRuleRow[] {
    const titles = new Map((this.result()?.rules ?? []).map((r) => [r.rule, r.title]));
    return Object.entries(asset.rules).map(([rule, per]) => ({
      rule,
      title: titles.get(rule) ?? rule,
      per,
    }));
  }

  protected signed(value: number): string {
    return `${value > 0 ? '+' : ''}${value.toFixed(2)}`;
  }

  /** Green above baseline, red below, amber in the ±0.25 noise zone. */
  protected deltaClass(delta: number): string {
    if (Math.abs(delta) < 0.25) return 'noise';
    return delta > 0 ? 'positive' : 'negative';
  }
}
