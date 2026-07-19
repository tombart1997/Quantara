import { Component, computed, input } from '@angular/core';

/** Tiny inline SVG sparkline for a close-price series (oldest first). */
@Component({
  selector: 'app-sparkline',
  template: `
    @if (points(); as pts) {
      <svg viewBox="0 0 100 28" preserveAspectRatio="none" class="sparkline" aria-hidden="true">
        <polyline
          [attr.points]="pts"
          fill="none"
          stroke="#6ec1ff"
          stroke-width="1.5"
          vector-effect="non-scaling-stroke"
        />
      </svg>
    }
  `,
  styles: [
    `
      .sparkline {
        width: 80px;
        height: 24px;
        display: block;
      }
    `,
  ],
})
export class SparklineComponent {
  readonly data = input<number[]>([]);

  /** "x,y x,y …" normalized to the 100x28 viewBox (2px vertical padding). */
  protected readonly points = computed(() => {
    const series = this.data();
    if (series.length < 2) return null;
    const min = Math.min(...series);
    const max = Math.max(...series);
    const range = max - min || 1;
    return series
      .map((value, i) => {
        const x = (i / (series.length - 1)) * 100;
        const y = 26 - ((value - min) / range) * 24;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');
  });
}
