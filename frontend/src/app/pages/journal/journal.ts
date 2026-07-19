import { DatePipe, DecimalPipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { Subject, startWith, switchMap } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialog } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';

import { ApiService } from '../../core/api.service';
import { ThesisReviewItem } from '../../core/api.models';
import type { AiConsultData } from '../../ai-consult/ai-consult';
import { JournalEntryDialogComponent } from './journal-entry-dialog';

@Component({
  selector: 'app-journal',
  imports: [
    DatePipe,
    DecimalPipe,
    RouterLink,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatFormFieldModule,
    MatIconModule,
    MatMenuModule,
    MatSelectModule,
    MatTooltipModule,
  ],
  templateUrl: './journal.html',
  styleUrl: './journal.scss',
})
export class JournalComponent {
  private readonly api = inject(ApiService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);

  protected readonly assets = toSignal(this.api.getAssets(), { initialValue: [] });

  /** Selected ticker filter; null = all assets. */
  protected readonly filter = signal<string | null>(null);

  private readonly refreshReview = new Subject<void>();
  protected readonly review = toSignal(
    this.refreshReview.pipe(
      startWith(void 0),
      switchMap(() => this.api.getThesisReview()),
    ),
    { initialValue: [] },
  );

  protected readonly filtered = computed(() => {
    const ticker = this.filter();
    const items = this.review();
    return ticker ? items.filter((i) => i.asset_ticker === ticker) : items;
  });

  /** The item whose delete menu is open. */
  protected readonly activeItem = signal<ThesisReviewItem | null>(null);

  protected openAddEntry(): void {
    this.dialog
      .open(JournalEntryDialogComponent, { width: '560px', maxWidth: '95vw' })
      .afterClosed()
      .subscribe((entry) => {
        if (!entry) return;
        this.snackBar.open('Entry added', undefined, { duration: 2500 });
        this.refreshReview.next();
      });
  }

  protected reviewWithAi(item: ThesisReviewItem): void {
    const entry = item.entry;
    const change =
      item.change_pct != null
        ? `${item.change_pct > 0 ? '+' : ''}${item.change_pct.toFixed(2)}`
        : 'n/a';
    const data: AiConsultData = {
      ticker: item.asset_ticker ?? undefined,
      question:
        `Is this thesis still supported by the current data? ` +
        `Thesis (${entry.date}): "${entry.thesis}" ` +
        `Expected: ${entry.expected_outcome ?? '-'}. Risk: ${entry.risk ?? '-'}. ` +
        `Confidence was ${entry.confidence}/10. Price has moved ${change}% since.`,
    };
    // Lazy-load, same as the FAB in the app shell.
    import('../../ai-consult/ai-consult').then((m) =>
      this.dialog.open(m.AiConsultComponent, { width: '640px', maxWidth: '95vw', data }),
    );
  }

  protected deleteEntry(item: ThesisReviewItem): void {
    this.api.deleteJournalEntry(item.entry.id).subscribe(() => {
      this.snackBar.open('Entry deleted', undefined, { duration: 2500 });
      this.refreshReview.next();
    });
  }
}
