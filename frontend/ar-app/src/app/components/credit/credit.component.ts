import { Component, OnInit } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { CreditService } from '../../services/credit.service';
import { CreditProfile } from '../../models';

@Component({
  selector: 'app-credit',
  templateUrl: './credit.component.html',
  styleUrls: ['./credit.component.scss']
})
export class CreditComponent implements OnInit {
  profiles: CreditProfile[] = [];
  highRisk: CreditProfile[] = [];
  loading = false;
  activeTab = 0;

  profileCols = ['customer_name', 'credit_limit', 'current_balance', 'available_credit', 'risk_level', 'payment_score', 'actions'];

  constructor(
    private creditService: CreditService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.loadProfiles();
    this.loadHighRisk();
  }

  loadProfiles(): void {
    this.loading = true;
    this.creditService.getCreditProfiles().subscribe({
      next: (profiles) => { this.profiles = profiles; this.loading = false; },
      error: () => { this.loading = false; }
    });
  }

  loadHighRisk(): void {
    this.creditService.getRiskAssessment().subscribe({
      next: (profiles) => { this.highRisk = profiles.filter(p => ['high', 'critical'].includes(p.risk_level)); }
    });
  }

  updateLimit(profile: CreditProfile): void {
    const newLimit = prompt(`Update credit limit for ${profile.customer_name}:`, profile.credit_limit.toString());
    if (newLimit === null) return;
    const limit = parseFloat(newLimit);
    if (isNaN(limit) || limit < 0) {
      this.snackBar.open('Invalid credit limit', 'Close', { duration: 3000, panelClass: 'error-snack' });
      return;
    }
    this.creditService.updateCreditLimit(profile.customer_id, limit).subscribe({
      next: () => {
        this.snackBar.open('Credit limit updated', 'Close', { duration: 3000, panelClass: 'success-snack' });
        this.loadProfiles();
      },
      error: () => this.snackBar.open('Failed to update credit limit', 'Close', { duration: 3000, panelClass: 'error-snack' })
    });
  }

  getUtilizationPercent(profile: CreditProfile): number {
    if (!profile.credit_limit) return 0;
    return Math.min(100, (profile.current_balance / profile.credit_limit) * 100);
  }

  formatCurrency(val: number): string {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val || 0);
  }
}
