// State
let currentCampaigns = [];
let selectedCampaignId = null;
let currentStreams = [];
let offersCache = [];

// DOM Ready
document.addEventListener("DOMContentLoaded", () => {
  loadCampaigns();
  loadResources();
  initOfferAutocomplete();
});

// Toast notification
function showToast(message, type = "success") {
  const toast = document.getElementById("toast");
  const msgEl = document.getElementById("toast-msg");
  const iconEl = document.getElementById("toast-icon");

  msgEl.textContent = message;
  iconEl.innerHTML = type === "success" 
    ? '<i class="fa-solid fa-check-circle text-emerald-400"></i>' 
    : '<i class="fa-solid fa-triangle-exclamation text-rose-400"></i>';

  toast.classList.remove("translate-y-20", "opacity-0");
  setTimeout(() => {
    toast.classList.add("translate-y-20", "opacity-0");
  }, 4000);
}

// Navigation Tabs
function switchTab(tab) {
  const editorBtn = document.getElementById("tab-editor-btn");
  const creatorBtn = document.getElementById("tab-creator-btn");
  const editorSection = document.getElementById("editor-section");
  const creatorSection = document.getElementById("creator-section");

  if (tab === "creator") {
    creatorBtn.className = "px-4 py-2 text-sm font-semibold rounded-lg bg-indigo-50 text-indigo-700 transition";
    editorBtn.className = "px-4 py-2 text-sm font-semibold rounded-lg text-slate-600 hover:bg-slate-100 transition";
    creatorSection.classList.remove("hidden");
    editorSection.classList.add("hidden");
  } else {
    editorBtn.className = "px-4 py-2 text-sm font-semibold rounded-lg bg-indigo-50 text-indigo-700 transition";
    creatorBtn.className = "px-4 py-2 text-sm font-semibold rounded-lg text-slate-600 hover:bg-slate-100 transition";
    editorSection.classList.remove("hidden");
    creatorSection.classList.add("hidden");
  }
}

// Load domains, groups, sources
async function loadResources() {
  try {
    const [domains, groups, sources] = await Promise.all([
      fetch("/api/resources/domains").then(r => r.json()).catch(() => []),
      fetch("/api/resources/groups").then(r => r.json()).catch(() => []),
      fetch("/api/resources/traffic_sources").then(r => r.json()).catch(() => [])
    ]);

    const dSel = document.getElementById("c-domain-select");
    const gSel = document.getElementById("c-group-select");
    const sSel = document.getElementById("c-source-select");

    dSel.innerHTML = domains.map(d => `<option value="${d.id}">${d.name || d.id}</option>`).join("");
    gSel.innerHTML = groups.map(g => `<option value="${g.id}">${g.name || g.id}</option>`).join("");
    sSel.innerHTML = sources.map(s => `<option value="${s.id}">${s.name || s.id}</option>`).join("");
  } catch (err) {
    console.error("Failed to load Keitaro resources:", err);
  }
}

// Load campaigns list
async function loadCampaigns(selectIdToSet = null) {
  try {
    const res = await fetch("/api/campaigns");
    const data = await res.json();
    currentCampaigns = data;

    const select = document.getElementById("campaign-select");
    if (data.length === 0) {
      select.innerHTML = '<option value="">Нет созданных кампаний</option>';
      return;
    }

    select.innerHTML = '<option value="">-- Выберите кампанию --</option>' + 
      data.map(c => `<option value="${c.id}" ${c.id === selectIdToSet ? "selected" : ""}>[#${c.keitaro_id}] ${c.name} (${c.geo})</option>`).join("");

    if (selectIdToSet) {
      selectedCampaignId = selectIdToSet;
      loadSelectedCampaign();
    } else if (data.length > 0 && !selectedCampaignId) {
      selectedCampaignId = data[0].id;
      select.value = data[0].id;
      loadSelectedCampaign();
    }
  } catch (err) {
    showToast("Ошибка загрузки кампаний", "error");
  }
}

// Autocomplete for Creator tab
let searchTimeout = null;
function initOfferAutocomplete() {
  const searchInput = document.getElementById("c-offer-search");
  const dropdown = document.getElementById("c-offer-dropdown");
  const spinner = document.getElementById("c-offer-spinner");

  searchInput.addEventListener("input", (e) => {
    clearTimeout(searchTimeout);
    const q = e.target.value.trim();
    if (!q) {
      dropdown.classList.add("hidden");
      return;
    }

    spinner.classList.remove("hidden");
    searchTimeout = setTimeout(async () => {
      try {
        const res = await fetch(`/api/offers?query=${encodeURIComponent(q)}`);
        const offers = await res.json();
        spinner.classList.add("hidden");

        if (offers.length === 0) {
          dropdown.innerHTML = '<div class="p-3 text-xs text-slate-400 text-center">Офферы не найдены</div>';
        } else {
          dropdown.innerHTML = offers.map(o => `
            <div class="p-2.5 text-xs hover:bg-indigo-50 cursor-pointer transition flex items-center justify-between" onclick="selectOffer(${o.id}, '${escapeQuotes(o.name)}')">
              <span class="font-semibold text-slate-700">[${o.id}]</span>
              <span class="truncate ml-2 text-slate-600 flex-1">${o.name}</span>
            </div>
          `).join("");
        }
        dropdown.classList.remove("hidden");
      } catch (err) {
        spinner.classList.add("hidden");
      }
    }, 250);
  });

  document.addEventListener("click", (e) => {
    if (!searchInput.contains(e.target) && !dropdown.contains(e.target)) {
      dropdown.classList.add("hidden");
    }
  });
}

function escapeQuotes(str) {
  return (str || "").replace(/'/g, "\\'").replace(/"/g, "&quot;");
}

function selectOffer(id, name) {
  document.getElementById("c-offer-id").value = id;
  document.getElementById("c-offer-search").value = "";
  document.getElementById("c-offer-dropdown").classList.add("hidden");

  const badge = document.getElementById("c-selected-offer-badge");
  const text = document.getElementById("c-selected-offer-text");
  text.textContent = `[${id}] ${name}`;
  badge.classList.remove("hidden");
}

function clearSelectedOffer() {
  document.getElementById("c-offer-id").value = "";
  document.getElementById("c-selected-offer-badge").classList.add("hidden");
}

// Handle Campaign Creation
async function handleCreateCampaign(e) {
  e.preventDefault();
  const name = document.getElementById("c-name").value.trim();
  const geo = document.getElementById("c-geo").value.trim();
  const offerId = document.getElementById("c-offer-id").value;
  const domainId = document.getElementById("c-domain-select").value || null;
  const groupId = document.getElementById("c-group-select").value || null;
  const sourceId = document.getElementById("c-source-select").value || null;

  if (!offerId) {
    showToast("Пожалуйста, выберите оффер из списка с автокомплитом", "error");
    return;
  }

  const btn = document.getElementById("c-submit-btn");
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin mr-2"></i> Создание в Keitaro...';

  try {
    const res = await fetch("/api/campaigns", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        geo,
        offer_id: parseInt(offerId),
        domain_id: domainId ? parseInt(domainId) : null,
        group_id: groupId ? parseInt(groupId) : null,
        traffic_source_id: sourceId ? parseInt(sourceId) : null
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Ошибка создания кампании");
    }

    const created = await res.json();
    showToast(`Кампания "${name}" успешно создана в Keitaro! (ID: ${created.keitaro_id})`);

    // Reset form
    document.getElementById("creator-form").reset();
    clearSelectedOffer();

    // Switch to editor
    await loadCampaigns(created.id);
    switchTab("editor");
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>Create</span>';
  }
}

// Load selected campaign & render streams
async function loadSelectedCampaign() {
  const select = document.getElementById("campaign-select");
  selectedCampaignId = select.value ? parseInt(select.value) : null;

  const container = document.getElementById("streams-container");
  const metaBadge = document.getElementById("campaign-meta-badge");

  if (!selectedCampaignId) {
    container.innerHTML = `
      <div id="no-campaign-alert" class="text-center py-12 bg-white rounded-xl border border-dashed border-slate-300">
        <i class="fa-solid fa-layer-group text-4xl text-slate-300 mb-3"></i>
        <p class="text-slate-500 font-medium">Выберите кампанию из списка выше</p>
      </div>
    `;
    metaBadge.classList.add("hidden");
    return;
  }

  const camp = currentCampaigns.find(c => c.id === selectedCampaignId);
  if (camp) {
    document.getElementById("meta-keitaro-id").textContent = camp.keitaro_id;
    document.getElementById("meta-geo").textContent = camp.geo;
    metaBadge.classList.remove("hidden");
  }

  try {
    const res = await fetch(`/api/campaigns/${selectedCampaignId}`);
    const data = await res.json();
    renderStreams(data.streams || []);
  } catch (err) {
    showToast("Не удалось загрузить данные кампании", "error");
  }
}

// Fetch streams directly from Keitaro
async function fetchStreamsForCurrentCampaign() {
  if (!selectedCampaignId) return;
  const btn = document.getElementById("fetch-streams-btn");
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-arrows-rotate fa-spin"></i> <span>Синхронизация...</span>';

  try {
    const res = await fetch(`/api/campaigns/${selectedCampaignId}/fetch_streams`, { method: "POST" });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Ошибка получения потоков");
    }
    const streams = await res.json();
    renderStreams(streams);
    showToast("Потоки успешно синхронизированы с Keitaro!");
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i> <span>Fetch streams</span>';
  }
}

// Render streams cards
function renderStreams(streams) {
  const container = document.getElementById("streams-container");
  currentStreams = streams;

  if (streams.length === 0) {
    container.innerHTML = `
      <div class="text-center py-12 bg-white rounded-xl border border-dashed border-slate-300">
        <p class="text-slate-500">В этой кампании нет потоков. Нажмите "Fetch streams" для синхронизации.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = streams.map(s => {
    const isOffersStream = s.schema === "landings" || s.offers.length > 0;
    const isDirty = s.is_dirty;
    const cardBgClass = isDirty ? "stream-dirty border-yellow-400" : "stream-clean border-slate-200";

    if (!isOffersStream) {
      // Flow 1 / Redirect Flow
      return `
        <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-5 transition">
          <div class="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
            <div class="flex items-center gap-2.5">
              <span class="w-3 h-3 rounded-full bg-emerald-500 inline-block"></span>
              <h3 class="font-bold text-slate-800 text-base">${s.name} <span class="text-xs font-normal text-slate-400">[#${s.keitaro_stream_id}]</span></h3>
              <span class="bg-blue-50 text-blue-700 text-xs px-2.5 py-0.5 rounded-full font-semibold uppercase">Редирект на Google</span>
            </div>
            <div class="text-xs text-slate-400">Позиция: ${s.position}</div>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-slate-600 bg-slate-50 p-4 rounded-lg">
            <div>
              <span class="font-bold text-slate-500 block mb-1">Действие редиректа:</span>
              <a href="https://google.com" target="_blank" class="text-indigo-600 hover:underline font-mono">https://google.com</a>
            </div>
            <div>
              <span class="font-bold text-slate-500 block mb-1">Фильтры потока:</span>
              <span class="text-slate-700">Перехват трафика из заданной страны (AU / указанной в Geo)</span>
            </div>
          </div>
        </div>
      `;
    }

    // Flow 2 / Offers Flow
    return `
      <div class="rounded-xl shadow-sm border ${cardBgClass} p-5 transition">
        <!-- Header -->
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-4 mb-4 ${isDirty ? "border-yellow-200" : "border-slate-100"}">
          <div class="flex items-center gap-2.5">
            <span class="w-3 h-3 rounded-full bg-emerald-500 inline-block"></span>
            <div>
              <h3 class="font-bold text-slate-800 text-base flex items-center gap-2">
                ${s.name}
                <span class="text-xs font-normal text-slate-400">[#${s.keitaro_stream_id}]</span>
                ${isDirty 
                  ? '<span class="bg-yellow-100 text-yellow-800 text-xs px-2.5 py-0.5 rounded-full font-bold border border-yellow-300">Не опубликовано</span>' 
                  : '<span class="bg-emerald-50 text-emerald-700 text-xs px-2.5 py-0.5 rounded-full font-semibold border border-emerald-200">Синхронизировано</span>'
                }
              </h3>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-2">
            ${isDirty ? `
              <button onclick="cancelStreamChanges(${s.id})" class="px-3 py-1.5 bg-white hover:bg-slate-100 text-slate-700 text-xs font-semibold rounded-lg border border-slate-300 transition shadow-sm">
                <i class="fa-solid fa-xmark mr-1"></i> Cancel
              </button>
              <button onclick="pushStreamToKeitaro(${s.id})" class="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow transition flex items-center gap-1.5">
                <i class="fa-solid fa-cloud-arrow-up"></i> Push to Keitaro
              </button>
            ` : `
              <span class="text-xs text-slate-400 italic">Изменений нет</span>
            `}
          </div>
        </div>

        <!-- Offers List -->
        <div class="space-y-2.5 mb-5">
          <div class="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2 flex items-center justify-between">
            <span>Офферы потока (${s.offers.filter(o => !o.is_removed).length} акт.)</span>
            <span class="font-normal text-slate-400">Суммарный вес: 100%</span>
          </div>

          ${s.offers.map(o => renderOfferRow(s.id, o)).join("")}
        </div>

        <!-- Add Offer Component -->
        <div class="border-t pt-4 ${isDirty ? "border-yellow-200" : "border-slate-100"}">
          <div class="text-xs font-bold text-slate-700 mb-2">Добавить оффер в поток:</div>
          <div class="flex gap-2 relative">
            <div class="flex-1 relative">
              <input type="text" id="stream-offer-search-${s.id}" placeholder="Поиск по офферам..." class="w-full px-3 py-2 bg-white rounded-lg border border-slate-300 text-xs focus:ring-1 focus:ring-indigo-500 outline-none" oninput="handleStreamOfferSearch(${s.id}, this.value)">
              <div id="stream-offer-dropdown-${s.id}" class="hidden absolute left-0 right-0 top-full mt-1 bg-white border border-slate-200 rounded-lg shadow-xl max-h-48 overflow-y-auto z-40 divide-y divide-slate-100 text-xs"></div>
            </div>
            <input type="hidden" id="stream-selected-offer-id-${s.id}">
            <input type="hidden" id="stream-selected-offer-name-${s.id}">
            <button onclick="submitAddOfferToStream(${s.id})" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold transition whitespace-nowrap shadow-sm">
              <i class="fa-solid fa-plus mr-1"></i> Добавить
            </button>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

// Render individual offer row
function renderOfferRow(streamId, o) {
  const isRemoved = o.is_removed;
  const isPinned = o.is_pinned;
  const rowClass = isRemoved ? "offer-removed opacity-75" : "offer-active shadow-sm";

  return `
    <div class="flex items-center justify-between p-3 rounded-lg border ${rowClass} transition text-xs">
      <div class="flex items-center gap-3 flex-1 min-w-0 mr-4">
        <span class="font-mono font-bold ${isRemoved ? "text-slate-400" : "text-indigo-600"}">[${o.keitaro_offer_id}]</span>
        <span class="truncate font-medium ${isRemoved ? "line-through text-slate-400" : "text-slate-800"}" title="${o.name || ''}">${o.name || 'Оффер без названия'}</span>
        ${o.is_new ? '<span class="bg-blue-100 text-blue-800 text-[10px] px-1.5 py-0.5 rounded font-bold">NEW</span>' : ''}
      </div>

      <div class="flex items-center gap-3">
        <!-- Share % -->
        <div class="flex items-center gap-1.5">
          <span class="font-bold text-sm ${isRemoved ? "text-slate-400" : "text-slate-900"}">${o.share}%</span>
        </div>

        <!-- Pin Button -->
        ${!isRemoved ? `
          <button onclick="togglePinOfferWeight(${streamId}, ${o.keitaro_offer_id}, ${!isPinned}, ${o.share})" title="${isPinned ? 'Открепить вес' : 'Запинить вес'}" class="p-1.5 rounded transition ${isPinned ? 'text-amber-600 bg-amber-50 font-bold' : 'text-slate-400 hover:text-slate-600'}">
            <i class="fa-solid fa-thumbtack ${isPinned ? '' : 'opacity-40'}"></i>
          </button>
        ` : ''}

        <!-- Remove or Bring Back Button -->
        ${isRemoved ? `
          <button onclick="bringBackOffer(${streamId}, ${o.keitaro_offer_id})" class="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded font-semibold text-[11px] shadow-sm transition">
            <i class="fa-solid fa-rotate-left mr-1"></i> Bring back
          </button>
        ` : `
          <button onclick="removeOfferFromStream(${streamId}, ${o.keitaro_offer_id})" class="p-1.5 text-slate-400 hover:text-rose-600 transition" title="Удалить оффер из потока">
            <i class="fa-solid fa-trash-can"></i>
          </button>
        `}
      </div>
    </div>
  `;
}

// Offer Autocomplete inside a specific stream card
const streamSearchTimeouts = {};
function handleStreamOfferSearch(streamId, query) {
  clearTimeout(streamSearchTimeouts[streamId]);
  const dropdown = document.getElementById(`stream-offer-dropdown-${streamId}`);
  if (!query.trim()) {
    dropdown.classList.add("hidden");
    return;
  }

  streamSearchTimeouts[streamId] = setTimeout(async () => {
    try {
      const res = await fetch(`/api/offers?query=${encodeURIComponent(query)}`);
      const offers = await res.json();
      if (offers.length === 0) {
        dropdown.innerHTML = '<div class="p-2 text-slate-400 text-center">Офферы не найдены</div>';
      } else {
        dropdown.innerHTML = offers.map(o => `
          <div class="p-2 hover:bg-indigo-50 cursor-pointer flex justify-between items-center" onclick="selectStreamOffer(${streamId}, ${o.id}, '${escapeQuotes(o.name)}')">
            <span class="font-bold text-slate-700">[${o.id}]</span>
            <span class="truncate ml-2 text-slate-600 flex-1">${o.name}</span>
          </div>
        `).join("");
      }
      dropdown.classList.remove("hidden");
    } catch (err) {
      console.error(err);
    }
  }, 250);
}

function selectStreamOffer(streamId, id, name) {
  document.getElementById(`stream-offer-search-${streamId}`).value = `[${id}] ${name}`;
  document.getElementById(`stream-selected-offer-id-${streamId}`).value = id;
  document.getElementById(`stream-selected-offer-name-${streamId}`).value = name;
  document.getElementById(`stream-offer-dropdown-${streamId}`).classList.add("hidden");
}

// Stream Actions
async function submitAddOfferToStream(streamId) {
  const offerId = document.getElementById(`stream-selected-offer-id-${streamId}`).value;
  const offerName = document.getElementById(`stream-selected-offer-name-${streamId}`).value;

  if (!offerId) {
    showToast("Выберите оффер для добавления", "error");
    return;
  }

  try {
    const res = await fetch(`/api/streams/${streamId}/offers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ offer_id: parseInt(offerId), name: offerName })
    });

    if (!res.ok) throw new Error("Не удалось добавить оффер");
    const updatedStream = await res.json();
    updateStreamInState(updatedStream);
    showToast("Оффер добавлен! Веса пересчитаны.");
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function removeOfferFromStream(streamId, offerId) {
  try {
    const res = await fetch(`/api/streams/${streamId}/offers/${offerId}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Ошибка при удалении оффера");
    const updatedStream = await res.json();
    updateStreamInState(updatedStream);
    showToast("Оффер удален (в архив). Веса пересчитаны.");
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function bringBackOffer(streamId, offerId) {
  try {
    const res = await fetch(`/api/streams/${streamId}/offers/${offerId}/bring_back`, { method: "POST" });
    if (!res.ok) throw new Error("Ошибка при восстановлении");
    const updatedStream = await res.json();
    updateStreamInState(updatedStream);
    showToast("Оффер восстановлен!");
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function togglePinOfferWeight(streamId, offerId, isPinned, currentShare) {
  try {
    const res = await fetch(`/api/streams/${streamId}/offers/${offerId}/pin`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_pinned: isPinned, share: currentShare })
    });
    if (!res.ok) throw new Error("Ошибка закрепления веса");
    const updatedStream = await res.json();
    updateStreamInState(updatedStream);
    showToast(isPinned ? `Вес ${currentShare}% закреплен` : "Вес откреплен");
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function cancelStreamChanges(streamId) {
  try {
    const res = await fetch(`/api/streams/${streamId}/cancel`, { method: "POST" });
    if (!res.ok) throw new Error("Ошибка отмены изменений");
    const updatedStream = await res.json();
    updateStreamInState(updatedStream);
    showToast("Несохраненные изменения отменены.");
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function pushStreamToKeitaro(streamId) {
  try {
    const res = await fetch(`/api/streams/${streamId}/push`, { method: "POST" });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Ошибка публикации в Keitaro");
    }
    const updatedStream = await res.json();
    updateStreamInState(updatedStream);
    showToast("Изменения успешно опубликованы в Keitaro!");
  } catch (err) {
    showToast(err.message, "error");
  }
}

function updateStreamInState(updatedStream) {
  const idx = currentStreams.findIndex(s => s.id === updatedStream.id);
  if (idx !== -1) {
    currentStreams[idx] = updatedStream;
  }
  renderStreams(currentStreams);
}
