// Global App State
let rawData2026 = [];
let summaryData = null;

let filteredRawData = [];
let currentPageData = 1;
const pageSizeData = 15;

let filteredFrame3Data = [];
let currentPageFrame3 = 1;
const pageSizeFrame3 = 15;

let filteredTop3DDData = [];
let currentPageTop3DD = 1;
const pageSizeTop3DD = 15;

let selectedChams = new Set();
let selectedTongs = new Set();

document.addEventListener('DOMContentLoaded', async () => {
    await loadSummaryData();
    await load2026Data();
    setupEventListeners();
    setupLucky26FilterEvents();
});

async function loadSummaryData() {
    try {
        const response = await fetch('analysis_summary.json');
        if (response.ok) {
            summaryData = await response.json();
            renderKPIs();
            renderHeadTailPredictions();
            renderTop20Table(summaryData.top_20_consensus);
            updateLucky26Filter();
            renderFirepowerAnd3D4D();
            
            if (summaryData.frame3_records) {
                filteredFrame3Data = [...summaryData.frame3_records];
                renderFrame3Table();
            }

            if (summaryData.history_top3_dau_duoi_records) {
                filteredTop3DDData = [...summaryData.history_top3_dau_duoi_records];
                renderTop3DDTable();
            }
        }
    } catch (err) {
        console.error('Failed to load summary analysis:', err);
    }
}

function renderFirepowerAnd3D4D() {
    if (!summaryData) return;

    // Render Song Thu & Tu Thu
    if (summaryData.song_thu_de && summaryData.song_thu_de.length >= 2) {
        document.getElementById('boxSongThu').textContent = summaryData.song_thu_de.map(x => x.number).join(' • ');
    }
    if (summaryData.tu_thu_de && summaryData.tu_thu_de.length >= 4) {
        document.getElementById('boxTuThu').textContent = summaryData.tu_thu_de.map(x => x.number).join(' • ');
    }

    // Render Top 20 3D Ba Cang
    const list3D = document.getElementById('list3D');
    const items3D = summaryData.top_20_3d || summaryData.top_10_3d || summaryData.top_5_3d || [];
    if (list3D && items3D.length > 0) {
        list3D.innerHTML = '';
        items3D.forEach(item => {
            const div = document.createElement('div');
            div.className = 'c3d4d-item';
            div.innerHTML = `
                <span>Càng ${item.cang_3d} + ${item.de_2d}</span>
                <strong class="c3d4d-val">${item.number_3d}</strong>
            `;
            list3D.appendChild(div);
        });
    }

    // Render Top 20 4D Bon Cang
    const list4D = document.getElementById('list4D');
    const items4D = summaryData.top_20_4d || summaryData.top_10_4d || summaryData.top_5_4d || [];
    if (list4D && items4D.length > 0) {
        list4D.innerHTML = '';
        items4D.forEach(item => {
            const div = document.createElement('div');
            div.className = 'c3d4d-item';
            div.innerHTML = `
                <span>Càng ${item.cang_4d} + ${item.num_3d}</span>
                <strong class="c3d4d-val val-4d">${item.number_4d}</strong>
            `;
            list4D.appendChild(div);
        });
    }
}




async function load2026Data() {
    try {
        const response = await fetch('data_2026.json');
        if (response.ok) {
            rawData2026 = await response.json();
            filteredRawData = [...rawData2026];
            renderDataTable();
        }
    } catch (err) {
        console.error('Failed to load 2026 raw data:', err);
    }
}

function renderKPIs() {
    if (!summaryData) return;
    
    if (summaryData.frame3_summary) {
        const f3 = summaryData.frame3_summary;
        document.getElementById('kpiFrame3Hits').textContent = `${f3.total_frame_hits} / ${f3.total_frames} Khung`;
        document.getElementById('kpiFrame3Rate').textContent = `${f3.frame_hit_rate}%`;
        document.getElementById('kpiN1Hits').textContent = `${f3.n1_hits} Khung (${roundRate(f3.n1_hits, f3.total_frames)}%)`;
        document.getElementById('kpiFrame3Misses').textContent = `${f3.frame_misses} Khung (${f3.frame_miss_rate}%)`;
    }
}

function roundRate(num, total) {
    return (num / total * 100).toFixed(1);
}

function renderHeadTailPredictions() {
    if (!summaryData) return;
    
    if (summaryData.top_predicted_heads && summaryData.top_predicted_heads.length >= 3) {
        const headsStr = summaryData.top_predicted_heads.map(h => h.head).join(' • ');
        document.getElementById('boxTopHeads').textContent = headsStr;
        document.getElementById('kpiTopHead').textContent = summaryData.top_predicted_heads.map(h => h.head).join(', ');
    }
    
    if (summaryData.top_predicted_tails && summaryData.top_predicted_tails.length >= 3) {
        const tailsStr = summaryData.top_predicted_tails.map(t => t.tail).join(' • ');
        document.getElementById('boxTopTails').textContent = tailsStr;
        document.getElementById('kpiTopTail').textContent = summaryData.top_predicted_tails.map(t => t.tail).join(', ');
    }

    if (summaryData.top3_dau_duoi_summary) {
        const s = summaryData.top3_dau_duoi_summary;
        if (document.getElementById('badgeHead1N')) document.getElementById('badgeHead1N').textContent = `${s.head_rate_1day}%`;
        if (document.getElementById('badgeHead3N')) document.getElementById('badgeHead3N').textContent = `${s.f3_head_rate}%`;
        if (document.getElementById('badgeTail1N')) document.getElementById('badgeTail1N').textContent = `${s.tail_rate_1day}%`;
        if (document.getElementById('badgeTail3N')) document.getElementById('badgeTail3N').textContent = `${s.f3_tail_rate}%`;

        if (document.getElementById('boxTop3Rate')) document.getElementById('boxTop3Rate').textContent = `Trúng 1N: ${s.head_rate_1day}% (Đầu) / ${s.tail_rate_1day}% (Đuôi) | Nuôi Khung 3N: ${s.f3_head_rate}%`;
        if (document.getElementById('boxTop4Rate')) document.getElementById('boxTop4Rate').textContent = `Trúng 1N: ${s.top4_head_rate_1day}% (Đầu) / ${s.top4_tail_rate_1day}% (Đuôi) | Nuôi Khung 3N: ${s.f3_top4_tail_rate}%`;
        if (document.getElementById('boxTop5Rate')) document.getElementById('boxTop5Rate').textContent = `Trúng 1N: ${s.top5_head_rate_1day}% (Đầu) / ${s.top5_tail_rate_1day}% (Đuôi) | Nuôi Khung 3N: ${s.f3_top5_tail_rate}%`;

        if (document.getElementById('statHead1N')) document.getElementById('statHead1N').textContent = `${s.head_hits_1day}/${s.total_evals} (${s.head_rate_1day}%)`;
        if (document.getElementById('statTail1N')) document.getElementById('statTail1N').textContent = `${s.tail_hits_1day}/${s.total_evals} (${s.tail_rate_1day}%)`;
        if (document.getElementById('statComb1N')) document.getElementById('statComb1N').textContent = `${s.combined_hits_1day}/${s.total_evals} (${s.combined_rate_1day}%)`;
        if (document.getElementById('statComb3N')) document.getElementById('statComb3N').textContent = `${s.f3_combined_hits}/${s.total_f3_evals} (${s.f3_combined_rate}%)`;
    }
}

function renderTop20Table(top20List) {
    const tbody = document.getElementById('tbodyTop20');
    tbody.innerHTML = '';
    
    top20List.forEach((item, index) => {
        const rank = index + 1;
        let rankBadge = `<span class="tag tag-silver">Top ${rank}</span>`;
        if (rank === 1) rankBadge = `<span class="tag tag-gold">🥇 Top 1</span>`;
        else if (rank === 2) rankBadge = `<span class="tag tag-silver">🥈 Top 2</span>`;
        else if (rank === 3) rankBadge = `<span class="tag tag-bronze">🥉 Top 3</span>`;
        
        let rhythmBadge = `<span class="status-pill active">Nhịp Đẹp</span>`;
        if (item.nhip < 3) rhythmBadge = `<span class="status-pill disabled">Vừa Ra</span>`;
        else if (item.nhip > 25) rhythmBadge = `<span class="status-pill disabled">Gan Dài</span>`;

        const isCham = item.is_cham_g7 === 'Có';
        const chamTag = isCham ? 
            `<span class="tag tag-gold" style="font-size: 11px; padding: 2px 6px;">Có Chạm</span>` : 
            `<span style="color: var(--text-muted); font-size: 12px;">Không</span>`;

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${rankBadge}</td>
            <td><strong style="font-size: 18px; color: #FFF;">${item.number}</strong></td>
            <td>Tổng ${item.tong}</td>
            <td>${chamTag}</td>
            <td><strong style="color: var(--cyan);">${item.f30} lần</strong></td>
            <td><strong style="color: var(--cyan);">${item.f60} lần</strong></td>
            <td><strong style="color: var(--cyan);">${item.f90} lần</strong></td>
            <td>${item.nhip} ngày</td>
            <td>${rhythmBadge}</td>
            <td><strong style="color: var(--gold);">${item.score}</strong></td>
        `;
        tbody.appendChild(tr);
    });
}

function renderFrame3Table() {
    const tbody = document.getElementById('tbodyFrame3Log');
    tbody.innerHTML = '';
    
    const startIdx = (currentPageFrame3 - 1) * pageSize;
    const endIdx = startIdx + pageSize;
    const pageData = filteredFrame3Data.slice(startIdx, endIdx);
    
    pageData.forEach((row) => {
        const isHit = row.frame_result.includes('TRÚNG');
        // Red badge for TRÚNG (hit), Soft Green badge for TRƯỢT (miss) per user rule
        const badgeTag = isHit ? 
            `<span class="tag tag-red" style="font-size: 13px; background: rgba(239, 68, 68, 0.25); color: #F87171; border: 1px solid rgba(239, 68, 68, 0.5);">${row.frame_result}</span>` : 
            `<span class="tag tag-silver" style="font-size: 13px; background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.3);">${row.frame_result}</span>`;
            
        const n1Style = row.hit_n1.includes('Trúng') ? 'color: #F87171; font-weight: bold;' : 'color: var(--text-muted);';
        const n2Style = row.hit_n2.includes('Trúng') ? 'color: #F87171; font-weight: bold;' : 'color: var(--text-muted);';
        const n3Style = row.hit_n3.includes('Trúng') ? 'color: #F87171; font-weight: bold;' : 'color: var(--text-muted);';

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${row.stt}</td>
            <td>${row.start_date}</td>
            <td style="${n1Style}">${row.de_n1} (${row.hit_n1})</td>
            <td style="${n2Style}">${row.de_n2} (${row.hit_n2})</td>
            <td style="${n3Style}">${row.de_n3} (${row.hit_n3})</td>
            <td style="font-size: 12px; color: var(--text-muted); max-width: 250px;">${row.pred_nums}</td>
            <td>${badgeTag}</td>
        `;
        tbody.appendChild(tr);
    });
    
    renderFrame3Pagination();
}

function renderFrame3Pagination() {
    const container = document.getElementById('paginationFrame3Area');
    container.innerHTML = '';
    
    const totalPages = Math.ceil(filteredFrame3Data.length / pageSize);
    if (totalPages <= 1) return;
    
    const prevBtn = document.createElement('button');
    prevBtn.className = `page-btn ${currentPageFrame3 === 1 ? 'disabled' : ''}`;
    prevBtn.textContent = '«';
    prevBtn.onclick = () => {
        if (currentPageFrame3 > 1) {
            currentPageFrame3--;
            renderFrame3Table();
        }
    };
    container.appendChild(prevBtn);
    
    let startP = Math.max(1, currentPageFrame3 - 3);
    let endP = Math.min(totalPages, startP + 6);
    
    for (let p = startP; p <= endP; p++) {
        const pageBtn = document.createElement('button');
        pageBtn.className = `page-btn ${p === currentPageFrame3 ? 'active' : ''}`;
        pageBtn.textContent = p;
        pageBtn.onclick = () => {
            currentPageFrame3 = p;
            renderFrame3Table();
        };
        container.appendChild(pageBtn);
    }
    
    const nextBtn = document.createElement('button');
    nextBtn.className = `page-btn ${currentPageFrame3 === totalPages ? 'disabled' : ''}`;
    nextBtn.textContent = '»';
    nextBtn.onclick = () => {
        if (currentPageFrame3 < totalPages) {
            currentPageFrame3++;
            renderFrame3Table();
        }
    };
    container.appendChild(nextBtn);
}

function renderDataTable() {
    const tbody = document.getElementById('tbodyData2026');
    tbody.innerHTML = '';
    
    const startIdx = (currentPageData - 1) * pageSize;
    const endIdx = startIdx + pageSize;
    const pageData = filteredRawData.slice(startIdx, endIdx);
    
    pageData.forEach((row) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${row.date}</td>
            <td><strong style="letter-spacing: 1px;">${row.db}</strong></td>
            <td><span class="tag tag-gold" style="font-size: 14px;">${row.de}</span></td>
            <td>${row.g7_1}</td>
            <td>${row.g7_2}</td>
            <td>${row.g7_3}</td>
            <td>${row.g7_4}</td>
        `;
        tbody.appendChild(tr);
    });
    
    renderDataPagination();
}

function renderDataPagination() {
    const container = document.getElementById('paginationArea');
    container.innerHTML = '';
    
    const totalPages = Math.ceil(filteredRawData.length / pageSize);
    if (totalPages <= 1) return;
    
    const prevBtn = document.createElement('button');
    prevBtn.className = `page-btn ${currentPageData === 1 ? 'disabled' : ''}`;
    prevBtn.textContent = '«';
    prevBtn.onclick = () => {
        if (currentPageData > 1) {
            currentPageData--;
            renderDataTable();
        }
    };
    container.appendChild(prevBtn);
    
    let startP = Math.max(1, currentPageData - 3);
    let endP = Math.min(totalPages, startP + 6);
    
    for (let p = startP; p <= endP; p++) {
        const pageBtn = document.createElement('button');
        pageBtn.className = `page-btn ${p === currentPageData ? 'active' : ''}`;
        pageBtn.textContent = p;
        pageBtn.onclick = () => {
            currentPageData = p;
            renderDataTable();
        };
        container.appendChild(pageBtn);
    }
    
    const nextBtn = document.createElement('button');
    nextBtn.className = `page-btn ${currentPageData === totalPages ? 'disabled' : ''}`;
    nextBtn.textContent = '»';
    nextBtn.onclick = () => {
        if (currentPageData < totalPages) {
            currentPageData++;
            renderDataTable();
        }
    };
    container.appendChild(nextBtn);
}

function renderTop3DDTable() {
    const tbody = document.getElementById('tbodyTop3DDLog');
    if (!tbody) return;
    tbody.innerHTML = '';

    const startIdx = (currentPageTop3DD - 1) * pageSizeTop3DD;
    const endIdx = startIdx + pageSizeTop3DD;
    const pageItems = filteredTop3DDData.slice(startIdx, endIdx);

    if (pageItems.length === 0) {
        tbody.innerHTML = `<tr><td colspan="12" style="text-align: center; color: var(--text-muted); padding: 20px;">Không tìm thấy dữ liệu phù hợp.</td></tr>`;
        renderTop3DDPagination();
        return;
    }

    pageItems.forEach((row) => {
        const isHeadHit = row.result_head_1day.includes('TRÚNG');
        const isTailHit = row.result_tail_1day.includes('TRÚNG');
        const isCombHit = row.result_combined_1day.includes('TRÚNG');
        const isF3Hit = row.result_combined_3day.includes('TRÚNG');

        const headBadge = isHeadHit ? `<span class="tag tag-gold">${row.result_head_1day}</span>` : `<span class="tag tag-silver" style="opacity: 0.6;">${row.result_head_1day}</span>`;
        const tailBadge = isTailHit ? `<span class="tag tag-cyan">${row.result_tail_1day}</span>` : `<span class="tag tag-silver" style="opacity: 0.6;">${row.result_tail_1day}</span>`;
        const combBadge = isCombHit ? `<span class="tag tag-gold" style="font-weight: bold; background: #9C0006; color: #FFF;">${row.result_combined_1day}</span>` : `<span class="tag tag-silver" style="opacity: 0.6;">${row.result_combined_1day}</span>`;
        const f3Badge = isF3Hit ? `<span class="tag tag-green">${row.result_combined_3day}</span>` : `<span class="tag tag-silver" style="opacity: 0.6;">${row.result_combined_3day}</span>`;

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${row.stt}</td>
            <td><strong>${row.date}</strong></td>
            <td>${row.db}</td>
            <td><strong style="color: #FFF;">${row.de}</strong></td>
            <td>Đầu ${row.head} / Đuôi ${row.tail}</td>
            <td>${row.pred_heads}</td>
            <td>${headBadge}</td>
            <td>${row.pred_tails}</td>
            <td>${tailBadge}</td>
            <td style="font-size: 11px; color: var(--gold);">${row.pred_9_nums}</td>
            <td>${combBadge}</td>
            <td>${f3Badge}</td>
        `;
        tbody.appendChild(tr);
    });

    renderTop3DDPagination();
}

function renderTop3DDPagination() {
    const container = document.getElementById('paginationTop3DDArea');
    if (!container) return;
    container.innerHTML = '';
    const totalPages = Math.ceil(filteredTop3DDData.length / pageSizeTop3DD);
    if (totalPages <= 1) return;

    const prevBtn = document.createElement('button');
    prevBtn.className = `page-btn ${currentPageTop3DD === 1 ? 'disabled' : ''}`;
    prevBtn.textContent = '«';
    prevBtn.onclick = () => {
        if (currentPageTop3DD > 1) {
            currentPageTop3DD--;
            renderTop3DDTable();
        }
    };
    container.appendChild(prevBtn);

    let startP = Math.max(1, currentPageTop3DD - 3);
    let endP = Math.min(totalPages, startP + 6);

    for (let p = startP; p <= endP; p++) {
        const pageBtn = document.createElement('button');
        pageBtn.className = `page-btn ${p === currentPageTop3DD ? 'active' : ''}`;
        pageBtn.textContent = p;
        pageBtn.onclick = () => {
            currentPageTop3DD = p;
            renderTop3DDTable();
        };
        container.appendChild(pageBtn);
    }

    const nextBtn = document.createElement('button');
    nextBtn.className = `page-btn ${currentPageTop3DD === totalPages ? 'disabled' : ''}`;
    nextBtn.textContent = '»';
    nextBtn.onclick = () => {
        if (currentPageTop3DD < totalPages) {
            currentPageTop3DD++;
            renderTop3DDTable();
        }
    };
    container.appendChild(nextBtn);
}

function setupEventListeners() {
    if (document.getElementById('searchTop3DDInput')) {
        document.getElementById('searchTop3DDInput').addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase().trim();
            if (summaryData && summaryData.history_top3_dau_duoi_records) {
                filteredTop3DDData = summaryData.history_top3_dau_duoi_records.filter((row) => {
                    return row.date.toLowerCase().includes(query) ||
                           row.de.includes(query) ||
                           row.pred_heads.toLowerCase().includes(query) ||
                           row.pred_tails.toLowerCase().includes(query) ||
                           row.pred_9_nums.includes(query) ||
                           row.result_head_1day.toLowerCase().includes(query) ||
                           row.result_tail_1day.toLowerCase().includes(query) ||
                           row.result_combined_1day.toLowerCase().includes(query);
                });
                currentPageTop3DD = 1;
                renderTop3DDTable();
            }
        });
    }

    document.getElementById('searchFrame3Input').addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();
        if (summaryData && summaryData.frame3_records) {
            filteredFrame3Data = summaryData.frame3_records.filter((row) => {
                return row.start_date.toLowerCase().includes(query) ||
                       row.de_n1.includes(query) ||
                       row.de_n2.includes(query) ||
                       row.de_n3.includes(query) ||
                       row.pred_nums.includes(query) ||
                       row.frame_result.toLowerCase().includes(query);
            });
            currentPageFrame3 = 1;
            renderFrame3Table();
        }
    });

    document.getElementById('searchInput').addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();
        filteredRawData = rawData2026.filter((row) => {
            return row.date.toLowerCase().includes(query) ||
                   row.db.includes(query) ||
                   row.de.includes(query) ||
                   row.g7_1.includes(query) ||
                   row.g7_2.includes(query) ||
                   row.g7_3.includes(query) ||
                   row.g7_4.includes(query);
        });
        currentPageData = 1;
        renderDataTable();
    });
    
    const btnAll = document.getElementById('btnFilterAll');
    const btnTop10 = document.getElementById('btnFilterTop10');
    
    btnAll.addEventListener('click', () => {
        btnAll.classList.add('active');
        btnTop10.classList.remove('active');
        if (summaryData && summaryData.top_20_consensus) renderTop20Table(summaryData.top_20_consensus);
    });
    
    btnTop10.addEventListener('click', () => {
        btnTop10.classList.add('active');
        btnAll.classList.remove('active');
        if (summaryData && summaryData.top_20_consensus) renderTop20Table(summaryData.top_20_consensus.slice(0, 10));
    });
}

function setupLucky26FilterEvents() {
    const chamBtns = document.querySelectorAll('.cham-btn');
    const tongBtns = document.querySelectorAll('.tong-btn');

    chamBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const val = parseInt(btn.dataset.val);
            if (selectedChams.has(val)) {
                selectedChams.delete(val);
                btn.classList.remove('active');
            } else {
                selectedChams.add(val);
                btn.classList.add('active');
            }
            updateLucky26Filter();
        });
    });

    tongBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const val = parseInt(btn.dataset.val);
            if (selectedTongs.has(val)) {
                selectedTongs.delete(val);
                btn.classList.remove('active');
            } else {
                selectedTongs.add(val);
                btn.classList.add('active');
            }
            updateLucky26Filter();
        });
    });

    document.getElementById('btnSuggestG7').addEventListener('click', () => {
        selectedChams.clear();
        selectedTongs.clear();
        
        chamBtns.forEach(b => b.classList.remove('active'));
        tongBtns.forEach(b => b.classList.remove('active'));
        
        if (summaryData && summaryData.suggested_g7_cham) {
            summaryData.suggested_g7_cham.forEach(c => {
                selectedChams.add(c);
                const btn = document.querySelector(`.cham-btn[data-val="${c}"]`);
                if (btn) btn.classList.add('active');
            });
        }
        
        if (summaryData && summaryData.suggested_g7_tongs) {
            summaryData.suggested_g7_tongs.forEach(t => {
                selectedTongs.add(t);
                const btn = document.querySelector(`.tong-btn[data-val="${t}"]`);
                if (btn) btn.classList.add('active');
            });
        }
        
        updateLucky26Filter();
    });

    document.getElementById('btnSelectTop10').addEventListener('click', () => {
        selectedChams.clear();
        selectedTongs.clear();
        
        chamBtns.forEach(b => b.classList.remove('active'));
        tongBtns.forEach(b => b.classList.remove('active'));

        if (summaryData && summaryData.top_10_ha_so) {
            summaryData.top_10_ha_so.forEach(item => {
                const d1 = parseInt(item.number[0]);
                const d2 = parseInt(item.number[1]);
                const t = (d1 + d2) % 10;
                selectedChams.add(d1);
                selectedChams.add(d2);
                selectedTongs.add(t);
            });

            selectedChams.forEach(c => {
                const btn = document.querySelector(`.cham-btn[data-val="${c}"]`);
                if (btn) btn.classList.add('active');
            });
            selectedTongs.forEach(t => {
                const btn = document.querySelector(`.tong-btn[data-val="${t}"]`);
                if (btn) btn.classList.add('active');
            });
        }

        updateLucky26Filter();
    });

    document.getElementById('btnResetLuckyFilter').addEventListener('click', () => {
        selectedChams.clear();
        selectedTongs.clear();
        
        chamBtns.forEach(b => b.classList.remove('active'));
        tongBtns.forEach(b => b.classList.remove('active'));
        
        updateLucky26Filter();
    });
}

function updateLucky26Filter() {
    if (!summaryData) return;

    // Update badges
    const chamBadge = document.getElementById('chamCountBadge');
    const tongBadge = document.getElementById('tongCountBadge');

    if (selectedChams.size === 0) {
        chamBadge.textContent = 'Đã chọn: Tất cả (Chưa lọc)';
    } else {
        chamBadge.textContent = `Đã chọn: Chạm ${Array.from(selectedChams).sort((a,b)=>a-b).join(', ')}`;
    }

    if (selectedTongs.size === 0) {
        tongBadge.textContent = 'Đã chọn: Tất cả (Chưa lọc)';
    } else {
        tongBadge.textContent = `Đã chọn: Tổng ${Array.from(selectedTongs).sort((a,b)=>a-b).join(', ')}`;
    }

    const candidatePool = summaryData.top_20_consensus || [];
    const origCount = candidatePool.length;

    const filtered = candidatePool.filter(item => {
        const d1 = parseInt(item.number[0]);
        const d2 = parseInt(item.number[1]);
        const t = (d1 + d2) % 10;

        const matchCham = selectedChams.size === 0 || (selectedChams.has(d1) || selectedChams.has(d2));
        const matchTong = selectedTongs.size === 0 || selectedTongs.has(t);

        return matchCham && matchTong;
    });

    const reducedCount = filtered.length;
    const savingsPercent = origCount > 0 ? ((1 - reducedCount / origCount) * 100).toFixed(0) : 0;

    document.getElementById('filterOriginalCount').textContent = `${origCount} số`;
    document.getElementById('filterReducedCount').textContent = `${reducedCount} số`;
    document.getElementById('filterSavingsRate').textContent = `${savingsPercent}%`;

    // Estimate rate based on frame size
    let estRate = "87.50%";
    if (reducedCount <= 8) estRate = "~71.2%";
    else if (reducedCount <= 12) estRate = "~76.8%";
    else if (reducedCount <= 16) estRate = "~82.4%";

    document.getElementById('filterEstRate').textContent = estRate;

    // Render cards
    const grid = document.getElementById('filteredCardsGrid');
    grid.innerHTML = '';

    if (filtered.length === 0) {
        grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 20px;">Không có con số nào thỏa mãn đồng thời Chạm & Tổng đã chọn. Thử bấm "Gợi Ý Chạm/Tổng G7".</div>`;
        return;
    }

    filtered.forEach((item, idx) => {
        const isTop10 = idx < 10;
        const d1 = item.number[0];
        const d2 = item.number[1];
        const t = (parseInt(d1) + parseInt(d2)) % 10;

        const card = document.createElement('div');
        card.className = `num-card ${isTop10 ? 'top10-card' : ''}`;
        card.innerHTML = `
            <div class="num-card-header">
                <span>Top ${idx + 1}</span>
                <span>Tổng ${t}</span>
            </div>
            <div class="num-card-val">${item.number}</div>
            <div class="num-card-score">${item.lucky26_score || item.score} đ</div>
            <div class="num-card-tags">
                <span class="num-tag ${isTop10 ? 'manh' : 'trungbinh'}">${isTop10 ? 'MẠNH' : 'TRUNG BÌNH'}</span>
                <span class="num-tag">Chạm ${d1},${d2}</span>
            </div>
        `;
        grid.appendChild(card);
    });
}

