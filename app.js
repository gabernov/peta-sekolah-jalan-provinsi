/**
 * Dashboard Sekolah Jawa Barat - App Logic
 * Filters, Search, Sort, Pagination, Export
 */

// --- Global State ---
let allData = [];
let filteredData = [];
let currentPage = 1;
const rowsPerPage = 15;
let sortColumn = 'no';
let sortDirection = 'asc';

// Active filters
let activeFilters = {
    jenjang: [],
    status: [],
    validasi: [],
    uptd: '',
    kabupaten: '',
    search: ''
};

// --- Initialize ---
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch('data.json');
        allData = await response.json();
        filteredData = [...allData];
        
        console.log(`Loaded ${allData.length} records`);
        
        populateKabupatenFilter();
        updatePanelCards();
        renderTable();
    } catch (error) {
        console.error('Error loading data:', error);
        document.getElementById('table-body').innerHTML = `
            <tr><td colspan="9" class="px-4 py-8 text-center text-red-500">
                Gagal memuat data. Pastikan file data.json tersedia.
            </td></tr>
        `;
    }
});

// --- Populate Kabupaten Filter ---
function populateKabupatenFilter() {
    const kabupatenList = [...new Set(allData.map(d => d.kabupaten))].sort();
    const select = document.getElementById('filter-kabupaten');
    kabupatenList.forEach(kab => {
        const option = document.createElement('option');
        option.value = kab;
        option.textContent = kab;
        select.appendChild(option);
    });
}

// --- Toggle Filter (for button-based filters) ---
function toggleFilter(type, value) {
    const index = activeFilters[type].indexOf(value);
    if (index === -1) {
        activeFilters[type].push(value);
    } else {
        activeFilters[type].splice(index, 1);
    }
    
    // Update button visual state
    const container = document.getElementById(`filter-${type}`);
    container.querySelectorAll('.filter-btn').forEach(btn => {
        const btnValue = btn.getAttribute('data-value');
        if (activeFilters[type].includes(btnValue)) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
    
    currentPage = 1;
    applyFilters();
}

// --- Apply All Filters ---
function applyFilters() {
    // Update dropdown filters
    activeFilters.uptd = document.getElementById('filter-uptd').value;
    activeFilters.kabupaten = document.getElementById('filter-kabupaten').value;
    activeFilters.search = document.getElementById('search-input').value.toLowerCase().trim();
    
    filteredData = allData.filter(item => {
        // Jenjang filter
        if (activeFilters.jenjang.length > 0 && !activeFilters.jenjang.includes(item.jenjang)) {
            return false;
        }
        
        // Status filter
        if (activeFilters.status.length > 0 && !activeFilters.status.includes(item.status)) {
            return false;
        }
        
        // Validasi filter
        if (activeFilters.validasi.length > 0 && !activeFilters.validasi.includes(item.validasi)) {
            return false;
        }
        
        // UPTD filter
        if (activeFilters.uptd && item.uptd !== activeFilters.uptd) {
            return false;
        }
        
        // Kabupaten filter
        if (activeFilters.kabupaten && item.kabupaten !== activeFilters.kabupaten) {
            return false;
        }
        
        // Search filter
        if (activeFilters.search && !item.nama_sekolah.toLowerCase().includes(activeFilters.search)) {
            return false;
        }
        
        return true;
    });
    
    // Re-apply sort
    sortData();
    
    updatePanelCards();
    renderTable();
}

// --- Reset All Filters ---
function resetFilters() {
    activeFilters = {
        jenjang: [],
        status: [],
        validasi: [],
        uptd: '',
        kabupaten: '',
        search: ''
    };
    
    // Reset button states
    document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
    
    // Reset dropdowns
    document.getElementById('filter-uptd').value = '';
    document.getElementById('filter-kabupaten').value = '';
    document.getElementById('search-input').value = '';
    
    currentPage = 1;
    filteredData = [...allData];
    updatePanelCards();
    renderTable();
}

// --- Update Panel Cards ---
function updatePanelCards() {
    const total = filteredData.length;
    const valid = filteredData.filter(d => d.validasi === 'Valid').length;
    const tidakValid = filteredData.filter(d => d.validasi === 'Tidak Valid').length;
    const negeri = filteredData.filter(d => d.status === 'NEGERI').length;
    const swasta = filteredData.filter(d => d.status === 'SWASTA').length;
    
    const sma = filteredData.filter(d => d.jenjang === 'SMA').length;
    const smk = filteredData.filter(d => d.jenjang === 'SMK').length;
    const slb = filteredData.filter(d => d.jenjang === 'SLB').length;
    
    document.getElementById('panel-cards').innerHTML = `
        <div class="bg-white rounded-xl shadow-sm p-4 card-hover transition-all duration-200 border-l-4 border-blue-500">
            <div class="text-2xl font-bold text-gray-800">${total}</div>
            <div class="text-sm text-gray-500">Total Sekolah</div>
            <div class="text-xs text-gray-400 mt-1">SMA: ${sma} | SMK: ${smk} | SLB: ${slb}</div>
        </div>
        <div class="bg-white rounded-xl shadow-sm p-4 card-hover transition-all duration-200 border-l-4 border-green-500">
            <div class="text-2xl font-bold text-green-600">${valid}</div>
            <div class="text-sm text-gray-500">Valid</div>
            <div class="text-xs text-gray-400 mt-1">${total > 0 ? ((valid/total)*100).toFixed(1) : 0}% dari total</div>
        </div>
        <div class="bg-white rounded-xl shadow-sm p-4 card-hover transition-all duration-200 border-l-4 border-red-500">
            <div class="text-2xl font-bold text-red-600">${tidakValid}</div>
            <div class="text-sm text-gray-500">Tidak Valid</div>
            <div class="text-xs text-gray-400 mt-1">${total > 0 ? ((tidakValid/total)*100).toFixed(1) : 0}% dari total</div>
        </div>
        <div class="bg-white rounded-xl shadow-sm p-4 card-hover transition-all duration-200 border-l-4 border-purple-500">
            <div class="text-2xl font-bold text-purple-600">${negeri}</div>
            <div class="text-sm text-gray-500">Negeri</div>
            <div class="text-xs text-gray-400 mt-1">${total > 0 ? ((negeri/total)*100).toFixed(1) : 0}% dari total</div>
        </div>
        <div class="bg-white rounded-xl shadow-sm p-4 card-hover transition-all duration-200 border-l-4 border-orange-500">
            <div class="text-2xl font-bold text-orange-600">${swasta}</div>
            <div class="text-sm text-gray-500">Swasta</div>
            <div class="text-xs text-gray-400 mt-1">${total > 0 ? ((swasta/total)*100).toFixed(1) : 0}% dari total</div>
        </div>
    `;
    
    document.getElementById('result-count').textContent = total;
    document.getElementById('total-count').textContent = allData.length;
}

// --- Sort Data ---
function sortData() {
    filteredData.sort((a, b) => {
        let valA = a[sortColumn];
        let valB = b[sortColumn];
        
        // Handle different types
        if (sortColumn === 'jarak_m') {
            valA = parseFloat(valA) || 0;
            valB = parseFloat(valB) || 0;
        } else if (sortColumn === 'no') {
            // Keep original order
            return sortDirection === 'asc' ? 0 : 0;
        } else {
            valA = String(valA || '').toLowerCase();
            valB = String(valB || '').toLowerCase();
        }
        
        if (valA < valB) return sortDirection === 'asc' ? -1 : 1;
        if (valA > valB) return sortDirection === 'asc' ? 1 : -1;
        return 0;
    });
}

function sortTable(column) {
    if (sortColumn === column) {
        sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        sortColumn = column;
        sortDirection = 'asc';
    }
    sortData();
    renderTable();
}

// --- Render Table ---
function renderTable() {
    const tbody = document.getElementById('table-body');
    const totalPages = Math.ceil(filteredData.length / rowsPerPage);
    
    if (currentPage > totalPages) currentPage = totalPages || 1;
    
    const startIdx = (currentPage - 1) * rowsPerPage;
    const endIdx = startIdx + rowsPerPage;
    const pageData = filteredData.slice(startIdx, endIdx);
    
    if (pageData.length === 0) {
        tbody.innerHTML = `
            <tr><td colspan="9" class="px-4 py-8 text-center text-gray-500">
                Tidak ada data yang sesuai dengan filter.
            </td></tr>
        `;
    } else {
        tbody.innerHTML = pageData.map((item, idx) => `
            <tr class="table-row fade-in">
                <td class="px-4 py-3 text-gray-500">${startIdx + idx + 1}</td>
                <td class="px-4 py-3">
                    <div class="font-medium text-gray-800">${escapeHtml(item.nama_sekolah)}</div>
                    <div class="text-xs text-gray-400">${escapeHtml(item.desa || '-')}, ${escapeHtml(item.kecamatan || '-')}</div>
                </td>
                <td class="px-4 py-3">
                    <span class="inline-block px-2 py-0.5 rounded text-xs font-medium ${getJenjangClass(item.jenjang)}">${item.jenjang}</span>
                </td>
                <td class="px-4 py-3">
                    <span class="inline-block px-2 py-0.5 rounded text-xs font-medium ${item.status === 'NEGERI' ? 'badge-negeri' : 'badge-swasta'}">${item.status}</span>
                </td>
                <td class="px-4 py-3 text-gray-600">${escapeHtml(item.kabupaten || '-')}</td>
                <td class="px-4 py-3 font-mono ${parseFloat(item.jarak_m) <= 60 ? 'text-green-600 font-semibold' : 'text-gray-600'}">${item.jarak_m ? item.jarak_m.toFixed(1) : '-'}</td>
                <td class="px-4 py-3">
                    <span class="inline-block px-2 py-0.5 rounded text-xs font-medium ${item.validasi === 'Valid' ? 'badge-valid' : 'badge-invalid'}">${item.validasi}</span>
                </td>
                <td class="px-4 py-3 text-gray-600">${escapeHtml(item.uptd || '-')}</td>
                <td class="px-4 py-3 text-center">
                    ${item.maps_link ? `<a href="${item.maps_link}" target="_blank" class="inline-flex items-center gap-1 px-2 py-1 bg-blue-50 text-blue-600 rounded hover:bg-blue-100 text-xs font-medium transition-colors"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/></svg>Maps</a>` : '-'}
                </td>
            </tr>
        `).join('');
    }
    
    // Update pagination
    document.getElementById('current-page').textContent = currentPage;
    document.getElementById('total-pages').textContent = totalPages || 1;
    document.getElementById('prev-btn').disabled = currentPage <= 1;
    document.getElementById('next-btn').disabled = currentPage >= totalPages;
}

function changePage(delta) {
    currentPage += delta;
    renderTable();
    document.querySelector('.overflow-x-auto').scrollTop = 0;
}

// --- Export to Excel ---
function exportToExcel() {
    if (filteredData.length === 0) {
        alert('Tidak ada data untuk di-export!');
        return;
    }
    
    // Create CSV content
    const headers = ['No', 'Nama Sekolah', 'NPSN', 'Jenjang', 'Status', 'Kabupaten', 'Kecamatan', 'Desa', 'Jarak (m)', 'Validasi', 'UPTD', 'Nama Jalan', 'Kode Jalan', 'Tipe Jalan', 'Lebar Lajur', 'Maps Link'];
    
    const rows = filteredData.map((item, idx) => [
        idx + 1,
        `"${(item.nama_sekolah || '').replace(/"/g, '""')}"`,
        item.npsn || '',
        item.jenjang || '',
        item.status || '',
        `"${(item.kabupaten || '').replace(/"/g, '""')}"`,
        `"${(item.kecamatan || '').replace(/"/g, '""')}"`,
        `"${(item.desa || '').replace(/"/g, '""')}"`,
        item.jarak_m || '',
        item.validasi || '',
        item.uptd || '',
        `"${(item.nama_jalan || '').replace(/"/g, '""')}"`,
        item.kode_jalan || '',
        item.tipe_jalan || '',
        item.lebar_lajur || '',
        item.maps_link || ''
    ]);
    
    const csvContent = '\uFEFF' + headers.join(',') + '\n' + rows.map(r => r.join(',')).join('\n');
    
    // Create download link
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `sekolah_jabar_${new Date().toISOString().slice(0,10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

// --- Utility Functions ---
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getJenjangClass(jenjang) {
    switch(jenjang) {
        case 'SMA': return 'bg-blue-100 text-blue-700';
        case 'SMK': return 'bg-purple-100 text-purple-700';
        case 'SLB': return 'bg-amber-100 text-amber-700';
        default: return 'bg-gray-100 text-gray-700';
    }
}
