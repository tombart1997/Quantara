import { Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

import { ApiService } from '../../core/api.service';
import { EventType, MarketEvent } from '../../core/api.models';

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
  imports: [MatButtonModule, MatIconModule],
  templateUrl: './calendar.html',
  styleUrl: './calendar.scss',
})
export class CalendarComponent {
  private readonly api = inject(ApiService);

  private readonly today = new Date();
  protected readonly viewYear = signal(this.today.getFullYear());
  protected readonly viewMonth = signal(this.today.getMonth()); // 0-based

  protected readonly events = toSignal(this.api.getEvents(), { initialValue: [] });

  protected readonly legend = Object.entries(TYPE_LABELS) as [EventType, string][];

  protected readonly title = computed(
    () => `${MONTH_NAMES[this.viewMonth()]} ${this.viewYear()}`,
  );

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
}
