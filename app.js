/**
 * XSMB AI PREDICTION 2026 - MINI APP CONTROLLER
 * Auto-fetches analysis_summary.json and dynamically renders statistics, 
 * predictions, frame history, and live 2D filtering tool.
 */

let appData = null;

document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

async function initApp() {
    try {
        const response = await fetch('analysis_summary.json?t=' + Date.now());
        if (!response.ok) throw new Error('Không thể tải dữ liệu analysis_summary.json');
        appData = await response.json();
        
        renderHeaderAndHero();
        renderTabFrame3Day();
        renderTabTop20AndFilter();
        renderTabTop3DauDuoi();
        renderTabTop3D4D();
        renderTabStatsG7();
        
        setupEventListeners();
    } catch (error) {
        console.error('Lỗi nạp dữ liệu Mini App:', error);
        showToast('❌ Lỗi nạp dữ liệu: ' + error.message, 'error');
    }
}

// 1. RENDER HEADER & HERO STATS
function renderHeaderAndHero() {
    if (!appData) return;
    
    const lastDateEl = document.getElementById('heroLastDate');
    if (lastDateEl) lastDateEl.textContent = appData.last_date || 'N/A';
    
    const totalDaysEl = document.getElementById('heroTotalDays');
    if (totalDaysEl) totalDaysEl.textContent = (appData.total_days || 235) + ' Kỳ';
    
    if (appData.frame3_summary) {
        const frameRateEl = document.getElementById('heroFrameRate');
        if (frameRateEl) frameRateEl.textContent = (appData.frame3_summary.frame_hit_rate || 87.50) + '%';
        
        const n2n3RateEl = document.getElementById('heroN2N3Rate');
        if (n2n3RateEl) n2n3RateEl.textContent = (appData.frame3_summary.n2_n3_super_rate_when_miss_n1 || 44.53) + '%';
    }
}

// 2. TAB 1: KHUNG NUÔI 3 NGÀY & DÀN GỐC N1
function renderTabFrame3Day() {
    if (!appData) return;
    
    let n1List = [];
    let n2List = [];
    let stlPair = '17, 19';
    
    if (appData.frame3_records && appData.frame3_records.length > 0) {
        const latestFrame = appData.frame3_records[appData.frame3_records.length - 1];
        if (latestFrame.pred_n1) {
            n1List = latestFrame.pred_n1.split(',').map(s => s.trim()).filter(Boolean);
        }
        if (latestFrame.pred_n2) {
            n2List = latestFrame.pred_n2.split(',').map(s => s.trim()).filter(Boolean);
        }
        if (latestFrame.stl_pair) {
            stlPair = latestFrame.stl_pair;
        }
    }
    
    // Fallback using lucky26_matrix_100 if frame record pred_n1 was empty
    if (n1List.length === 0 && appData.lucky26_matrix_100) {
        n1List = appData.lucky26_matrix_100.slice(0, 60).map(x => x.number);
    }
    if (n2List.length === 0 && appData.lucky26_matrix_100) {
        n2List = appData.lucky26_matrix_100.slice(0, 28).map(x => x.number);
    }

    // Render Dàn Gốc N1 (60 Số)
    const gridN1 = document.getElementById('gridN1Numbers');
    if (gridN1) {
        gridN1.innerHTML = '';
        n1List.forEach(num => {
            const tag = document.createElement('div');
            tag.className = 'num-tag cyan';
            tag.textContent = num;
            gridN1.appendChild(tag);
        });
    }
    
    const countN1 = document.getElementById('countN1Label');
    if (countN1) countN1.textContent = `${n1List.length} số`;
    window.currentN1List = n1List.join(' ');
    
    // Render Dàn Siêu Lọc N2 & N3 (28 Số)
    const gridN2 = document.getElementById('gridN2Numbers');
    if (gridN2) {
        gridN2.innerHTML = '';
        n2List.forEach(num => {
            const tag = document.createElement('div');
            tag.className = 'num-tag gold';
            tag.textContent = num;
            gridN2.appendChild(tag);
        });
    }
    
    const countN2 = document.getElementById('countN2Label');
    if (countN2) countN2.textContent = `${n2List.length} số`;
    window.currentN2List = n2List.join(' ');

    // Render Song Thủ Lô Rơi
    const stlEl = document.getElementById('stlPairLabel');
    if (stlEl) stlEl.textContent = stlPair;

    // Render History Table 3-Day Frames (Last 20 frames)
    const tbody = document.getElementById('tbodyFrameHistory');
    if (tbody && appData.frame3_records) {
        tbody.innerHTML = '';
        const recentFrames = appData.frame3_records.slice(-20).reverse();
        
        recentFrames.forEach(rec => {
            const tr = document.createElement('tr');
            const isHit = rec.frame_result && rec.frame_result.includes('TRÚNG');
            const resTag = isHit 
                ? `<span class="tag-hit">TRÚNG (${rec.frame_result.split(' ')[1] || 'KHUNG'})</span>` 
                : `<span class="tag-miss">TRƯỢT</span>`;
            
            tr.innerHTML = `
                <td><strong>#${rec.stt}</strong></td>
                <td>${rec.start_date}</td>
                <td>${rec.de_n1} <span class="${rec.hit_n1 === 'Trúng' || rec.hit_n1 === 'TRÚNG' ? 'tag-hit' : 'tag-miss'}">${rec.hit_n1}</span></td>
                <td>${rec.de_n2} <span class="${rec.hit_n2 === 'Trúng' || rec.hit_n2 === 'TRÚNG' ? 'tag-hit' : 'tag-miss'}">${rec.hit_n2}</span></td>
                <td>${rec.de_n3} <span class="${rec.hit_n3 === 'Trúng' || rec.hit_n3 === 'TRÚNG' ? 'tag-hit' : 'tag-miss'}">${rec.hit_n3}</span></td>
                <td>${rec.stl_pair} <span class="${rec.stl_hit && rec.stl_hit.includes('TRÚNG') ? 'tag-hit' : 'tag-miss'}">${rec.stl_hit}</span></td>
                <td>${resTag}</td>
            `;
            tbody.appendChild(tr);
        });
    }
}

// 3. TAB 2: TOP 20 SUPER-SCORE & BỘ LỌC 2D LIVE
function renderTabTop20AndFilter() {
    if (!appData) return;
    
    // Top 20 Super-Score Grid / Cards
    const containerTop20 = document.getElementById('gridTop20Cards');
    if (containerTop20) {
        containerTop20.innerHTML = '';
        const top20List = appData.top_20_consensus || [];
        
        top20List.slice(0, 20).forEach((item, idx) => {
            const card = document.createElement('div');
            card.className = 'num-tag gold';
            card.style.padding = '10px 6px';
            card.style.fontSize = '15px';
            card.innerHTML = `<div>Top ${idx+1}</div><strong>${item.number}</strong><div style="font-size:10px; color:#94A3B8;">${item.score.toFixed(1)}đ</div>`;
            containerTop20.appendChild(card);
        });
        
        window.currentTop20List = top20List.slice(0, 20).map(x => x.number).join(' ');
    }
    
    // Setup Live 2D Filter
    filter2DMatrix();
}

function filter2DMatrix() {
    const inputCham = document.getElementById('filterChamInput')?.value.trim() || '0123456789';
    const inputTong = document.getElementById('filterTongInput')?.value.trim() || '0123456789';
    
    const chamDigits = inputCham.split('').filter(c => c >= '0' && c <= '9');
    const tongDigits = inputTong.split('').filter(c => c >= '0' && c <= '9');
    
    const filteredList = [];
    for (let i = 0; i < 100; i++) {
        const numStr = String(i).padStart(2, '0');
        const d1 = parseInt(numStr[0]);
        const d2 = parseInt(numStr[1]);
        const sumMod = (d1 + d2) % 10;
        
        const matchCham = chamDigits.length === 0 || chamDigits.includes(String(d1)) || chamDigits.includes(String(d2));
        const matchTong = tongDigits.length === 0 || tongDigits.includes(String(sumMod));
        
        if (matchCham && matchTong) {
            filteredList.push(numStr);
        }
    }
    
    const gridFiltered = document.getElementById('grid2DFiltered');
    if (gridFiltered) {
        gridFiltered.innerHTML = '';
        filteredList.forEach(num => {
            const tag = document.createElement('div');
            tag.className = 'num-tag cyan';
            tag.textContent = num;
            gridFiltered.appendChild(tag);
        });
    }
    
    const countLabel = document.getElementById('count2DFiltered');
    if (countLabel) countLabel.textContent = `${filteredList.length} số`;
    window.current2DFilteredList = filteredList.join(' ');
}

// 4. TAB 3: TOP 3 ĐẦU / TOP 3 ĐUÔI & DÀN 9 SỐ & ĐIỂM PHỤC HỒI
function renderTabTop3DauDuoi() {
    if (!appData || !appData.top3_dau_duoi_summary) return;
    
    const summaryDD = appData.top3_dau_duoi_summary;
    
    const rawHeads = (appData.top_predicted_heads || []).slice(0, 3);
    const rawTails = (appData.top_predicted_tails || []).slice(0, 3);

    const headNames = rawHeads.map(item => (typeof item === 'object' && item.head) ? item.head : String(item));
    const tailNames = rawTails.map(item => (typeof item === 'object' && item.tail) ? item.tail : String(item));

    const top3HeadStr = headNames.length > 0 ? headNames.join(' - ') : 'Đầu 2 - Đầu 1 - Đầu 3';
    const top3TailStr = tailNames.length > 0 ? tailNames.join(' - ') : 'Đuôi 3 - Đuôi 7 - Đuôi 8';
    
    const headEl = document.getElementById('lblTop3Head');
    if (headEl) headEl.textContent = top3HeadStr;
    
    const tailEl = document.getElementById('lblTop3Tail');
    if (tailEl) tailEl.textContent = top3TailStr;
    
    // Construct 9-number set (Head x Tail)
    const headDigits = rawHeads.map(item => {
        const val = (typeof item === 'object' && item.head) ? item.head : String(item);
        return val.replace(/\D/g, '');
    }).filter(Boolean);

    const tailDigits = rawTails.map(item => {
        const val = (typeof item === 'object' && item.tail) ? item.tail : String(item);
        return val.replace(/\D/g, '');
    }).filter(Boolean);

    const dan9List = [];
    headDigits.forEach(h => {
        tailDigits.forEach(t => {
            dan9List.push(`${h}${t}`);
        });
    });
    
    const grid9 = document.getElementById('gridDan9Numbers');
    if (grid9) {
        grid9.innerHTML = '';
        dan9List.forEach(num => {
            const tag = document.createElement('div');
            tag.className = 'num-tag purple';
            tag.textContent = num;
            grid9.appendChild(tag);
        });
    }
    window.currentDan9List = dan9List.join(' ');

    const h1n = document.getElementById('rateHead1N');
    if (h1n) h1n.textContent = (summaryDD.head_rate_1day || 28.63) + '%';
    
    const h3n = document.getElementById('rateHead3N');
    if (h3n) h3n.textContent = (summaryDD.f3_head_rate || 69.83) + '%';
    
    const t1n = document.getElementById('rateTail1N');
    if (t1n) t1n.textContent = (summaryDD.tail_rate_1day || 25.64) + '%';
    
    const t3n = document.getElementById('rateTail3N');
    if (t3n) t3n.textContent = (summaryDD.f3_tail_rate || 61.64) + '%';

    // Render Table Recovery Scoring Breakdown
    const tbodyRec = document.getElementById('tbodyRecoveryScoring');
    if (tbodyRec) {
        tbodyRec.innerHTML = '';
        
        const renderRows = (listData, typeLabel) => {
            listData.forEach(([digit, info]) => {
                const tr = document.createElement('tr');
                
                const isRecovery = info.recovery_bonus > 0;
                const statusTag = isRecovery 
                    ? `<span class="tag-hit" style="background:rgba(245, 158, 11, 0.25); border-color:rgba(245, 158, 11, 0.5); color:#FBBF24;">Ngưỡng Phục Hồi 🔥</span>` 
                    : (info.penalty > 0 ? `<span class="tag-miss">Bão Hòa (Mới Ra)</span>` : `<span class="tag-info">${info.status_label || 'Bình Thường'}</span>`);
                
                const recBonusCell = isRecovery 
                    ? `<strong style="color:#FBBF24;">+${info.recovery_bonus.toFixed(1)}đ</strong>` 
                    : `<span style="color:#64748B;">0.0đ</span>`;

                const penaltyCell = info.penalty > 0 
                    ? `<span style="color:#FB7185;">-${info.penalty.toFixed(1)}đ</span>` 
                    : `<span style="color:#64748B;">0.0đ</span>`;

                tr.innerHTML = `
                    <td><strong>${typeLabel} ${digit}</strong></td>
                    <td>${typeLabel}</td>
                    <td>${info.freq_30d} lần</td>
                    <td>${info.nhip} ngày</td>
                    <td>${penaltyCell}</td>
                    <td>${recBonusCell}</td>
                    <td><strong style="color:#67E8F9;">${info.total_score.toFixed(1)}đ</strong></td>
                    <td>${statusTag}</td>
                `;
                tbodyRec.appendChild(tr);
            });
        };

        if (appData.head_scoring_breakdown) renderRows(appData.head_scoring_breakdown, 'Đầu');
        if (appData.tail_scoring_breakdown) renderRows(appData.tail_scoring_breakdown, 'Đuôi');
    }
}

// 5. TAB 4: TOP 20 BA CÀNG (3D) & BỐN CÀNG (4D) & BẢNG THỐNG KÊ LỊCH SỬ
function renderTabTop3D4D() {
    if (!appData) return;
    
    // Top 20 3D
    const list3D = appData.top_20_3d || [];
    const container3D = document.getElementById('grid3DList');
    if (container3D) {
        container3D.innerHTML = '';
        list3D.slice(0, 20).forEach((item, idx) => {
            const tag = document.createElement('div');
            tag.className = 'num-tag gold';
            tag.style.fontSize = '13px';
            tag.style.padding = '6px';
            tag.innerHTML = `<strong>${item.number_3d}</strong>`;
            container3D.appendChild(tag);
        });
        window.current3DList = list3D.slice(0, 20).map(x => x.number_3d).join(' ');
    }

    // Top 20 4D
    const list4D = appData.top_20_4d || [];
    const container4D = document.getElementById('grid4DList');
    if (container4D) {
        container4D.innerHTML = '';
        list4D.slice(0, 20).forEach((item, idx) => {
            const tag = document.createElement('div');
            tag.className = 'num-tag purple';
            tag.style.fontSize = '12px';
            tag.style.padding = '6px';
            tag.innerHTML = `<strong>${item.number_4d}</strong>`;
            container4D.appendChild(tag);
        });
        window.current4DList = list4D.slice(0, 20).map(x => x.number_4d).join(' ');
    }

    // Thống kê Tỷ lệ Trúng 3D & 4D Lịch sử
    const recs = appData.history_3d_4d_records || [];
    const totalEvals = recs.length || 1;
    const hit3DCount = recs.filter(r => r.result_3d_top20 && r.result_3d_top20.includes('TRÚNG')).length;
    const hit4DCount = recs.filter(r => r.result_4d && r.result_4d.includes('TRÚNG')).length;

    const rate3D = ((hit3DCount / totalEvals) * 100).toFixed(2);
    const rate4D = ((hit4DCount / totalEvals) * 100).toFixed(2);

    const el3DRate = document.getElementById('stat3DRate');
    if (el3DRate) el3DRate.textContent = `${rate3D}%`;

    const el3DHits = document.getElementById('stat3DHits');
    if (el3DHits) el3DHits.textContent = `${hit3DCount}/${totalEvals}`;

    const el4DRate = document.getElementById('stat4DRate');
    if (el4DRate) el4DRate.textContent = `${rate4D}%`;

    const el4DHits = document.getElementById('stat4DHits');
    if (el4DHits) el4DHits.textContent = `${hit4DCount}/${totalEvals}`;

    // Render Bảng Lịch Sử Kiểm Chứng (20 kỳ gần nhất)
    const tbody = document.getElementById('tbody3D4DHistory');
    if (tbody && recs.length > 0) {
        tbody.innerHTML = '';
        const recentRecs = recs.slice(-20).reverse();
        recentRecs.forEach(rec => {
            const tr = document.createElement('tr');
            const isHit3D = rec.result_3d_top20 && rec.result_3d_top20.includes('TRÚNG');
            const isHit4D = rec.result_4d && rec.result_4d.includes('TRÚNG');

            const tag3D = isHit3D ? `<span class="tag-hit">TRÚNG 🎯</span>` : `<span class="tag-miss">TRƯỢT ❌</span>`;
            const tag4D = isHit4D ? `<span class="tag-hit">TRÚNG 🎯</span>` : `<span class="tag-miss">TRƯỢT ❌</span>`;

            tr.innerHTML = `
                <td><strong>#${rec.stt}</strong></td>
                <td>${rec.date}</td>
                <td><strong>${rec.db}</strong></td>
                <td><strong style="color: #FBBF24;">${rec.actual_3d || '---'}</strong></td>
                <td>${tag3D}</td>
                <td><strong style="color: #C084FC;">${rec.actual_4d || '---'}</strong></td>
                <td>${tag4D}</td>
            `;
            tbody.appendChild(tr);
        });
    }
}

// 6. TAB 5: THỐNG KÊ G7 & MỐC KHUNG THỜI GIAN & DỰ ĐOÁN NỔ THEO THỨ
function renderTabStatsG7() {
    if (!appData) return;
    
    // Render High-Confidence Day-of-Week Burst Prediction Card
    if (appData.dow_model) {
        const dowM = appData.dow_model;
        
        const nextDayEl = document.getElementById('lblDowNextDay');
        if (nextDayEl) nextDayEl.textContent = dowM.next_dow_name || 'Thứ Sáu';

        const g7PosEl = document.getElementById('lblDowG7Pos');
        if (g7PosEl) {
            const positions = (dowM.top2_next_g || ['g7_1', 'g7_4']).map(p => p.toUpperCase().replace('_', '.'));
            g7PosEl.textContent = positions.join(' & ');
        }

        const targetSumsEl = document.getElementById('lblDowTargetSums');
        if (targetSumsEl) {
            const sums = (dowM.next_target_sums || [8, 1, 3, 6]).map(s => 'Tổng ' + s);
            targetSumsEl.textContent = sums.join(', ');
        }

        const chamSetEl = document.getElementById('lblDowChamSet');
        if (chamSetEl) {
            chamSetEl.textContent = (dowM.next_cham_set || [0, 1, 2, 3, 5, 6, 7, 8]).join(', ');
        }

        const burstList = dowM.next_dan_ha_so || ['38', '83', '17', '33', '80', '79', '21', '26', '67', '47', '60', '10', '42', '65', '71', '01', '85', '97', '53', '51'];
        const gridBurst = document.getElementById('gridDowBurst20');
        if (gridBurst) {
            gridBurst.innerHTML = '';
            burstList.forEach(num => {
                const tag = document.createElement('div');
                tag.className = 'num-tag gold';
                tag.style.fontSize = '15px';
                tag.style.fontWeight = '800';
                tag.textContent = num;
                gridBurst.appendChild(tag);
            });
        }
        window.currentDowBurstList = burstList.join(' ');
    }

    // Render G7 & Móc chung Lô Predictions
    if (appData.g7_lo_predictions) {
        const loP = appData.g7_lo_predictions;
        const badgeStl = document.getElementById('badgeStlGocRate');
        if (badgeStl) badgeStl.textContent = `Tỷ Lệ Nổ Lô STL: ${loP.stl_goc_rate}%`;

        const lblStl = document.getElementById('lblStlGocNext');
        if (lblStl) lblStl.textContent = loP.stl_goc_next || '-- - --';

        const lblHits = document.getElementById('lblStlGocHits');
        if (lblHits) lblHits.textContent = `${loP.stl_goc_hits} kỳ`;

        const lblNhay = document.getElementById('lblStlGocNhay');
        if (lblNhay) lblNhay.textContent = `${loP.stl_goc_total_nhay} nháy`;

        const lblBtl = document.getElementById('lblBtlGocNext');
        if (lblBtl) lblBtl.textContent = loP.btl_goc_next || '--';

        const gridTopLo = document.getElementById('gridTopLoG7');
        if (gridTopLo && loP.top_lo_g7_moc_chung) {
            gridTopLo.innerHTML = '';
            loP.top_lo_g7_moc_chung.forEach(item => {
                const card = document.createElement('div');
                card.style.background = 'rgba(16, 185, 129, 0.12)';
                card.style.border = '1px solid rgba(52, 211, 153, 0.3)';
                card.style.borderRadius = '8px';
                card.style.padding = '8px 12px';
                card.style.textAlign = 'center';

                card.innerHTML = `
                    <div style="font-size: 18px; font-weight: 800; color: #34D399;">${item.number}</div>
                    <div style="font-size: 10px; color: #94A3B8;">${item.source}</div>
                    <div style="font-size: 11px; font-weight: 700; color: #FBBF24;">${item.score} điểm</div>
                `;
                gridTopLo.appendChild(card);
            });
        }
    }

    // Render G7 ranking for initial window (30 days)
    renderG7WindowStats('30');

    // Render Table Performance by DOW
    const tbody = document.getElementById('tbodyDowStats');
    if (tbody && appData.dow_stats) {
        tbody.innerHTML = '';
        Object.entries(appData.dow_stats).forEach(([dowName, st]) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${dowName}</strong></td>
                <td>${st.evals} ngày</td>
                <td>G7.1 & G7.3 (${st.cham_hits} trúng)</td>
                <td><span class="tag-hit">${st.cham_rate}%</span></td>
                <td><span class="tag-info">${st.inter_rate}%</span></td>
            `;
            tbody.appendChild(tr);
        });
    }
}

function renderG7WindowStats(windowKey) {
    if (!appData) return;
    
    const container = document.getElementById('gridG7RankingCards');
    if (!container) return;
    container.innerHTML = '';

    let rankings = [];
    let windowTitle = '';
    const totalDays = appData.total_days || 235;

    if (windowKey === 'all') {
        windowTitle = `Toàn Bộ Năm 2026 (${totalDays} Kỳ)`;
        if (appData.overall_g7_stats) {
            Object.entries(appData.overall_g7_stats).forEach(([gKey, val]) => {
                const hits = (val.td || 0) + (val.b || 0);
                const rate = ((hits / totalDays) * 100).toFixed(1);
                rankings.push({
                    position: gKey.toUpperCase().replace('_', '.'),
                    hits: hits,
                    rate: parseFloat(rate)
                });
            });
            rankings.sort((a, b) => b.hits - a.hits);
        }
    } else {
        const days = parseInt(windowKey) || 30;
        windowTitle = `Khung ${days} Ngày Gần Nhất`;
        if (appData.window_stats && appData.window_stats[windowKey]) {
            rankings = appData.window_stats[windowKey].g7_ranking || [];
        }
    }

    rankings.forEach((item, idx) => {
        const isExcluded = (idx === rankings.length - 1);
        const card = document.createElement('div');
        card.style.background = isExcluded ? 'rgba(244, 63, 94, 0.1)' : 'rgba(30, 41, 59, 0.6)';
        card.style.border = '1px solid ' + (isExcluded ? 'rgba(244, 63, 94, 0.3)' : (idx === 0 ? 'rgba(245, 158, 11, 0.4)' : 'rgba(255, 255, 255, 0.08)'));
        card.style.borderRadius = '12px';
        card.style.padding = '12px';
        card.style.textAlign = 'center';

        const rankTitle = isExcluded ? '❌ VỊ TRÍ LOẠI' : (idx === 0 ? '👑 TOP 1 PHONG ĐỘ' : `TOP ${idx+1}`);
        const rankColor = isExcluded ? '#FB7185' : (idx === 0 ? '#FBBF24' : '#67E8F9');

        card.innerHTML = `
            <div style="font-size: 11px; font-weight: 700; color: ${rankColor}; margin-bottom: 4px;">${rankTitle}</div>
            <div style="font-size: 18px; font-weight: 800; color: #F8FAFC;">${item.position}</div>
            <div style="font-size: 13px; font-weight: 700; color: #34D399; margin-top: 4px;">${item.hits} Lần Trúng</div>
            <div style="font-size: 11px; color: #94A3B8;">Tỷ lệ: ${item.rate}%</div>
        `;
        container.appendChild(card);
    });
}

// EVENT LISTENERS & COPY ACTIONS
function setupEventListeners() {
    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            btn.classList.add('active');
            const tabId = btn.getAttribute('data-tab');
            document.getElementById(tabId)?.classList.add('active');
        });
    });

    // Window Selector Buttons in Tab 5
    document.querySelectorAll('.window-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.window-btn').forEach(b => {
                b.classList.remove('active', 'btn-gold');
                b.classList.add('btn-secondary');
            });
            btn.classList.add('active', 'btn-gold');
            btn.classList.remove('btn-secondary');
            
            const windowKey = btn.getAttribute('data-window');
            renderG7WindowStats(windowKey);
        });
    });

    // Copy buttons
    document.getElementById('btnCopyN1')?.addEventListener('click', () => {
        copyToClipboard(window.currentN1List || '', 'Đã copy Dàn 60 Số N1 vào bộ nhớ tạm!');
    });

    document.getElementById('btnCopyN2')?.addEventListener('click', () => {
        copyToClipboard(window.currentN2List || '', 'Đã copy Dàn Siêu Lọc 28 Số N2/N3 vào bộ nhớ tạm!');
    });

    document.getElementById('btnCopyTop20')?.addEventListener('click', () => {
        copyToClipboard(window.currentTop20List || '', 'Đã copy Top 20 Super-Score!');
    });

    document.getElementById('btnCopyFiltered2D')?.addEventListener('click', () => {
        copyToClipboard(window.current2DFilteredList || '', 'Đã copy Dàn 2D đã lọc!');
    });

    document.getElementById('btnCopyDan9')?.addEventListener('click', () => {
        copyToClipboard(window.currentDan9List || '', 'Đã copy Dàn 9 Số!');
    });

    document.getElementById('btnCopy3D')?.addEventListener('click', () => {
        copyToClipboard(window.current3DList || '', 'Đã copy Top 20 Ba Càng (3D)!');
    });

    document.getElementById('btnCopy4D')?.addEventListener('click', () => {
        copyToClipboard(window.current4DList || '', 'Đã copy Top 20 Bốn Càng (4D)!');
    });

    document.getElementById('btnCopyDowBurst')?.addEventListener('click', () => {
        copyToClipboard(window.currentDowBurstList || '', 'Đã copy 20 Số Nổ Hỏa Lực Theo Thứ!');
    });

    // Filter inputs
    document.getElementById('filterChamInput')?.addEventListener('input', filter2DMatrix);
    document.getElementById('filterTongInput')?.addEventListener('input', filter2DMatrix);
}

function copyToClipboard(text, successMsg) {
    if (!text) {
        showToast('⚠️ Không có dữ liệu để copy', 'warn');
        return;
    }
    navigator.clipboard.writeText(text).then(() => {
        showToast('📋 ' + successMsg, 'success');
    }).catch(err => {
        showToast('❌ Copy thất bại', 'error');
    });
}

function showToast(message) {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(20px)';
        setTimeout(() => toast.remove(), 300);
    }, 2500);
}
