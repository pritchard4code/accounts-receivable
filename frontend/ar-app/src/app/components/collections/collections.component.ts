import { Component, OnInit } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { CollectionsService } from '../../services/collections.service';
import { CollectionItem, DunningRule } from '../../models';

@Component({
  selector: 'app-collections',
  templateUrl: './collections.component.html',
  styleUrls: ['./collections.component.scss']
})
export class CollectionsComponent implements OnInit {
  collectionQueue: CollectionItem[] = [];
  dunningRules: DunningRule[] = [];
  loading = false;
  runningDunning = false;
  activeTab = 0;

  queueCols = ['customer_name', 'total_overdue', 'days_overdue', 'overdue_invoices', 'risk_level', 'last_contact', 'actions'];
  rulesCols = ['name', 'days_range', 'action_type', 'is_active'];

  constructor(
    private collectionsService: CollectionsService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.loadQueue();
    this.loadRules();
  }

  loadQueue(): void {
    this.loading = true;
    this.collectionsService.getCollectionQueue().subscribe({
      next: (queue) => { this.collectionQueue = queue; this.loading = false; },
      error: () => { this.loading = false; }
    });
  }

  loadRules(): void {
    this.collectionsService.getDunningRules().subscribe({
      next: (rules) => { this.dunningRules = rules; }
    });
  }

  sendReminder(item: CollectionItem): void {
    this.collectionsService.sendReminder(item.customer_id).subscribe({
      next: () => {
        this.snackBar.open(`Reminder sent to ${item.customer_name}`, 'Close', { duration: 3000, panelClass: 'success-snack' });
        this.loadQueue();
      },
      error: () => this.snackBar.open('Failed to send reminder', 'Close', { duration: 3000, panelClass: 'error-snack' })
    });
  }

  runDunning(): void {
    this.runningDunning = true;
    this.collectionsService.runDunning().subscribe({
      next: (result) => {
        this.runningDunning = false;
        this.snackBar.open(`Dunning workflow processed ${result.processed} customers`, 'Close', { duration: 4000, panelClass: 'success-snack' });
        this.loadQueue();
      },
      error: () => {
        this.runningDunning = false;
        this.snackBar.open('Failed to run dunning workflow', 'Close', { duration: 3000, panelClass: 'error-snack' });
      }
    });
  }

  formatCurrency(val: number): string {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val || 0);
  }

  get totalOverdue(): number {
    return this.collectionQueue.reduce((s, i) => s + i.total_overdue, 0);
  }

  get highRiskCount(): number {
    return this.collectionQueue.filter(i => ['high', 'critical'].includes(i.risk_level)).length;
  }
}
