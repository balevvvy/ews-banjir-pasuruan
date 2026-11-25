function showFeedback(id, text, timeoutMs = 6000) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = text;
    clearTimeout(el._timer);
    if (timeoutMs) el._timer = setTimeout(() => { el.textContent = ''; }, timeoutMs);
}

async function postJSON(url, body) {
    const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body || {})
    });
    if (res.status === 401) {
        window.location.href = '/login';
        throw new Error('Sesi habis');
    }
    return res.json();
}

// --- Kontrol PTZ (khusus kamera Dahua PTZ) ---
async function resetPTZ() {
    const btn = document.getElementById('btn-reset-camera');
    const label = 'Kembalikan Kamera ke Papan Duga';

    btn.disabled = true;
    btn.textContent = 'Mengembalikan kamera...';
    try {
        const data = await postJSON('/api/ptz/reset');
        showFeedback('ptz-feedback', data.message || data.error || '');
    } catch (e) {
        showFeedback('ptz-feedback', 'Gagal menghubungi server');
    }
    btn.textContent = label;
    btn.disabled = false;
}

// --- Ambil Ulang Referensi ---
async function captureReference() {
    const btn = document.getElementById('btn-reference');
    btn.disabled = true;
    try {
        const data = await postJSON('/api/reference');
        showFeedback('system-feedback', data.message);
    } catch (e) {
        showFeedback('system-feedback', 'Gagal menghubungi server');
    }
    btn.disabled = false;
}

// --- Rekam Video ---
let isRecording = false;

function formatDuration(sec) {
    const m = Math.floor(sec / 60).toString().padStart(2, '0');
    const s = Math.floor(sec % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
}

function renderRecording(recording, seconds) {
    isRecording = recording;
    const btn = document.getElementById('btn-record');
    if (!btn) return;
    btn.classList.toggle('recording', recording);
    btn.textContent = recording ? `■ Stop Rekam (${formatDuration(seconds)})` : '● Rekam Video';
}

async function toggleRecording() {
    const btn = document.getElementById('btn-record');
    btn.disabled = true;
    try {
        const data = await postJSON('/api/recording', { action: isRecording ? 'stop' : 'start' });
        if (data.ok) {
            renderRecording(data.recording, 0);
            showFeedback('system-feedback', data.recording ? 'Merekam...' : data.message, data.recording ? 3000 : 15000);
        } else {
            showFeedback('system-feedback', data.message);
        }
    } catch (e) {
        showFeedback('system-feedback', 'Gagal menghubungi server');
    }
    btn.disabled = false;
}

// Dipanggil oleh main.js setiap polling status
function onStatusUpdate(data) {
    renderRecording(data.recording, data.recording_sec);
}

// --- Tampilan Video: kamera / mask deteksi ---
function setView(view) {
    document.getElementById('video-feed').src = '/video_feed?view=' + view;
    document.querySelectorAll('.view-toggle button').forEach(b => {
        b.classList.toggle('active', b.dataset.view === view);
    });
}

// --- Kontrol Sensitivitas & Blur ---
function updateSensitivity(val) {
    document.getElementById('sensitivity-val').textContent = val;
    postJSON('/api/settings', { sensitivity: parseInt(val) });
}

function updateBlur(val) {
    document.getElementById('blur-val').textContent = val;
    postJSON('/api/settings', { blur_size: parseInt(val) });
}

async function loadSettings() {
    try {
        const res = await fetch('/api/settings');
        const data = await res.json();
        if (data.sensitivity !== undefined) {
            document.getElementById('sensitivity-slider').value = data.sensitivity;
            document.getElementById('sensitivity-val').textContent = data.sensitivity;
        }
        if (data.blur_size !== undefined) {
            document.getElementById('blur-slider').value = data.blur_size;
            document.getElementById('blur-val').textContent = data.blur_size;
        }
    } catch (e) { }
}
loadSettings();

// --- Alert Log ---
async function loadAlerts() {
    try {
        const res = await fetch('/api/alerts?hours=24');
        const data = await res.json();

        const tbody = document.getElementById('alert-log-body');
        if (!tbody) return;

        if (data.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="3" style="text-align: center; padding: 20px; color: var(--text-muted);">
                        Belum ada alert dalam 24 jam terakhir.
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = data.map(alert => {
            const t = new Date(alert.timestamp * 1000);
            const timeStr = t.toLocaleString('id-ID', {
                hour12: false,
                day: '2-digit',
                month: 'short',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
            const statusClass = alert.status.toLowerCase();
            return `
                <tr>
                    <td class="mono">${timeStr}</td>
                    <td><span class="status-badge ${statusClass}">${alert.status}</span></td>
                    <td>${alert.pesan || '-'}</td>
                </tr>
            `;
        }).join('');
    } catch (e) {
        console.log('Gagal memuat alert:', e);
    }
}

loadAlerts();
setInterval(loadAlerts, 5000);

// --- Export CSV ---
async function exportCSV() {
    try {
        const res = await fetch('/api/history?minutes=1440');
        const data = await res.json();

        if (data.length === 0) {
            alert('Tidak ada data untuk diexport.');
            return;
        }

        let csv = 'Timestamp,Water_Y,Water_Pct,Status\n';
        data.forEach(row => {
            const timeStr = new Date(row.timestamp * 1000).toISOString();
            csv += `${timeStr},${row.water_y ?? ''},${row.water_pct ?? ''},${row.status}\n`;
        });

        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `ews_data_${new Date().toISOString().slice(0, 10)}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    } catch (e) {
        alert('Gagal export: ' + e.message);
    }
}
