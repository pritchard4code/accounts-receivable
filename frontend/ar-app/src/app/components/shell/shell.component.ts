import { Component, OnInit } from '@angular/core';
import { Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { AuthService } from '../../services/auth.service';
import { User } from '../../models';

interface NavItem {
  label: string;
  icon: string;
  route: string;
  roles?: string[];
}

@Component({
  selector: 'app-shell',
  templateUrl: './shell.component.html',
  styleUrls: ['./shell.component.scss']
})
export class ShellComponent implements OnInit {
  currentUser: User | null = null;
  activeRoute = '';

  navItems: NavItem[] = [
    { label: 'Dashboard', icon: 'dashboard', route: '/dashboard' },
    { label: 'Invoices', icon: 'receipt_long', route: '/invoices' },
    { label: 'Payments', icon: 'payments', route: '/payments' },
    { label: 'Collections', icon: 'account_balance', route: '/collections' },
    { label: 'Credit Management', icon: 'credit_score', route: '/credit' },
    { label: 'Disputes', icon: 'gavel', route: '/disputes' },
    { label: 'Reports', icon: 'bar_chart', route: '/reports' },
    { label: 'Customers', icon: 'people', route: '/customers' },
  ];

  constructor(private authService: AuthService, private router: Router) {}

  ngOnInit(): void {
    this.currentUser = this.authService.getCurrentUser();
    this.router.events.pipe(
      filter(e => e instanceof NavigationEnd)
    ).subscribe((e: any) => {
      this.activeRoute = e.urlAfterRedirects;
    });
    this.activeRoute = this.router.url;
  }

  isActive(route: string): boolean {
    return this.activeRoute.startsWith(route);
  }

  navigate(route: string): void {
    this.router.navigate([route]);
  }

  getUserInitials(): string {
    if (!this.currentUser) return 'U';
    const name = this.currentUser.username || this.currentUser.email;
    return name.substring(0, 2).toUpperCase();
  }

  getRoleLabel(): string {
    const labels: Record<string, string> = {
      admin: 'Administrator',
      ar_clerk: 'AR Clerk',
      collections_specialist: 'Collections',
      finance_manager: 'Finance Manager',
      credit_manager: 'Credit Manager',
      customer: 'Customer'
    };
    return labels[this.currentUser?.role || ''] || this.currentUser?.role || '';
  }

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }
}
