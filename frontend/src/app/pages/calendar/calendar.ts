import { Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { Subject, startWith, switchMap } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatSnackBar } from '@angular/material/snack-bar';

import { ApiService } from '../../core/api.service';
import { EventType, MarketEvent } from '../../core/api.models';
import { AddEventDialogComponent } from './add-event-dialog';

interface DayCell {
  day: number;
  date: string; // YYYY-MM-DD
  isToday: boolean;
}

const MONTH_NAMES = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];

const TYPE_LABELS: Record<EventType, string> = {
  EARNINGS: 'Earnings',
  ECONOMIC_RELEASE: 'Economic release',
  COMPANY_ANNOUNCEMENT: 'Company announcement',
  COMMODITY_REPORT: 'Commodity report',
  WEATHER: 'Weather',
};

@Component({
  selector: 'app-calendar',
  imports: [MatButtonModule, MatIconModule, MatMenuModule],
  templateUrl: './calendar.html',
  styleUrl: './calendar.scss',
})
export class CalendarComponent {
  private readonly api = inject(ApiService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);

  private readonly today = new Date();
  protected readonly viewYear = signal(this.today.getFullYear());
  protected readonly viewMonth = signal(this.today.getMonth()); // 0-based

  private readonly refreshEvents = new Subject<void>();
  protected readonly events = toSignal(
    this.refreshEvents.pipe(
      startWith(void 0),
      switchMap(() => this.api.getEvents()),
    ),
    { initialValue: [] },
  );

  protected readonly legend = Object.entries(TYPE_LABELS) as [EventType, string][];

  protected readonly title = computed(
    () => `${MONTH_NAMES[this.viewMonth()]} ${this.viewYear()}`,
  );

  /** True when the displayed month contains at least one event. */
  protected readonly hasEventsThisMonth = computed(() => {
    const prefix = `${this.viewYear()}-${String(this.viewMonth() + 1).padStart(2, '0')}-`;
    return this.events().some((e) => e.date.startsWith(prefix));
  });

  private readonly eventsByDate = computed(() => {
    const map = new Map<string, MarketEvent[]>();
    for (const event of this.events()) {
      const key = event.date.slice(0, 10);
      const list = map.get(key) ?? [];
      list.push(event);
      map.set(key, list);
    }
    return map;
  });

  /** Null entries are leading blanks before the 1st of the month. */
  protected readonly cells = computed<(DayCell | null)[]>(() => {
    const year = this.viewYear();
    const month = this.viewMonth();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const todayKey = this.today.toISOString().slice(0, 10);
    const cells: (DayCell | null)[] = [];
    for (let i = 0; i < new Date(year, month, 1).getDay(); i++) cells.push(null);
    for (let day = 1; day <= daysInMonth; day++) {
      const date = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
      cells.push({ day, date, isToday: date === todayKey });
    }
    return cells;
  });

  protected eventsFor(date: string): MarketEvent[] {
    return this.eventsByDate().get(date) ?? [];
  }

  /** The event whose chip opened the delete menu. */
  protected readonly activeEvent = signal<MarketEvent | null>(null);

  private readonly seriesCounts = computed(() => {
    const counts = new Map<string, number>();
    for (const event of this.events()) {
      if (event.series_id) {
        counts.set(event.series_id, (counts.get(event.series_id) ?? 0) + 1);
      }
    }
    return counts;
  });

  protected seriesCount(seriesId: string): number {
    return this.seriesCounts().get(seriesId) ?? 0;
  }

  protected deleteOccurrence(event: MarketEvent): void {
    this.api.deleteEvent(event.id).subscribe(() => {
      this.snackBar.open('Event deleted', undefined, { duration: 2500 });
      this.refreshEvents.next();
    });
  }

  protected deleteSeries(event: MarketEvent): void {
    if (!event.series_id) return;
    this.api.deleteEventSeries(event.series_id).subscribe((result) => {
      this.snackBar.open(`${result.deleted} events deleted`, undefined, { duration: 2500 });
      this.refreshEvents.next();
    });
  }

  protected typeLabel(type: EventType): string {
    return TYPE_LABELS[type];
  }

  protected typeClass(type: EventType): string {
    return `type-${type.toLowerCase()}`;
  }

  protected previousMonth(): void {
    if (this.viewMonth() === 0) {
      this.viewMonth.set(11);
      this.viewYear.update((y) => y - 1);
    } else {
      this.viewMonth.update((m) => m - 1);
    }
  }

  protected nextMonth(): void {
    if (this.viewMonth() === 11) {
      this.viewMonth.set(0);
      this.viewYear.update((y) => y + 1);
    } else {
      this.viewMonth.update((m) => m + 1);
    }
  }

  protected openAddEvent(): void {
    this.dialog
      .open(AddEventDialogComponent, { width: '560px', maxWidth: '95vw' })
      .afterClosed()
      .subscribe((created: MarketEvent[] | undefined) => {
        if (!created?.length) return;
        this.snackBar.open(
          created.length === 1 ? 'Event added' : `${created.length} events added`,
          undefined,
          { duration: 2500 },
        );
        // Jump the calendar to the first occurrence's month so it's visible immediately.
        const [year, month] = created[0].date.slice(0, 10).split('-').map(Number);
        this.viewYear.set(year);
        this.viewMonth.set(month - 1);
        this.refreshEvents.next();
      });
  }
}
