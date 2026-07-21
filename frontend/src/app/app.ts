import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatTooltipModule } from '@angular/material/tooltip';

interface NavItem {
  label: string;
  icon: string;
  route: string;
}

@Component({
  selector: 'app-root',
  imports: [
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    MatButtonModule,
    MatDialogModule,
    MatIconModule,
    MatListModule,
    MatSidenavModule,
    MatToolbarModule,
    MatTooltipModule,
  ],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  private readonly dialog = inject(MatDialog);

  protected readonly navItems: NavItem[] = [
    { label: 'Dashboard', icon: 'dashboard', route: '/dashboard' },
    { label: 'Ripple', icon: 'blur_circular', route: '/ripple' },
    { label: 'Weather', icon: 'thermostat', route: '/weather' },
    { label: 'Temperature', icon: 'device_thermostat', route: '/temperature' },
    { label: 'Backtest', icon: 'fact_check', route: '/backtest' },
    { label: 'Calendar', icon: 'event', route: '/calendar' },
    { label: 'Journal', icon: 'edit_note', route: '/journal' },
  ];

  protected openAiConsult(): void {
    // Lazy-load so the dialog's Material deps stay out of the initial bundle.
    import('./ai-consult/ai-consult').then((m) =>
      this.dialog.open(m.AiConsultComponent, { width: '640px', maxWidth: '95vw' }),
    );
  }
}
