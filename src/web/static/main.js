function updateClock() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('id-ID', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    const el = document.getElementById('clock');
    if (el) el.textContent = timeString + ' WIB';
}
setInterval(updateClock, 1000);
updateClock();

const STATUS_LABELS = {
    NORMAL: 'NORMAL',
    WASPADA: 'WASPADA',
    SIAGA: 'SIAGA',
    OFFLINE: 'OFFLINE',
    BELUM_KALIBRASI: 'BELUM KALIBRASI'
};

// --- Chart.js Setup ---
Chart.defaults.color = '#64748b';
Chart.defaults.font.family = "'JetBrains Mono', 'Consolas', monospace";

const CHART_MINUTES = 10;
const CHART_POINT_INTERVAL_MS = 5000;
const MAX_CHART_POINTS = (CHART_MINUTES * 60 * 1000) / CHART_POINT_INTERVAL_MS;

const chartEl = document.getElementById('waterChart');
let waterChart = null;

function thresholdDataset(label, color) {
    return {
        label: label,
        data: [],
        borderColor: color,
        borderWidth: 1.5,
        borderDash: [6, 4],
        pointRadius: 0,
        fill: false
    };
}

if (chartEl) {
    waterChart = new Chart(chartEl.getContext('2d'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Ketinggian Air (%)',
                    data: [],
                    borderColor: '#0d9488',
                    backgroundColor: 'rgba(13, 148, 136, 0.08)',
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: true,
                    tension: 0.3,
                    spanGaps: false
                },
                thresholdDataset('Waspada', '#f59e0b'),
                thresholdDataset('Siaga', '#ef4444')
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(0, 0, 0, 0.06)' },
                    ticks: { maxTicksLimit: 6, font: { size: 10 } }
                },
                y: {
                    grid: { color: 'rgba(0, 0, 0, 0.06)' },
                    min: 0,
                    max: 100,
                    ticks: {
                        font: { size: 10 },
                        callback: function(value) { return value + '%'; }
                    }
                }
            },
            animation: { duration: 0 }
        }
    });
}

let thresholds = { waspada: null, siaga: null };

function timeLabel(date) {
    return date.toLocaleTimeString('id-ID', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function pushChartPoint(label, pct) {
    if (!waterChart) return;
    const ds = waterChart.data.datasets;
    waterChart.data.labels.push(label);
    ds[0].data.push(pct);
    ds[1].data.push(thresholds.waspada);
    ds[2].data.push(thresholds.siaga);
    while (waterChart.data.labels.length > MAX_CHART_POINTS) {
        waterChart.data.labels.shift();
        ds.forEach(d => d.data.shift());
    }
    waterChart.update();
}

function refreshThresholdLines() {
    if (!waterChart) return;
    const n = waterChart.data.labels.length;
    waterChart.data.datasets[1].data = Array(n).fill(thresholds.waspada);
    waterChart.data.datasets[2].data = Array(n).fill(thresholds.siaga);
    waterChart.update();
}

// --- Polling Status API ---
let lastChartPush = 0;
let lastData = null;

async function fetchStatus() {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();
        lastData = data;

        const statusEl = document.getElementById('status-text');
        if (statusEl) {
            statusEl.textContent = STATUS_LABELS[data.status] || data.status;
            statusEl.className = 'status-value ' + data.status.toLowerCase();
        }

        const waterEl = document.getElementById('water-level-text');
        if (waterEl) {
            waterEl.textContent = data.water_pct !== null ? `${data.water_pct}%` : '—';
        }

        const msgEl = document.getElementById('status-message');
        if (msgEl) msgEl.textContent = data.message || '';

        const tsEl = document.getElementById('last-update');
        if (tsEl && data.timestamp) {
            const d = new Date(data.timestamp * 1000);
            tsEl.textContent = 'Terakhir: ' + d.toLocaleTimeString('id-ID', { hour12: false });
        }

        const dot = document.getElementById('connection-dot');
        const badge = document.getElementById('camera-badge');
        if (data.camera_connected) {
            if (dot) dot.className = 'status-dot';
            if (badge) { badge.className = 'camera-badge online'; badge.textContent = '● Online · ' + data.source; }
        } else {
            if (dot) dot.className = 'status-dot offline';
            if (badge) { badge.className = 'camera-badge offline'; badge.textContent = '● Offline'; }
        }

        if (data.waspada_pct !== thresholds.waspada || data.siaga_pct !== thresholds.siaga) {
            thresholds = { waspada: data.waspada_pct, siaga: data.siaga_pct };
            refreshThresholdLines();
        }

        const now = Date.now();
        if (now - lastChartPush >= CHART_POINT_INTERVAL_MS) {
            lastChartPush = now;
            pushChartPoint(timeLabel(new Date()), data.water_pct);
        }

        if (typeof onStatusUpdate === 'function') onStatusUpdate(data);
    } catch (e) {
        const dot = document.getElementById('connection-dot');
        if (dot) dot.className = 'status-dot offline';
    }
}

setInterval(fetchStatus, 1000);

// --- Load Historical Data for Chart ---
async function loadHistory() {
    try {
        const res = await fetch(`/api/history?minutes=${CHART_MINUTES}`);
        const data = await res.json();
        if (!waterChart) return;

        const recent = data.slice(-MAX_CHART_POINTS);
        waterChart.data.labels = recent.map(d => timeLabel(new Date(d.timestamp * 1000)));
        waterChart.data.datasets[0].data = recent.map(d => d.water_pct);
        if (recent.length > 0) lastChartPush = recent[recent.length - 1].timestamp * 1000;
        refreshThresholdLines();
    } catch (e) {
        console.log('Gagal memuat riwayat:', e);
    }
}

loadHistory().then(fetchStatus);
