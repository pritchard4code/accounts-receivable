import { Component, OnInit } from '@angular/core';
import { ChartConfiguration, ChartData } from 'chart.js';
import { ReportingService } from '../../services/reporting.service';
import { AgingReport, CashTrend, AgingBucket } from '../../models';

@Component({
  selector: 'app-reports',
  templateUrl: './reports.component.html',
  styleUrls: ['./reports.component.scss']
})
export class ReportsComponent implements OnInit {
  activeTab = 0;
  loadingAging = false;
  loadingTrend = false;
  loadingForecast = false;

  agingReport: AgingReport | null = null;
  agingDisplayCols = ['customer_name', 'current', 'days_1_30', 'days_31_60', 'days_61_90', 'days_over_90', 'total'];
  dso = 0;

  // Aging Pie Chart
  agingPieData: ChartData<'doughnut'> = {
    labels: ['Current', '1-30 Days', '31-60 Days', '61-90 Days', '90+ Days'],
    datasets: [{
      data: [0, 0, 0, 0, 0],
      backgroundColor: ['#003087', '#1565c0', '#f57c00', '#d32f2f', '#6a1b9a'],
      borderWidth: 2,
      borderColor: '#fff'
    }]
  };

  agingPieOptions: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'right' },
      tooltip: {
        callbacks: {
          label: (ctx) => ` $${Number(ctx.raw).toLocaleString('en-US', { minimumFractionDigits: 2 })}`
        }
      }
    }
  };

  // Cash Trend Chart
  cashTrendData: ChartData<'bar'> = {
    labels: [],
    datasets: [
      { label: 'Collected', data: [], backgroundColor: '#003087' },
      { label: 'Invoiced', data: [], backgroundColor: '#E87722' }
    ]
  };

  cashTrendOptions: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { position: 'top' } },
    scales: {
      y: {
        beginAtZero: true,
        ticks: { callback: (val) => `$${Number(val).toLocaleString()}` }
      }
    }
  };

  constructor(private reportingService: ReportingService) {}

  ngOnInit(): void {
    this.loadAgingReport();
    this.loadDso();
    this.loadCashTrend();
  }

  loadAgingReport(): void {
    this.loadingAging = true;
    this.reportingService.getAgingReport().subscribe({
      next: (report) => {
        this.agingReport = report;
        const t = report.totals;
        this.agingPieData = {
          ...this.agingPieData,
          datasets: [{ ...this.agingPieData.datasets[0], data: [t.current, t.days_1_30, t.days_31_60, t.days_61_90, t.days_over_90] }]
        };
        this.loadingAging = false;
      },
      error: () => { this.loadingAging = false; }
    });
  }

  loadDso(): void {
    this.reportingService.getDso().subscribe({
      next: (res) => { this.dso = res.dso; }
    });
  }

  loadCashTrend(): void {
    this.loadingTrend = true;
    this.reportingService.getCashTrend(12).subscribe({
      next: (trend: CashTrend[]) => {
        this.cashTrendData = {
          labels: trend.map(t => t.month),
          datasets: [
            { label: 'Collected', data: trend.map(t => t.collected), backgroundColor: '#003087' },
            { label: 'Invoiced', data: trend.map(t => t.invoiced), backgroundColor: '#E87722' }
          ]
        };
        this.loadingTrend = false;
      },
      error: () => { this.loadingTrend = false; }
    });
  }

  exportAgingCsv(): void {
    if (!this.agingReport) return;
    const rows = [
      ['Customer', 'Current', '1-30 Days', '31-60 Days', '61-90 Days', '90+ Days', 'Total'],
      ...this.agingReport.buckets.map(b => [
        b.customer_name, b.current, b.days_1_30, b.days_31_60, b.days_61_90, b.days_over_90, b.total
      ])
    ];
    const csv = rows.map(r => r.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ar-aging-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  }

  formatCurrency(val: number): string {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val || 0);
  }

  get agingTotals() {
    return this.agingReport?.totals;
  }
}
