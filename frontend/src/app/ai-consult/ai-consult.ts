import { Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ClipboardModule } from '@angular/cdk/clipboard';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';

import { ApiService } from '../core/api.service';
import { AiConsultResponse } from '../core/api.models';

type ConsultMode = 'asset' | 'cross';

@Component({
  selector: 'app-ai-consult',
  imports: [
    FormsModule,
    ClipboardModule,
    MatButtonModule,
    MatButtonToggleModule,
    MatCheckboxModule,
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
  protected readonly indicators = toSignal(this.api.getIndicators(), { initialValue: [] });

  protected readonly mode = signal<ConsultMode>('asset');

  // Asset consult mode: null = portfolio overview.
  protected readonly ticker = signal<string | null>(this.tickerFromUrl());

  // Cross-reference mode: target asset is required, preselected from the route.
  protected readonly crossTicker = signal<string | null>(this.tickerFromUrl());
  protected readonly selectedIndicators = signal<Set<string>>(new Set());

  protected readonly question = signal('');

  protected readonly result = signal<AiConsultResponse | null>(null);
  protected readonly loading = signal(false);

  protected readonly canSubmit = computed(() => {
    if (this.mode() === 'asset') return true; // null ticker = portfolio overview
    return this.crossTicker() !== null && this.selectedIndicators().size > 0;
  });

  protected toggleIndicator(id: string, checked: boolean): void {
    this.selectedIndicators.update((selected) => {
      const next = new Set(selected);
      if (checked) {
        next.add(id);
      } else {
        next.delete(id);
      }
      return next;
    });
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
        cross ? [...this.selectedIndicators()] : null,
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

  private tickerFromUrl(): string | null {
    const match = /^\/assets\/([^/?]+)/.exec(this.router.url);
    return match ? match[1] : null;
  }
}
