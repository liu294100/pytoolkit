const sourceSelect = document.getElementById("sourceSelect");
const loadSourceBtn = document.getElementById("loadSourceBtn");
const openSourceBtn = document.getElementById("openSourceBtn");
const customUrlInput = document.getElementById("customUrlInput");
const loadCustomBtn = document.getElementById("loadCustomBtn");
const loadTextBtn = document.getElementById("loadTextBtn");
const m3uText = document.getElementById("m3uText");
const keywordInput = document.getElementById("keywordInput");
const groupFilter = document.getElementById("groupFilter");
const channelList = document.getElementById("channelList");
const channelCount = document.getElementById("channelCount");
const sourceStatus = document.getElementById("sourceStatus");
const player = document.getElementById("player");
const videoWrap = document.querySelector(".video-wrap");
const playerStatus = document.getElementById("playerStatus");
const channelSourceSelect = document.getElementById("channelSourceSelect");
const proxySettingsBtn = document.getElementById("proxySettingsBtn");
const proxyIndicator = document.getElementById("proxyIndicator");
const proxyModal = document.getElementById("proxyModal");
const proxyEnabled = document.getElementById("proxyEnabled");
const proxyHost = document.getElementById("proxyHost");
const proxyPort = document.getElementById("proxyPort");
const proxySaveBtn = document.getElementById("proxySaveBtn");
const proxyCancelBtn = document.getElementById("proxyCancelBtn");
const proxyStatus = document.getElementById("proxyStatus");
const nowPlaying = document.getElementById("nowPlaying");
const streamUrl = document.getElementById("streamUrl");

const playPauseBtn = document.getElementById("playPauseBtn");
const retryBtn = document.getElementById("retryBtn");
const muteBtn = document.getElementById("muteBtn");
const fullBtn = document.getElementById("fullBtn");
const copyBtn = document.getElementById("copyBtn");
const epgPreset = document.getElementById("epgPreset");
const epgUrlInput = document.getElementById("epgUrlInput");
const loadEpgBtn = document.getElementById("loadEpgBtn");
const clearEpgBtn = document.getElementById("clearEpgBtn");
const epgChannel = document.getElementById("epgChannel");
const epgNow = document.getElementById("epgNow");
const epgNext = document.getElementById("epgNext");
const epgList = document.getElementById("epgList");
const epgStatus = document.getElementById("epgStatus");

let hls = null;
let playerUi = null;
let sources = [];
let epgSources = [];
let channels = [];
let filtered = [];
let currentIndex = -1;
let currentChannel = null;
let currentSourceIndex = 0;
let filterTimer = null;
const PROXY_STORAGE_KEY = "iptv_proxy_settings_v1";

function setStatus(el, text, color = "#fcd34d") {
    el.textContent = text || "";
    el.style.color = color;
}

function normalize(text) {
    return (text || "").toString().trim().toLowerCase();
}

function normalizeChannelName(name) {
    return (name || "").toString().replace(/\s+/g, " ").trim();
}

function toDisplayName(name) {
    const cleaned = normalizeChannelName(name);
    if (!cleaned) {
        return "";
    }
    const parts = cleaned.split(/[|｜/]/).map(v => v.trim()).filter(Boolean);
    const first = parts[0] || cleaned;
    const commaParts = first.split(/[,，]/).map(v => v.trim()).filter(Boolean);
    return commaParts[0] || first;
}

function getChannelKey(item) {
    const tvgId = normalize(item.tvgId || "");
    if (tvgId) {
        return `tvg:${tvgId}`;
    }
    return `name:${normalize(item.displayName || item.name || item.title || "")}`;
}

function isHlsStream(url) {
    const value = (url || "").toString().trim();
    if (!value) {
        return false;
    }
    try {
        const decoded = decodeURIComponent(value);
        return /\.m3u8(\?|$)/i.test(decoded) || /[?&]url=https?:\/\/[^&]+\.m3u8(?:[?&]|$)/i.test(decoded);
    } catch (_) {
        return /\.m3u8(\?|$)/i.test(value) || /[?&]url=https?:\/\/[^&]+\.m3u8(?:[?&]|$)/i.test(value);
    }
}

function aggregateChannels(items) {
    const map = new Map();
    for (const item of items) {
        const displayName = item.displayName || item.name || item.title || "未命名频道";
        const key = getChannelKey({ ...item, displayName });
        const currentSource = {
            name: item.sourceName || "默认源",
            url: item.url || "",
            playUrl: item.playUrl || item.url || "",
            group: item.group || "未分组",
            logo: item.logo || "",
            logoUrl: item.logoUrl || "",
            tvgId: item.tvgId || "",
        };
        if (!map.has(key)) {
            map.set(key, {
                ...item,
                displayName,
                group: item.group || "未分组",
                logo: item.logo || "",
                logoUrl: item.logoUrl || "",
                url: item.url || "",
                playUrl: item.playUrl || item.url || "",
                sources: [currentSource],
            });
            continue;
        }
        const channel = map.get(key);
        const exists = channel.sources.some(source => source.playUrl === currentSource.playUrl || source.url === currentSource.url);
        if (!exists) {
            channel.sources.push(currentSource);
        }
        if (!channel.logoUrl && currentSource.logoUrl) {
            channel.logoUrl = currentSource.logoUrl;
        }
        if (!channel.logo && currentSource.logo) {
            channel.logo = currentSource.logo;
        }
        if (!channel.tvgId && currentSource.tvgId) {
            channel.tvgId = currentSource.tvgId;
        }
    }
    return Array.from(map.values()).map(channel => ({
        ...channel,
        sourceCount: channel.sources.length,
    }));
}

async function getJson(url) {
    const res = await fetch(url, { cache: "no-store" });
    const data = await res.json();
    if (!res.ok) {
        throw new Error(data.error || `请求失败：${res.status}`);
    }
    return data;
}

async function postJson(url, payload) {
    const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
        throw new Error(data.error || `请求失败：${res.status}`);
    }
    return data;
}

function getSavedProxySettings() {
    try {
        const raw = localStorage.getItem(PROXY_STORAGE_KEY);
        return raw ? JSON.parse(raw) : null;
    } catch (_) {
        return null;
    }
}

function saveProxySettingsToStorage(settings) {
    localStorage.setItem(PROXY_STORAGE_KEY, JSON.stringify(settings));
}

function fillProxyForm(settings) {
    proxyEnabled.checked = Boolean(settings?.enabled);
    proxyHost.value = settings?.host || "127.0.0.1";
    proxyPort.value = String(settings?.port || 7890);
}

function updateProxyIndicator(settings) {
    if (settings?.enabled) {
        proxyIndicator.textContent = `代理已启用 ${settings.host}:${settings.port}`;
        proxyIndicator.style.color = "#86efac";
    } else {
        proxyIndicator.textContent = "代理未启用";
        proxyIndicator.style.color = "#bfdbfe";
    }
}

function openProxyModal() {
    proxyModal.classList.add("show");
    setStatus(proxyStatus, "");
}

function closeProxyModal() {
    proxyModal.classList.remove("show");
}

async function syncProxySettings() {
    const local = getSavedProxySettings();
    if (local) {
        const synced = await postJson("/api/proxy-settings", local);
        fillProxyForm(synced);
        updateProxyIndicator(synced);
        return synced;
    }
    const settings = await getJson("/api/proxy-settings");
    fillProxyForm(settings);
    updateProxyIndicator(settings);
    return settings;
}

async function loadSources() {
    setStatus(sourceStatus, "正在读取源配置...");
    const data = await getJson("/api/sources");
    sources = data.sources || [];
    epgSources = data.epgSources || [];

    sourceSelect.innerHTML = "";
    for (const source of sources) {
        const option = document.createElement("option");
        option.value = source.url;
        option.textContent = `${source.name} (${source.type || "m3u"})`;
        option.dataset.name = source.name || "未命名源";
        option.dataset.type = source.type || "m3u";
        option.dataset.epg = source.epg || "";
        option.dataset.userAgent = source.userAgent || "";
        sourceSelect.appendChild(option);
    }
    fillEpgPresets(epgSources);
    setStatus(sourceStatus, `已加载 ${sources.length} 个源`, "#22c55e");
}

function fillEpgPresets(presets) {
    epgPreset.innerHTML = "";
    const defaultOption = document.createElement("option");
    defaultOption.value = "";
    defaultOption.textContent = "选择 EPG 预设";
    epgPreset.appendChild(defaultOption);

    for (const item of presets) {
        const option = document.createElement("option");
        option.value = item.url || "";
        option.textContent = item.name || item.url || "EPG";
        epgPreset.appendChild(option);
    }
}

function updateGroupFilter() {
    const groups = Array.from(new Set(channels.map(item => item.group || "未分组")));
    groups.sort((a, b) => a.localeCompare(b, "zh-CN"));

    groupFilter.innerHTML = "";
    const all = document.createElement("option");
    all.value = "";
    all.textContent = "全部分组";
    groupFilter.appendChild(all);

    for (const group of groups) {
        const option = document.createElement("option");
        option.value = group;
        option.textContent = group;
        groupFilter.appendChild(option);
    }
}

function applyFilters() {
    const keyword = normalize(keywordInput.value);
    const group = groupFilter.value;

    filtered = channels.filter(item => {
        const inKeyword = !keyword || normalize(item.displayName || item.name).includes(keyword);
        const inGroup = !group || (item.group || "未分组") === group;
        return inKeyword && inGroup;
    });
    currentIndex = -1;
    currentChannel = null;
    clearChannelSourceSelect();
    renderChannels();
}

function renderChannels() {
    channelList.innerHTML = "";
    channelCount.textContent = String(filtered.length);
    const fragment = document.createDocumentFragment();

    filtered.forEach((item, index) => {
        const row = document.createElement("div");
        row.className = "channel-item";
        row.dataset.index = String(index);
        if (index === currentIndex) {
            row.classList.add("active");
        }
        row.innerHTML = `
            <img class="logo" src="${item.logoUrl || item.logo || ""}" alt="" onerror="this.style.display='none'">
            <div class="channel-main">
                <div class="title">${item.displayName || item.name || "未命名频道"}</div>
                <div class="meta">${item.group || "未分组"}</div>
            </div>
            <div class="channel-side">${item.sourceCount || 1} 个源</div>
        `;
        fragment.appendChild(row);
    });

    channelList.appendChild(fragment);
}

function clearChannelSourceSelect() {
    channelSourceSelect.innerHTML = "";
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "请先选择频道";
    channelSourceSelect.appendChild(option);
    channelSourceSelect.disabled = true;
}

function updateActiveItem(prevIndex, nextIndex) {
    if (prevIndex >= 0) {
        const prev = channelList.querySelector(`.channel-item[data-index="${prevIndex}"]`);
        if (prev) {
            prev.classList.remove("active");
        }
    }
    if (nextIndex >= 0) {
        const next = channelList.querySelector(`.channel-item[data-index="${nextIndex}"]`);
        if (next) {
            next.classList.add("active");
            next.scrollIntoView({ block: "nearest" });
        }
    }
}

function destroyPlayer() {
    if (hls) {
        hls.destroy();
        hls = null;
    }
    videoWrap.classList.remove("has-source");
}

function setVideoLoaded() {
    videoWrap.classList.add("has-source");
}

function playByUrl(url, rawUrl = "") {
    destroyPlayer();
    const isM3u8 = isHlsStream(rawUrl) || isHlsStream(url);
    if (isM3u8 && window.Hls && Hls.isSupported()) {
        hls = new Hls({
            enableWorker: true,
            lowLatencyMode: false,
            capLevelToPlayerSize: true,
            backBufferLength: 18,
            maxBufferLength: 20,
            maxMaxBufferLength: 32,
            liveSyncDurationCount: 3,
            liveMaxLatencyDurationCount: 8,
            manifestLoadingTimeOut: 12000,
            fragLoadingTimeOut: 18000,
            levelLoadingTimeOut: 12000,
            startFragPrefetch: true,
        });
        hls.loadSource(url);
        hls.attachMedia(player);
        hls.on(Hls.Events.ERROR, (_, data) => {
            if (data?.fatal) {
                setStatus(playerStatus, `播放失败：${data.type || "未知错误"} / ${data.details || "未知详情"}`, "#fb7185");
                if (data.type === Hls.ErrorTypes.NETWORK_ERROR) {
                    hls.startLoad();
                    return;
                }
                if (data.type === Hls.ErrorTypes.MEDIA_ERROR) {
                    hls.recoverMediaError();
                    return;
                }
            }
        });
        hls.on(Hls.Events.MANIFEST_PARSED, () => {
            setVideoLoaded();
            player.play().catch(() => {});
        });
        return;
    }

    player.src = url;
    setVideoLoaded();
    player.play().catch(() => {});
}

function playChannel(index) {
    const channel = filtered[index];
    if (!channel) {
        return;
    }
    const previousIndex = currentIndex;
    currentIndex = index;
    currentChannel = channel;
    currentSourceIndex = 0;
    updateActiveItem(previousIndex, currentIndex);
    clearEpgPanel(false);
    renderChannelSources(channel);
    applyCurrentSource(channel, currentSourceIndex);
    setStatus(playerStatus, "播放中", "#22c55e");
}

function renderChannelSources(channel) {
    channelSourceSelect.innerHTML = "";
    const sourceItems = channel?.sources?.length ? channel.sources : [{
        name: channel?.sourceName || "默认源",
        url: channel?.url || "",
        playUrl: channel?.playUrl || channel?.url || "",
        group: channel?.group || "未分组",
        logo: channel?.logo || "",
        logoUrl: channel?.logoUrl || "",
        tvgId: channel?.tvgId || "",
    }];
    sourceItems.forEach((source, index) => {
        const option = document.createElement("option");
        option.value = String(index);
        option.textContent = `${source.name || "默认源"} · ${source.group || "未分组"}`;
        channelSourceSelect.appendChild(option);
    });
    channelSourceSelect.disabled = sourceItems.length <= 1;
}

function applyCurrentSource(channel, sourceIndex) {
    const sourceItems = channel?.sources?.length ? channel.sources : [channel];
    const source = sourceItems[sourceIndex] || sourceItems[0];
    currentSourceIndex = sourceItems.indexOf(source);
    channelSourceSelect.value = String(currentSourceIndex);
    epgChannel.textContent = channel.displayName || channel.name || "-";
    playByUrl(source.playUrl || source.url, source.url || source.playUrl || "");
    streamUrl.textContent = `流地址：${source.url || "-"}`;
    nowPlaying.textContent = `正在播放：${channel.displayName || channel.name || "未命名频道"} · ${source.name || "默认源"}`;
}

async function loadChannels(sourceUrl, sourceName, userAgent) {
    const encodedUrl = encodeURIComponent(sourceUrl);
    const encodedName = encodeURIComponent(sourceName || "自定义源");
    const encodedUA = userAgent ? `&user_agent=${encodeURIComponent(userAgent)}` : "";
    setStatus(sourceStatus, "正在拉取频道列表...");
    const data = await getJson(`/api/channels?source_url=${encodedUrl}&source_name=${encodedName}${encodedUA}`);
    channels = aggregateChannels((data.channels || []).map(item => ({
        ...item,
        displayName: toDisplayName(item.name || item.title || ""),
    })));
    filtered = [...channels];
    currentIndex = -1;
    currentChannel = null;
    currentSourceIndex = 0;
    updateGroupFilter();
    applyFilters();
    clearEpgPanel(true);
    setStatus(sourceStatus, `频道加载完成：去重后 ${channels.length} 个频道`, "#22c55e");
}

async function loadChannelsByText(rawText) {
    setStatus(sourceStatus, "正在解析 M3U 文本...");
    const data = await postJson("/api/channels-text", {
        m3u_text: rawText,
        source_name: "文本导入",
    });
    channels = aggregateChannels((data.channels || []).map(item => ({
        ...item,
        displayName: toDisplayName(item.name || item.title || ""),
    })));
    filtered = [...channels];
    currentIndex = -1;
    currentChannel = null;
    currentSourceIndex = 0;
    updateGroupFilter();
    applyFilters();
    clearEpgPanel(true);
    setStatus(sourceStatus, `文本导入完成：去重后 ${channels.length} 个频道`, "#22c55e");
}

function clearEpgPanel(resetChannel) {
    epgList.innerHTML = "";
    epgNow.textContent = "-";
    epgNext.textContent = "-";
    if (resetChannel) {
        epgChannel.textContent = "-";
    }
}

function renderEpgRows(programmes) {
    epgList.innerHTML = "";
    if (!programmes.length) {
        epgList.innerHTML = '<div class="epg-empty">没有匹配到节目单，请尝试切换 EPG 源或启用代理模式</div>';
        return;
    }
    for (const item of programmes) {
        const row = document.createElement("div");
        row.className = "epg-item";
        row.innerHTML = `
            <div class="epg-time">${item.start || "--"} - ${item.stop || "--"}</div>
            <div class="epg-title">${item.title || "未知节目"}</div>
        `;
        epgList.appendChild(row);
    }
}

async function loadEpgForCurrentChannel() {
    if (!currentChannel) {
        setStatus(epgStatus, "请先选择一个频道", "#fb7185");
        return;
    }
    const epgUrl = epgUrlInput.value.trim();
    if (!epgUrl) {
        setStatus(epgStatus, "请先填写 EPG 链接", "#fb7185");
        return;
    }
    const params = new URLSearchParams({
        epg_url: epgUrl,
        channel_name: currentChannel.name || "",
        tvg_id: currentChannel.tvgId || "",
    });
    setStatus(epgStatus, "正在加载节目表...");
    const data = await getJson(`/api/epg?${params.toString()}`);
    const programmes = data.programmes || [];
    renderEpgRows(programmes);
    epgNow.textContent = programmes[0]?.title || "-";
    epgNext.textContent = programmes[1]?.title || "-";
    setStatus(epgStatus, programmes.length ? `节目条数：${programmes.length}` : "未匹配到节目单", programmes.length ? "#22c55e" : "#f59e0b");
}

function setupOpenSourceAndEpgBind() {
    sourceSelect.addEventListener("change", () => {
        const option = sourceSelect.selectedOptions[0];
        if (!option) {
            return;
        }
        const sourceEpg = option.dataset.epg || "";
        if (sourceEpg && !epgUrlInput.value.trim()) {
            epgUrlInput.value = sourceEpg;
        }
    });

    epgPreset.addEventListener("change", () => {
        epgUrlInput.value = epgPreset.value || "";
    });
}

function initPlyr() {
    player.preload = "metadata";
    if (window.Plyr) {
        playerUi = new Plyr(player, {
            controls: ["play-large", "play", "progress", "current-time", "mute", "volume", "settings", "fullscreen"],
        });
    }
}

loadSourceBtn.addEventListener("click", async () => {
    try {
        const option = sourceSelect.selectedOptions[0];
        if (!option) {
            return;
        }
        const sourceType = option.dataset.type || "m3u";
        if (sourceType !== "m3u") {
            window.open(option.value, "_blank");
            setStatus(sourceStatus, "该源是网页导航，已为你打开原始页面", "#38bdf8");
            return;
        }
        if (option.dataset.epg && !epgUrlInput.value.trim()) {
            epgUrlInput.value = option.dataset.epg;
        }
        await loadChannels(option.value, option.dataset.name || "默认源", option.dataset.userAgent || "");
    } catch (error) {
        setStatus(sourceStatus, error.message || "加载失败", "#fb7185");
    }
});

openSourceBtn.addEventListener("click", () => {
    const option = sourceSelect.selectedOptions[0];
    if (!option) {
        return;
    }
    window.open(option.value, "_blank");
});

loadCustomBtn.addEventListener("click", async () => {
    const url = customUrlInput.value.trim();
    if (!url) {
        setStatus(sourceStatus, "请输入 M3U 链接", "#fb7185");
        return;
    }
    try {
        await loadChannels(url, "手动输入");
    } catch (error) {
        setStatus(sourceStatus, error.message || "加载失败", "#fb7185");
    }
});

loadTextBtn.addEventListener("click", async () => {
    const raw = m3uText.value.trim();
    if (!raw) {
        setStatus(sourceStatus, "请先粘贴 M3U 文本", "#fb7185");
        return;
    }
    try {
        await loadChannelsByText(raw);
    } catch (error) {
        setStatus(sourceStatus, error.message || "导入失败", "#fb7185");
    }
});

keywordInput.addEventListener("input", () => {
    clearTimeout(filterTimer);
    filterTimer = setTimeout(() => {
        applyFilters();
    }, 160);
});
groupFilter.addEventListener("change", applyFilters);

channelList.addEventListener("click", event => {
    const row = event.target.closest(".channel-item");
    if (!row) {
        return;
    }
    const index = Number(row.dataset.index);
    if (!Number.isNaN(index)) {
        playChannel(index);
    }
});

channelSourceSelect.addEventListener("change", () => {
    if (!currentChannel) {
        return;
    }
    const nextIndex = Number(channelSourceSelect.value);
    if (Number.isNaN(nextIndex)) {
        return;
    }
    applyCurrentSource(currentChannel, nextIndex);
    setStatus(playerStatus, "已切换信号源", "#38bdf8");
});

proxySettingsBtn.addEventListener("click", openProxyModal);
proxyCancelBtn.addEventListener("click", closeProxyModal);
proxyModal.addEventListener("click", event => {
    if (event.target === proxyModal) {
        closeProxyModal();
    }
});

proxySaveBtn.addEventListener("click", async () => {
    const payload = {
        enabled: proxyEnabled.checked,
        host: proxyHost.value.trim() || "127.0.0.1",
        port: proxyPort.value.trim() || "7890",
    };
    try {
        const settings = await postJson("/api/proxy-settings", payload);
        saveProxySettingsToStorage(settings);
        fillProxyForm(settings);
        updateProxyIndicator(settings);
        setStatus(proxyStatus, "代理设置已保存", "#22c55e");
        setTimeout(() => {
            closeProxyModal();
        }, 260);
    } catch (error) {
        setStatus(proxyStatus, error.message || "保存失败", "#fb7185");
    }
});

playPauseBtn.addEventListener("click", () => {
    if (player.paused) {
        player.play().catch(() => {});
    } else {
        player.pause();
    }
});

retryBtn.addEventListener("click", () => {
    if (currentIndex >= 0) {
        playChannel(currentIndex);
    }
});

muteBtn.addEventListener("click", () => {
    player.muted = !player.muted;
    muteBtn.textContent = player.muted ? "取消静音" : "静音";
});

fullBtn.addEventListener("click", async () => {
    if (document.fullscreenElement) {
        await document.exitFullscreen();
    } else {
        await player.requestFullscreen();
    }
});

copyBtn.addEventListener("click", async () => {
    const value = streamUrl.textContent.replace("流地址：", "").trim();
    if (!value) {
        setStatus(playerStatus, "当前没有可复制的流地址", "#fb7185");
        return;
    }
    try {
        await navigator.clipboard.writeText(value);
        setStatus(playerStatus, "流地址已复制", "#22c55e");
    } catch (_) {
        setStatus(playerStatus, "复制失败，请手动复制", "#fb7185");
    }
});

loadEpgBtn.addEventListener("click", async () => {
    try {
        await loadEpgForCurrentChannel();
    } catch (error) {
        setStatus(epgStatus, error.message || "EPG 加载失败", "#fb7185");
    }
});

clearEpgBtn.addEventListener("click", () => {
    clearEpgPanel(true);
    setStatus(epgStatus, "已清空节目表", "#38bdf8");
});

player.addEventListener("error", () => {
    const mediaError = player.error;
    const detailMap = {
        1: "播放被中止",
        2: "网络拉流失败",
        3: "媒体解码失败",
        4: "当前格式不受支持",
    };
    const detail = mediaError ? detailMap[mediaError.code] || "未知错误" : "未知错误";
    setStatus(playerStatus, `播放器发生错误：${detail}，建议切换线路或重连`, "#fb7185");
});

player.addEventListener("loadedmetadata", () => {
    setVideoLoaded();
});

window.addEventListener("keydown", event => {
    if (event.key === "Escape") {
        closeProxyModal();
    }
});

initPlyr();
setupOpenSourceAndEpgBind();
clearChannelSourceSelect();
Promise.all([syncProxySettings(), loadSources()]).catch(error => {
    setStatus(sourceStatus, error.message || "初始化失败", "#fb7185");
});
