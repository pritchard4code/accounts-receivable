import { Component, OnInit } from '@angular/core';
import { PageEvent } from '@angular/material/paginator';
import { MatSnackBar } from '@angular/material/snack-bar';
import { DisputeService } from '../../services/dispute.service';
import { Dispute } from '../../models';

@Component({
  selector: 'app-disputes',
  templateUrl: './disputes.component.html',
  styleUrls: ['./disputes.component.scss']
})
export class DisputesComponent implements OnInit {
  disputes: Dispute[] = [];
  total = 0;
  loading = false;
  filterStatus = '';
  page = 1;
  size = 25;

  statusOptions = [
    { value: '', label: 'All Statuses' },
    { value: 'open', label: 'Open' },
    { value: 'under_review', label: 'Under Review' },
    { value: 'resolved', label: 'Resolved' },
    { value: 'rejected', label: 'Rejected' },
  ];

  displayedColumns = ['dispute_number', 'customer_name', 'invoice_number', 'amount_disputed', 'reason', 'status', 'created_at', 'actions'];

  constructor(
    private disputeService: DisputeService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.loadDisputes();
  }

  loadDisputes(): void {
    this.loading = true;
    this.disputeService.getDisputes({ status: this.filterStatus, page: this.page, size: this.size }).subscribe({
      next: (res) => { this.disputes = res.items; this.total = res.total; this.loading = false; },
      error: () => { this.loading = false; }
    });
  }

  onPage(event: PageEvent): void {
    this.page = event.pageIndex + 1;
    this.size = event.pageSize;
    this.loadDisputes();
  }

  updateStatus(dispute: Dispute, status: string): void {
    let resolution: string | undefined;
    if (status === 'resolved' || status === 'rejected') {
      resolution = prompt(`Enter resolution notes for dispute ${dispute.dispute_number}:`) || undefined;
    }
    this.disputeService.updateDisputeStatus(dispute.id, status, resolution).subscribe({
      next: () => {
        this.snackBar.open(`Dispute ${dispute.dispute_number} updated to ${status}`, 'Close', { duration: 3000, panelClass: 'success-snack' });
        this.loadDisputes();
      },
      error: () => this.snackBar.open('Failed to update dispute', 'Close', { duration: 3000, panelClass: 'error-snack' })
    });
  }

  getNextStatuses(current: string): { value: string; label: string }[] {
    const transitions: Record<string, { value: string; label: string }[]> = {
      open: [{ value: 'under_review', label: 'Start Review' }],
      under_review: [
        { value: 'resolved', label: 'Resolve' },
        { value: 'rejected', label: 'Reject' }
      ]
    };
    return transitions[current] || [];
  }

  formatCurrency(val: number): string {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val || 0);
  }
}
