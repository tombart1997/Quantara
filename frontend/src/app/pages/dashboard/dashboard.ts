import { DatePipe, DecimalPipe } from '@angular/common';
import { Component, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTableModule } from '@angular/material/table';

import { ApiService } from '../../core/api.service';
import { Asset, AssetType, EventType, Signal } from '../../core/api.models';

interface AssetGroup {
  type: AssetType;
  label: string;
  icon: string;
  assets: Asset[];
}

const ASSET_TYPE_META: Record<AssetType, { label: string; icon: string }> = {
  STOCK: { label: 'Stocks', icon: 'show_chart' },
  COMMODITY: { label: 'Commodities', icon: 'eco' },
  ETF: { label: 'ETFs', icon: 'account_balance' },
  INDEX: { label: 'Indexes', icon: 'public' },
};

@Component({
  selector: 'app-dashboard',
  imports: [
    DatePipe,
    DecimalPipe,
    RouterLink,
    MatCardModule,
    MatChipsModule,
    MatExpansionModule,
    MatIconModule,
    MatListModule,
    MatProgressBarModule,
    MatTableModule,
  ],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
})
export class DashboardComponent {
  private readonly api = inject(ApiService);

  protected readonly data = toSignal(this.api.getDashboard());
  protected readonly allAssets = toSignal(this.api.getAssets(), { initialValue: [] });

  protected readonly assetGroups = computed<AssetGroup[]>(() => {
    const assets = this.allAssets();
    return (Object.keys(ASSET_TYPE_META) as AssetType[])
      .map((type) => ({
        type,
        ...ASSET_TYPE_META[type],
        assets: assets.filter((a) => a.asset_type === type),
      }))
      .filter((group) => group.assets.length > 0);
  });

  protected readonly watchlistColumns = ['ticker', 'name', 'latest_close', 'change_pct'];

  protected scoreColor(signal: Signal): string {
    if (signal.score >= 70) return 'score-high';
    if (signal.score >= 40) return 'score-mid';
    return 'score-low';
  }

  protected formatType(type: EventType): string {
    return type.replace(/_/g, ' ').toLowerCase();
  }
}
