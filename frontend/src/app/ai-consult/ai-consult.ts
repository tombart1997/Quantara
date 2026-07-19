import { Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ClipboardModule } from '@angular/cdk/clipboard';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';

import { ApiService } from '../core/api.service';
import { AiConsultResponse, EventType, MarketEvent } from '../core/api.models';

type ConsultMode = 'asset' | 'cross';

const MAX_EVENTS = 20;

@Component({
  selector: 'app-ai-consult',
  imports: [
    FormsModule,
    ClipboardModule,
    MatButtonModule,
    MatButtonToggleModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSelectModule,
  ],
  templateUrl: './ai-consult.html',
  styleUrl: './ai-consult.scss',
})
export class AiConsultComponent {
  private readonly api = inject(ApiService);
  private readonly router = inject(Router);
  private readonly snackBar = inject(MatSnackBar);

  protected readonly assets = toSignal(this.api.getAssets(), { initialValue: [] });
  protected readonly status = toSignal(this.api.getAiStatus());

  protected readonly mode = signal<ConsultMode>('asset');

  // Asset consult mode: null = portfolio overview.
  protected readonly ticker = signal<string | null>(this.tickerFromUrl());

  // Cross-reference mode: target asset is required, preselected from the route.
  protected readonly crossTicker = signal<string | null>(this.tickerFromUrl());
  protected readonly selectedEventIds = signal<number[]>([]);

  protected readonly events = toSignal(this.api.getEvents(), { initialValue: [] });
  protected readonly sortedEvents = computed(() =>
    [...this.events()].sort((a, b) => a.date.localeCompare(b.date)),
  );

  protected readonly question = signal('');

  protected readonly result = signal<AiConsultResponse | null>(null);
  protected readonly loading = signal(false);

  protected readonly canSubmit = computed(() => {
    if (this.mode() === 'asset') return true; // null ticker = portfolio overview
    return this.crossTicker() !== null && this.selectedEventIds().length > 0;
  });

  protected eventLabel(event: MarketEvent): string {
    const date = event.date.slice(0, 10);
    const ticker = event.asset_ticker ?? 'MACRO';
    return `${date} · ${ticker} · ${event.title} (${this.formatType(event.event_type)})`;
  }

  protected onEventSelection(ids: number[]): void {
    // Cap the selection at the API limit.
    this.selectedEventIds.set(ids.slice(0, MAX_EVENTS));
  }

  protected consult(): void {
    if (this.loading() || !this.canSubmit()) return;
    this.loading.set(true);
    this.result.set(null);
    const question = this.question().trim() || null;
    const cross = this.mode() === 'cross';
    this.api
      .aiConsult(
        cross ? this.crossTicker() : this.ticker(),
        question,
        cross ? this.selectedEventIds() : null,
      )
      .subscribe({
        next: (res) => {
          this.result.set(res);
          this.loading.set(false);
        },
        error: () => this.loading.set(false),
      });
  }

  protected copied(): void {
    this.snackBar.open('Copied!', undefined, { duration: 2000 });
  }

  private formatType(type: EventType): string {
    return type.replace(/_/g, ' ').toLowerCase();
  }

  private tickerFromUrl(): string | null {
    const match = /^\/assets\/([^/?]+)/.exec(this.router.url);
    return match ? match[1] : null;
  }
}
