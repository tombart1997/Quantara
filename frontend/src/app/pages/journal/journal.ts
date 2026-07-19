import { Component, inject, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { switchMap } from 'rxjs';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';

import { ApiService } from '../../core/api.service';

@Component({
  selector: 'app-journal',
  imports: [DatePipe, RouterLink, MatFormFieldModule, MatSelectModule, MatTableModule],
  templateUrl: './journal.html',
  styleUrl: './journal.scss',
})
export class JournalComponent {
  private readonly api = inject(ApiService);

  protected readonly assets = toSignal(this.api.getAssets(), { initialValue: [] });

  /** Selected asset id filter; null = all assets. */
  protected readonly filter = signal<number | null>(null);

  protected readonly entries = toSignal(
    toObservable(this.filter).pipe(
      switchMap((assetId) => this.api.getJournal(assetId ?? undefined)),
    ),
    { initialValue: [] },
  );

  protected readonly columns = [
    'date',
    'asset_ticker',
    'thesis',
    'expected_outcome',
    'risk',
    'confidence',
  ];
}
