import { Component, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

import { ApiService } from '../../core/api.service';
import { JournalEntry } from '../../core/api.models';

@Component({
  selector: 'app-journal-entry-dialog',
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
  ],
  templateUrl: './journal-entry-dialog.html',
  styleUrl: './journal-entry-dialog.scss',
})
export class JournalEntryDialogComponent {
  private readonly api = inject(ApiService);
  private readonly fb = inject(FormBuilder);
  private readonly dialogRef = inject(MatDialogRef<JournalEntryDialogComponent>);

  protected readonly assets = toSignal(this.api.getAssets(), { initialValue: [] });

  protected readonly form = this.fb.nonNullable.group({
    asset_id: [null as number | null, Validators.required],
    date: [new Date().toISOString().slice(0, 10), Validators.required],
    thesis: ['', Validators.required],
    expected_outcome: [''],
    risk: [''],
    confidence: [5, [Validators.required, Validators.min(1), Validators.max(10)]],
  });

  protected readonly submitting = signal(false);
  protected readonly errorMessage = signal<string | null>(null);

  protected submit(): void {
    if (this.form.invalid || this.submitting()) return;
    this.submitting.set(true);
    this.errorMessage.set(null);
    const value = this.form.getRawValue();
    this.api
      .createJournalEntry({
        asset_id: value.asset_id as number,
        date: value.date,
        thesis: value.thesis.trim(),
        expected_outcome: value.expected_outcome.trim() || null,
        risk: value.risk.trim() || null,
        confidence: value.confidence,
      })
      .subscribe({
        next: (entry: JournalEntry) => this.dialogRef.close(entry),
        error: () => {
          this.submitting.set(false);
          this.errorMessage.set('Could not save the entry. Please try again.');
        },
      });
  }
}
