import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
  {
    path: 'dashboard',
    loadComponent: () => import('./pages/dashboard/dashboard').then((m) => m.DashboardComponent),
  },
  {
    path: 'assets/:ticker',
    loadComponent: () =>
      import('./pages/asset-detail/asset-detail').then((m) => m.AssetDetailComponent),
  },
  {
    path: 'calendar',
    loadComponent: () => import('./pages/calendar/calendar').then((m) => m.CalendarComponent),
  },
  {
    path: 'ripple',
    loadComponent: () => import('./pages/ripple/ripple').then((m) => m.RippleComponent),
  },
  {
    path: 'weather',
    loadComponent: () => import('./pages/weather/weather').then((m) => m.WeatherComponent),
  },
  {
    path: 'temperature',
    loadComponent: () =>
      import('./pages/temperature/temperature').then((m) => m.TemperatureComponent),
  },
  {
    path: 'backtest',
    loadComponent: () => import('./pages/backtest/backtest').then((m) => m.BacktestComponent),
  },
  {
    path: 'journal',
    loadComponent: () => import('./pages/journal/journal').then((m) => m.JournalComponent),
  },
  { path: '**', redirectTo: 'dashboard' },
];
