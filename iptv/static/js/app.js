const sourceSelect = document.getElementById("sourceSelect");
const loadSourceBtn = document.getElementById("loadSourceBtn");
const openSourceBtn = document.getElementById("openSourceBtn");
const customUrlInput = document.getElementById("customUrlInput");
const customUserAgent = document.getElementById("customUserAgent");
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

// EPG 弹框元素
const showEpgModalBtn = document.getElementById("showEpgModalBtn");
const epgPanelMask = document.getElementById("epgPanelMask");
const epgPanel = document.getElementById("epgPanel");
const epgPanelHeader = document.getElementById("epgPanelHeader");
const epgModalTitle = document.getElementById("epgModalTitle");
const epgDateTabs = document.getElementById("epgDateTabs");
const epgModalNow = document.getElementById("epgModalNow");
const epgModalNext = document.getElementById("epgModalNext");
const epgModalList = document.getElementById("epgModalList");
const epgModalStatus = document.getElementById("epgModalStatus");
const epgPanelCloseBtn = document.getElementById("epgPanelCloseBtn");

// EPG 弹框当前数据
let epgModalProgrammes = [];
let epgModalCurrentDate = "";

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
        
        const logoUrl = item.logoUrl || item.logo || "";
        const sourceCount = item.sourceCount || 1;
        const sourceText = sourceCount > 1 ? `${sourceCount} 源` : "";
        
        row.innerHTML = `
            <div class="logo-wrap">
                ${logoUrl ? `<img class="logo" data-src="${logoUrl}" alt="" loading="lazy">` : ""}
                <span class="logo-placeholder">${(item.displayName || item.name || "?").charAt(0)}</span>
            </div>
            <div class="channel-main">
                <div class="title">${item.displayName || item.name || "未命名频道"}</div>
                <div class="meta">${item.group || "未分组"}${sourceText ? ` · ${sourceText}` : ""}</div>
            </div>
        `;
        fragment.appendChild(row);
    });

    channelList.appendChild(fragment);
    
    // 启动懒加载
    observeChannelLogos();
}

// 图片懒加载观察器
let logoObserver = null;

function observeChannelLogos() {
    // 清理旧的观察器
    if (logoObserver) {
        logoObserver.disconnect();
    }
    
    // 不支持 IntersectionObserver 时直接加载
    if (!window.IntersectionObserver) {
        channelList.querySelectorAll("img.logo[data-src]").forEach(img => {
            img.src = img.dataset.src;
            img.removeAttribute("data-src");
        });
        return;
    }
    
    logoObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                const src = img.dataset.src;
                if (src) {
                    img.src = src;
                    img.removeAttribute("data-src");
                    img.onload = () => {
                        img.classList.add("loaded");
                    };
                    img.onerror = () => {
                        img.classList.add("error");
                    };
                }
                logoObserver.unobserve(img);
            }
        });
    }, {
        root: channelList,
        rootMargin: "100px",
        threshold: 0.01
    });
    
    channelList.querySelectorAll("img.logo[data-src]").forEach(img => {
        logoObserver.observe(img);
    });
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

// 检测 URL 是否可能是 H.265 流（根据文件名特征）
function isLikelyHevc(url) {
    const lowerUrl = (url || "").toLowerCase();
    return lowerUrl.includes("h265") || lowerUrl.includes("hevc") || lowerUrl.includes("4k");
}

function playByUrl(url, rawUrl = "") {
    destroyPlayer();
    const isM3u8 = isHlsStream(rawUrl) || isHlsStream(url);
    const likelyHevc = isLikelyHevc(rawUrl) || isLikelyHevc(url);
    
    // 如果明显是 H.265，提前提示
    if (likelyHevc) {
        setStatus(playerStatus, "检测到可能是 H.265 流，若播放失败请切换 H.264 线路", "#f59e0b");
    }
    
    if (isM3u8 && window.Hls && Hls.isSupported()) {
        hls = new Hls({
            enableWorker: true,
            lowLatencyMode: true,
            capLevelToPlayerSize: true,
            // 初始使用最小缓冲，快速启动
            backBufferLength: 5,
            maxBufferLength: 5,
            maxMaxBufferLength: 15,
            liveSyncDurationCount: 2,
            liveMaxLatencyDurationCount: 4,
            // 超时设置
            manifestLoadingTimeOut: 10000,
            fragLoadingTimeOut: 15000,
            levelLoadingTimeOut: 10000,
            // 快速启动
            startFragPrefetch: true,
            testBandwidth: false,
            // 容错
            stretchShortVideoTrack: true,
            maxBufferHole: 0.5,
            maxStarvationDelay: 4,
            maxLoadingDelay: 4,
            appendErrorMaxRetry: 3,
            enableSoftwareAES: true,
        });
        
        // 监测加载性能，自动调整
        let loadStartTime = Date.now();
        let hasAdjusted = false;
        
        hls.on(Hls.Events.FRAG_LOADING, () => {
            if (!loadStartTime) loadStartTime = Date.now();
        });
        
        hls.on(Hls.Events.FRAG_LOADED, (_, data) => {
            if (hasAdjusted) return;
            const loadTime = Date.now() - loadStartTime;
            // 如果分片加载超过 2 秒，说明网络较慢或源延迟高，增加缓冲
            if (loadTime > 2000) {
                console.log("[HLS] 检测到高延迟，调整缓冲配置");
                hls.config.maxBufferLength = 30;
                hls.config.maxMaxBufferLength = 60;
                hls.config.liveSyncDurationCount = 4;
                hls.config.liveMaxLatencyDurationCount = 10;
                hasAdjusted = true;
            }
            loadStartTime = Date.now();
        });
        hls.loadSource(url);
        hls.attachMedia(player);
        hls.on(Hls.Events.ERROR, (_, data) => {
            console.warn("[HLS Error]", data.type, data.details, data);
            // fragParsingError：H.265 流浏览器不支持
            if (data.details === "fragParsingError") {
                setStatus(playerStatus, "流解析失败：H.265/HEVC 格式浏览器不支持，请切换 H.264 线路", "#fb7185");
                return;
            }
            if (data?.fatal) {
                setStatus(playerStatus, `播放失败：${data.type || "未知错误"} / ${data.details || "未知详情"}`, "#fb7185");
                if (data.type === Hls.ErrorTypes.NETWORK_ERROR) {
                    setTimeout(() => hls?.startLoad(), 1000);
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
            if (!likelyHevc) {
                setStatus(playerStatus, "播放中", "#22c55e");
            }
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
    
    // 如果已预加载 EPG，自动加载当前频道的节目表
    if (epgPreloaded && epgUrlInput.value.trim()) {
        loadEpgForCurrentChannel();
    }
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

function renderEpgRows(programmes, container = epgList) {
    container.innerHTML = "";
    if (!programmes.length) {
        container.innerHTML = '<div class="epg-empty">没有匹配到节目单，请尝试切换 EPG 源或启用代理模式</div>';
        return;
    }
    for (const item of programmes) {
        const row = document.createElement("div");
        row.className = "epg-item";
        row.innerHTML = `
            <div class="epg-time">${item.start || "--"} - ${item.stop || "--"}</div>
            <div class="epg-title">${item.title || "未知节目"}</div>
        `;
        container.appendChild(row);
    }
}

// 标记当前 EPG 源是否已预加载
let epgPreloaded = false;
let epgPreloadedUrl = "";

// 从后端获取频道 EPG（后端已有内存缓存，秒返回）
async function fetchChannelEpg(epgUrl, channelName, tvgId) {
    const params = new URLSearchParams({
        epg_url: epgUrl,
        channel_name: channelName,
        tvg_id: tvgId,
    });
    const data = await getJson(`/api/epg?${params.toString()}`);
    return data.programmes || [];
}

// 预加载整个 EPG 源到后端缓存
async function preloadEpgSource() {
    const epgUrl = epgUrlInput.value.trim();
    if (!epgUrl) {
        setStatus(epgStatus, "请先填写 EPG 链接", "#fb7185");
        return;
    }
    
    setStatus(epgStatus, "正在加载 EPG 节目单...");
    try {
        const result = await postJson("/api/epg/preload", { epg_url: epgUrl });
        epgPreloaded = true;
        epgPreloadedUrl = epgUrl;
        setStatus(epgStatus, `EPG 已缓存：${result.channel_count} 个频道，${result.programme_count} 条节目`, "#22c55e");
        
        // 如果当前已选中频道，自动加载该频道的节目
        if (currentChannel) {
            await loadEpgForCurrentChannel();
        }
    } catch (error) {
        setStatus(epgStatus, error.message || "EPG 加载失败", "#fb7185");
    }
}

// 加载当前频道的节目表（从后端缓存获取）
async function loadEpgForCurrentChannel() {
    if (!currentChannel) {
        return;
    }
    const epgUrl = epgUrlInput.value.trim();
    if (!epgUrl) {
        return;
    }
    
    const channelName = currentChannel.displayName || currentChannel.name || "";
    const tvgId = currentChannel.tvgId || "";
    
    try {
        const programmes = await fetchChannelEpg(epgUrl, channelName, tvgId);
        renderEpgRows(programmes, epgList);
        epgNow.textContent = programmes[0]?.title || "-";
        epgNext.textContent = programmes[1]?.title || "-";
    } catch (error) {
        // 静默失败，不影响播放
        console.warn("EPG 加载失败:", error);
    }
}
// EPG 弹框相关函数
function openEpgModal() {
    epgPanelMask.classList.add("show");
    epgPanel.classList.add("show");
    loadEpgForModal();
}

function closeEpgModal() {
    epgPanelMask.classList.remove("show");
    epgPanel.classList.remove("show");
    // 重置位置，下次打开时居中
    epgPanel.classList.remove("dragged");
    epgPanel.style.left = "";
    epgPanel.style.top = "";
    // 清空数据
    epgModalProgrammes = [];
    epgModalCurrentDate = "";
}

// 从节目的 start 字段提取日期（格式: MM-DD HH:MM）
function extractDateFromStart(start) {
    if (!start) return "";
    const match = start.match(/^(\d{2}-\d{2})/);
    return match ? match[1] : "";
}

// 获取日期的显示文本
function getDateLabel(dateStr) {
    if (!dateStr) return "未知";
    const today = new Date();
    const todayStr = `${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    const tomorrowStr = `${String(tomorrow.getMonth() + 1).padStart(2, "0")}-${String(tomorrow.getDate()).padStart(2, "0")}`;
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const yesterdayStr = `${String(yesterday.getMonth() + 1).padStart(2, "0")}-${String(yesterday.getDate()).padStart(2, "0")}`;
    
    if (dateStr === todayStr) return "今天";
    if (dateStr === tomorrowStr) return "明天";
    if (dateStr === yesterdayStr) return "昨天";
    return dateStr;
}

// 按日期分组节目
function groupProgrammesByDate(programmes) {
    const groups = new Map();
    for (const prog of programmes) {
        const date = extractDateFromStart(prog.start);
        if (!groups.has(date)) {
            groups.set(date, []);
        }
        groups.get(date).push(prog);
    }
    return groups;
}

// 渲染日期 Tab
function renderEpgDateTabs(dateGroups, currentDate) {
    epgDateTabs.innerHTML = "";
    epgDateTabs.classList.remove("has-tabs");
    
    const dates = Array.from(dateGroups.keys()).filter(d => d); // 过滤空日期
    if (dates.length <= 1) {
        return; // 只有一天不显示 Tab
    }
    
    epgDateTabs.classList.add("has-tabs");
    
    for (const date of dates) {
        const tab = document.createElement("button");
        tab.className = "epg-date-tab" + (date === currentDate ? " active" : "");
        tab.textContent = getDateLabel(date);
        tab.dataset.date = date;
        tab.addEventListener("click", () => {
            epgModalCurrentDate = date;
            // 更新 Tab 激活状态
            epgDateTabs.querySelectorAll(".epg-date-tab").forEach(t => {
                t.classList.toggle("active", t.dataset.date === date);
            });
            renderEpgRows(dateGroups.get(date) || [], epgModalList);
        });
        epgDateTabs.appendChild(tab);
    }
}

async function loadEpgForModal() {
    epgDateTabs.innerHTML = "";
    epgDateTabs.classList.remove("has-tabs");
    epgModalProgrammes = [];
    epgModalCurrentDate = "";
    
    if (!currentChannel) {
        epgModalTitle.textContent = "节目表";
        epgModalNow.textContent = "-";
        epgModalNext.textContent = "-";
        epgModalList.innerHTML = '<div class="epg-empty">请先选择一个频道</div>';
        setStatus(epgModalStatus, "");
        return;
    }
    
    const epgUrl = epgUrlInput.value.trim();
    const channelName = currentChannel.displayName || currentChannel.name || "";
    
    epgModalTitle.textContent = `${channelName}`;
    
    if (!epgUrl) {
        epgModalNow.textContent = "-";
        epgModalNext.textContent = "-";
        epgModalList.innerHTML = '<div class="epg-empty">请先加载 EPG 节目单</div>';
        setStatus(epgModalStatus, "");
        return;
    }
    
    const tvgId = currentChannel.tvgId || "";
    
    // 从后端获取（后端有缓存，秒返回）
    setStatus(epgModalStatus, "正在加载...");
    try {
        const programmes = await fetchChannelEpg(epgUrl, channelName, tvgId);
        epgModalProgrammes = programmes;
        epgModalNow.textContent = programmes[0]?.title || "-";
        epgModalNext.textContent = programmes[1]?.title || "-";
        
        // 按日期分组
        const dateGroups = groupProgrammesByDate(programmes);
        const dates = Array.from(dateGroups.keys());
        
        // 默认选中今天，如果没有今天则选第一个
        const today = new Date();
        const todayStr = `${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
        epgModalCurrentDate = dates.includes(todayStr) ? todayStr : (dates[0] || "");
        
        // 渲染 Tab 和列表
        renderEpgDateTabs(dateGroups, epgModalCurrentDate);
        renderEpgRows(dateGroups.get(epgModalCurrentDate) || programmes, epgModalList);
        
        setStatus(epgModalStatus, programmes.length ? `共 ${programmes.length} 条节目` : "未匹配到节目", programmes.length ? "#22c55e" : "#f59e0b");
    } catch (error) {
        epgModalList.innerHTML = `<div class="epg-empty">加载失败：${error.message || "未知错误"}</div>`;
        setStatus(epgModalStatus, "加载失败", "#fb7185");
    }
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
        const ua = customUserAgent.value.trim() || "";
        await loadChannels(url, "手动输入", ua);
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
    await preloadEpgSource();
});

clearEpgBtn.addEventListener("click", () => {
    clearEpgPanel(true);
    epgPreloaded = false;
    epgPreloadedUrl = "";
    setStatus(epgStatus, "已清空 EPG 缓存", "#38bdf8");
});

// EPG 弹框事件
showEpgModalBtn.addEventListener("click", openEpgModal);
epgPanelCloseBtn.addEventListener("click", closeEpgModal);
epgPanelMask.addEventListener("click", closeEpgModal);

// EPG 面板拖动功能
(function initEpgPanelDrag() {
    let isDragging = false;
    let startX = 0;
    let startY = 0;
    let startLeft = 0;
    let startTop = 0;

    epgPanelHeader.addEventListener("mousedown", e => {
        if (e.target.closest("button")) return;
        isDragging = true;
        startX = e.clientX;
        startY = e.clientY;
        const rect = epgPanel.getBoundingClientRect();
        startLeft = rect.left;
        startTop = rect.top;
        // 首次拖动时，移除居中的 transform，改为绝对定位
        if (!epgPanel.classList.contains("dragged")) {
            epgPanel.classList.add("dragged");
            epgPanel.style.left = startLeft + "px";
            epgPanel.style.top = startTop + "px";
        }
        epgPanelHeader.style.cursor = "grabbing";
        e.preventDefault();
    });

    document.addEventListener("mousemove", e => {
        if (!isDragging) return;
        const dx = e.clientX - startX;
        const dy = e.clientY - startY;
        let newLeft = startLeft + dx;
        let newTop = startTop + dy;
        
        // 边界限制
        const panelWidth = epgPanel.offsetWidth;
        const panelHeight = epgPanel.offsetHeight;
        const maxLeft = window.innerWidth - panelWidth;
        const maxTop = window.innerHeight - panelHeight;
        
        newLeft = Math.max(0, Math.min(newLeft, maxLeft));
        newTop = Math.max(0, Math.min(newTop, maxTop));
        
        epgPanel.style.left = newLeft + "px";
        epgPanel.style.top = newTop + "px";
    });

    document.addEventListener("mouseup", () => {
        if (isDragging) {
            isDragging = false;
            epgPanelHeader.style.cursor = "move";
        }
    });
})();

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
        closeEpgModal();
    }
});

initPlyr();
setupOpenSourceAndEpgBind();
clearChannelSourceSelect();
Promise.all([syncProxySettings(), loadSources()]).catch(error => {
    setStatus(sourceStatus, error.message || "初始化失败", "#fb7185");
});
