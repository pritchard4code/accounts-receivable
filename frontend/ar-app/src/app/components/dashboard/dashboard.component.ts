import { Component, OnInit } from '@angular/core';
import { ChartConfiguration, ChartData } from 'chart.js';
import { ReportingService } from '../../services/reporting.service';
import { InvoiceService } from '../../services/invoice.service';
import { CollectionsService } from '../../services/collections.service';
import { DashboardKpis, Invoice, CollectionItem, AgingReport, CashTrend } from '../../models';

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss']
})
export class DashboardComponent implements OnInit {
  kpis: DashboardKpis | null = null;
  recentInvoices: Invoice[] = [];
  collectionQueue: CollectionItem[] = [];
  loadingKpis = true;
  loadingInvoices = true;
  loadingQueue = true;
  today = new Date();

  // Aging Chart
  agingChartData: ChartData<'bar'> = {
    labels: ['Current', '1-30 Days', '31-60 Days', '61-90 Days', '90+ Days'],
    datasets: [{
      label: 'Outstanding ($)',
      data: [0, 0, 0, 0, 0],
      backgroundColor: ['#003087', '#1565c0', '#f57c00', '#d32f2f', '#6a1b9a'],
      borderRadius: 4,
    }]
  };

  agingChartOptions: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (ctx) => `$${Number(ctx.raw).toLocaleString('en-US', { minimumFractionDigits: 2 })}`
        }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          callback: (val) => `$${Number(val).toLocaleString()}`
        },
        grid: { color: '#e0e4ea' }
      },
      x: { grid: { display: false } }
    }
  };

  // Cash Trend Chart
  trendChartData: ChartData<'line'> = {
    labels: [],
    datasets: [
      {
        label: 'Collected',
        data: [],
        borderColor: '#003087',
        backgroundColor: 'rgba(0,48,135,0.08)',
        fill: true,
        tension: 0.4,
        pointBackgroundColor: '#003087',
      },
      {
        label: 'Invoiced',
        data: [],
        borderColor: '#E87722',
        backgroundColor: 'rgba(232,119,34,0.08)',
        fill: true,
        tension: 0.4,
        pointBackgroundColor: '#E87722',
      }
    ]
  };

  trendChartOptions: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'top', labels: { usePointStyle: true, padding: 16 } },
      tooltip: {
        callbacks: {
          label: (ctx) => `${ctx.dataset.label}: $${Number(ctx.raw).toLocaleString()}`
        }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: { callback: (val) => `$${Number(val).toLocaleString()}` },
        grid: { color: '#e0e4ea' }
      },
      x: { grid: { display: false } }
    }
  };

  displayedInvoiceCols = ['invoice_number', 'customer_name', 'due_date', 'total_amount', 'balance_due', 'status'];
  displayedQueueCols = ['customer_name', 'total_overdue', 'days_overdue', 'overdue_invoices', 'risk_level'];

  constructor(
    private reportingService: ReportingService,
    private invoiceService: InvoiceService,
    private collectionsService: CollectionsService
  ) {}

  ngOnInit(): void {
    this.loadKpis();
    this.loadAgingChart();
    this.loadCashTrend();
    this.loadRecentInvoices();
    this.loadCollectionQueue();
  }

  loadKpis(): void {
    this.loadingKpis = true;
    this.reportingService.getDashboardKpis().subscribe({
      next: (kpis) => { this.kpis = kpis; this.loadingKpis = false; },
      error: () => { this.loadingKpis = false; this.kpis = this.getMockKpis(); }
    });
  }

  loadAgingChart(): void {
    this.reportingService.getAgingReport().subscribe({
      next: (report: AgingReport) => {
        const t = report.totals;
        this.agingChartData = {
          ...this.agingChartData,
          datasets: [{
            ...this.agingChartData.datasets[0],
            data: [t.current, t.days_1_30, t.days_31_60, t.days_61_90, t.days_over_90]
          }]
        };
      },
      error: () => {}
    });
  }

  loadCashTrend(): void {
    this.reportingService.getCashTrend(6).subscribe({
      next: (trend: CashTrend[]) => {
        this.trendChartData = {
          labels: trend.map(t => t.month),
          datasets: [
            { ...this.trendChartData.datasets[0], data: trend.map(t => t.collected) },
            { ...this.trendChartData.datasets[1], data: trend.map(t => t.invoiced) }
          ]
        };
      },
      error: () => {}
    });
  }

  loadRecentInvoices(): void {
    this.loadingInvoices = true;
    this.invoiceService.getInvoices({ size: 10 }).subscribe({
      next: (res) => { this.recentInvoices = res.items; this.loadingInvoices = false; },
      error: () => { this.loadingInvoices = false; }
    });
  }

  loadCollectionQueue(): void {
    this.loadingQueue = true;
    this.collectionsService.getCollectionQueue().subscribe({
      next: (queue) => { this.collectionQueue = queue.slice(0, 5); this.loadingQueue = false; },
      error: () => { this.loadingQueue = false; }
    });
  }

  formatCurrency(val: number): string {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val || 0);
  }

  private getMockKpis(): DashboardKpis {
    return {
      total_receivables: 0, dso: 0, overdue_amount: 0, collection_rate: 0,
      current_month_collections: 0, overdue_count: 0, total_customers: 0, invoices_this_month: 0
    };
  }
}
