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
import { EventType, MarketEvent, Recurrence } from '../../core/api.models';

const EVENT_TYPE_LABELS: Record<EventType, string> = {
  EARNINGS: 'Earnings',
  ECONOMIC_RELEASE: 'Economic release',
  COMPANY_ANNOUNCEMENT: 'Company announcement',
  COMMODITY_REPORT: 'Commodity report',
  WEATHER: 'Weather',
};

const RECURRENCE_LABELS: Record<Recurrence, string> = {
  NONE: 'Does not repeat',
  WEEKLY: 'Weekly',
  MONTHLY: 'Monthly',
  QUARTERLY: 'Quarterly',
  YEARLY: 'Yearly',
};

/** How many occurrences the backend creates per recurrence option. */
const RECURRENCE_COUNTS: Partial<Record<Recurrence, number>> = {
  WEEKLY: 26,
  MONTHLY: 12,
  QUARTERLY: 8,
  YEARLY: 3,
};

@Component({
  selector: 'app-add-event-dialog',
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
  ],
  templateUrl: './add-event-dialog.html',
  styleUrl: './add-event-dialog.scss',
})
export class AddEventDialogComponent {
  private readonly api = inject(ApiService);
  private readonly fb = inject(FormBuilder);
  private readonly dialogRef = inject(MatDialogRef<AddEventDialogComponent>);

  protected readonly assets = toSignal(this.api.getAssets(), { initialValue: [] });

  protected readonly eventTypes = Object.entries(EVENT_TYPE_LABELS) as [EventType, string][];
  protected readonly recurrenceOptions = Object.entries(RECURRENCE_LABELS) as [
    Recurrence,
    string,
  ][];
  protected readonly importanceLevels = [1, 2, 3, 4, 5];

  protected readonly form = this.fb.nonNullable.group({
    asset_id: [null as number | null],
    event_type: ['COMMODITY_REPORT' as EventType, Validators.required],
    date: [new Date().toISOString().slice(0, 10), Validators.required],
    time: ['14:00'],
    recurrence: ['NONE' as Recurrence, Validators.required],
    title: ['', [Validators.required, Validators.maxLength(300)]],
    description: [''],
    importance: [3, [Validators.required, Validators.min(1), Validators.max(5)]],
  });

  protected readonly submitting = signal(false);
  protected readonly errorMessage = signal<string | null>(null);

  protected submit(): void {
    if (this.form.invalid || this.submitting()) return;
    this.submitting.set(true);
    this.errorMessage.set(null);
    const value = this.form.getRawValue();
    const time = value.time || '14:00';
    this.api
      .createEvent({
        asset_id: value.asset_id ?? null,
        event_type: value.event_type,
        date: `${value.date}T${time}:00`,
        title: value.title.trim(),
        description: value.description.trim() || null,
        importance: value.importance,
        recurrence: value.recurrence,
      })
      .subscribe({
        next: (events: MarketEvent[]) => this.dialogRef.close(events),
        error: () => {
          this.submitting.set(false);
          this.errorMessage.set('Could not save the event. Please try again.');
        },
      });
  }

  protected recurrenceCount(): number | null {
    return RECURRENCE_COUNTS[this.form.controls.recurrence.value] ?? null;
  }
}
