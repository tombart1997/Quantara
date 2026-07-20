import { DecimalPipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatChipsModule } from '@angular/material/chips';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSliderModule } from '@angular/material/slider';
import { MatSnackBar } from '@angular/material/snack-bar';

import { ApiService } from '../../core/api.service';
import { RippleExposure, RippleSignal, RippleState } from '../../core/api.models';

@Component({
  selector: 'app-ripple',
  imports: [
    DecimalPipe,
    RouterLink,
    MatButtonModule,
    MatCardModule,
    MatCheckboxModule,
    MatChipsModule,
    MatExpansionModule,
    MatIconModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    MatSliderModule,
  ],
  templateUrl: './ripple.html',
  styleUrl: './ripple.scss',
})
export class RippleComponent implements OnInit {
  private readonly api = inject(ApiService);
  private readonly snackBar = inject(MatSnackBar);

  protected readonly state = signal<RippleState | null>(null);
  protected readonly loading = signal(true);
  protected readonly scenarioRunning = signal(false);
  /** True while the displayed state comes from a scenario run, not live data. */
  protected readonly scenarioMode = signal(false);

  protected readonly selectedSignalId = signal<string | null>(null);

  protected readonly activeSignals = computed(() =>
    (this.state()?.signals ?? [])
      .filter((s) => s.active)
      .sort((a, b) => b.propagation_strength - a.propagation_strength),
  );
  protected readonly dormantSignals = computed(() =>
    (this.state()?.signals ?? []).filter((s) => !s.active),
  );

  protected readonly selectedSignal = computed(
    () => (this.state()?.signals ?? []).find((s) => s.id === this.selectedSignalId()) ?? null,
  );

  protected readonly beneficiaries = computed(() =>
    (this.selectedSignal()?.exposure ?? [])
      .filter((e) => e.impact > 0)
      .sort((a, b) => b.impact - a.impact),
  );
  protected readonly victims = computed(() =>
    (this.selectedSignal()?.exposure ?? [])
      .filter((e) => e.impact < 0)
      .sort((a, b) => a.impact - b.impact),
  );

  protected readonly topAssets = computed(() =>
    [...(this.state()?.assets ?? [])]
      .sort((a, b) => Math.abs(b.net_score) - Math.abs(a.net_score))
      .slice(0, 10),
  );

  // --- Scenario builder --------------------------------------------------------

  protected readonly scenarioSelection = signal<Set<string>>(new Set());
  protected readonly scenarioValues = signal<Record<string, number>>({});

  protected readonly canRunScenario = computed(
    () => this.scenarioSelection().size > 0 && !this.scenarioRunning(),
  );

  ngOnInit(): void {
    this.loadLive();
  }

  protected loadLive(): void {
    this.loading.set(true);
    this.api.getRippleState().subscribe({
      next: (state) => {
        this.state.set(state);
        this.scenarioMode.set(false);
        this.loading.set(false);
        this.selectFirstSignal(state);
      },
      error: () => {
        this.loading.set(false);
        this.snackBar.open('Failed to load ripple state', undefined, { duration: 3000 });
      },
    });
  }

  protected selectSignal(id: string): void {
    this.selectedSignalId.set(id);
  }

  protected toggleScenarioSignal(id: string, checked: boolean): void {
    this.scenarioSelection.update((selected) => {
      const next = new Set(selected);
      if (checked) {
        next.add(id);
      } else {
        next.delete(id);
      }
      return next;
    });
  }

  protected setScenarioValue(id: string, value: number): void {
    this.scenarioValues.update((values) => ({ ...values, [id]: value }));
  }

  protected runScenario(): void {
    if (!this.canRunScenario()) return;
    this.scenarioRunning.set(true);
    const activations: Record<string, number> = {};
    for (const id of this.scenarioSelection()) {
      activations[id] = this.scenarioValues()[id] ?? 50;
    }
    this.api.runRippleScenario(activations).subscribe({
      next: (state) => {
        this.scenarioRunning.set(false);
        this.state.set(state);
        this.scenarioMode.set(true);
        this.selectFirstSignal(state);
      },
      error: () => {
        this.scenarioRunning.set(false);
        this.snackBar.open('Scenario run failed', undefined, { duration: 3000 });
      },
    });
  }

  private selectFirstSignal(state: RippleState): void {
    const current = this.selectedSignalId();
    if (current && state.signals.some((s) => s.id === current && s.active)) return;
    const first = [...state.signals]
      .filter((s) => s.active)
      .sort((a, b) => b.propagation_strength - a.propagation_strength)[0];
    this.selectedSignalId.set(first?.id ?? null);
  }

  // --- Display helpers -----------------------------------------------------------

  protected ordinal(order: number): string {
    return order === 1 ? '1st' : order === 2 ? '2nd' : '3rd';
  }

  protected orderClass(order: number): string {
    return `order-${order}`;
  }

  protected signed(value: number, decimals = 2): string {
    return `${value > 0 ? '+' : ''}${value.toFixed(decimals)}`;
  }

  protected pricedInCrowded(exposure: RippleExposure): boolean {
    return exposure.priced_in != null && exposure.priced_in >= 0.7;
  }

  /** Short source label for the priced-in chip, e.g. "CFTC COT" -> "COT". */
  protected crowdSuffix(exposure: RippleExposure): string {
    if (!exposure.crowd_source) return '';
    return ` · ${exposure.crowd_source === 'CFTC COT' ? 'COT' : exposure.crowd_source}`;
  }

  /** Tag for the data feed behind an activation detector, if recognizable. */
  protected activationTag(signal: RippleSignal): { label: string; class: string } | null {
    if (signal.activation_detail.startsWith('NOAA CPC status:')) {
      return { label: 'official data', class: 'tag-official' };
    }
    if (signal.activation_detail.startsWith('narrative intensity:')) {
      return { label: 'news volume', class: 'tag-news' };
    }
    return null;
  }
}
