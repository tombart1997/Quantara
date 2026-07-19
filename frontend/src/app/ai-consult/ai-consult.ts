import { Component, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ClipboardModule } from '@angular/cdk/clipboard';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';

import { ApiService } from '../core/api.service';
import { AiConsultResponse } from '../core/api.models';

@Component({
  selector: 'app-ai-consult',
  imports: [
    FormsModule,
    ClipboardModule,
    MatButtonModule,
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

  /** Preselected from /assets/:ticker when the dialog opens on an asset page. */
  protected readonly ticker = signal<string | null>(this.tickerFromUrl());
  protected readonly question = signal('');

  protected readonly result = signal<AiConsultResponse | null>(null);
  protected readonly loading = signal(false);

  protected consult(): void {
    if (this.loading()) return;
    this.loading.set(true);
    this.result.set(null);
    this.api.aiConsult(this.ticker(), this.question().trim() || null).subscribe({
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
