/* AR System – shared JS */

// Auto-dismiss flash alerts after 5 seconds
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.alert.alert-success, .alert.alert-info').forEach(el => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(el);
      bsAlert.close();
    }, 5000);
  });
});

// Confirm destructive actions
document.querySelectorAll('[data-confirm]').forEach(el => {
  el.addEventListener('click', e => {
    if (!confirm(el.dataset.confirm)) e.preventDefault();
  });
});

// Format currency inputs on blur
document.querySelectorAll('input[data-currency]').forEach(input => {
  input.addEventListener('blur', () => {
    const val = parseFloat(input.value);
    if (!isNaN(val)) input.value = val.toFixed(2);
  });
});

// KPI refresh on dashboard
async function refreshKPIs() {
  try {
    const res = await fetch('/reports/api/kpis');
    const data = await res.json();
    const dsoEl = document.getElementById('kpi-dso');
    if (dsoEl) dsoEl.textContent = data.dso + ' days';
  } catch (_) {}
}
