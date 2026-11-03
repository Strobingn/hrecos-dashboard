/* Fish Sounds — Hudson River hydrophone network.
   Live path: Supabase Realtime on public.detections (see config.js).
   Offline path: data/fish-sounds.json, with clips synthesized in the browser. */

var fsState = {
  ready: false,
  loading: false,
  source: "mock",
  notice: "",
  species: [],
  nodes: [],
  detections: [],
  hourly: [],
  selectedNodeId: "westpoint-cornwall",
  speciesFilter: "",
  selectedId: null,
  scrollDetail: false,
  clipCache: {},
  fsMap: null,
  channel: null,
  client: null,
  drawToken: 0,
  playing: null
};

function fsEsc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
  });
}

function fsConfig() {
  return window.HRECOS_CONFIG || {};
}

function fsCanLive() {
  var c = fsConfig();
  var url = String(c.supabaseUrl || "").trim();
  var key = String(c.supabaseAnonKey || "").trim();
  if (!url || !key) return false;
  if (/YOUR_|PASTE_|example\.supabase|changeme/i.test(url + " " + key)) return false;
  return !!(window.supabase && typeof window.supabase.createClient === "function");
}

function fsById(list, id) {
  for (var i = 0; i < list.length; i++) if (list[i].id === id) return list[i];
  return null;
}

function fsSpecies(id) { return fsById(fsState.species, id); }
function fsNode(id) { return fsById(fsState.nodes, id); }

function fsFloorHour(d) {
  var x = new Date(d);
  x.setMinutes(0, 0, 0);
  x.setMilliseconds(0);
  return x.getTime();
}

function fsRelTime(iso) {
  var ms = Date.now() - new Date(iso).getTime();
  if (!isFinite(ms)) return "";
  var m = Math.round(ms / 60000);
  if (m < 1) return "just now";
  if (m < 60) return m + " min ago";
  var h = Math.round(m / 60);
  if (h < 48) return h + " h ago";
  return new Date(iso).toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

function fsNormalizeMock(doc) {
  var now = Date.now();
  var species = doc.species || [];
  var nodes = (doc.hydrophone_nodes || doc.nodes || []).map(function (n) {
    var copy = Object.assign({}, n);
    if (copy.last_heartbeat_minutes_ago != null && !copy.last_heartbeat) {
      copy.last_heartbeat = new Date(now - copy.last_heartbeat_minutes_ago * 60000).toISOString();
    }
    return copy;
  });
  var detections = (doc.detections || []).map(function (d) {
    var copy = Object.assign({}, d);
    if (copy.minutes_ago != null && !copy.start_time) {
      var start = now - copy.minutes_ago * 60000;
      var dur = (copy.duration_s || 1.5) * 1000;
      copy.start_time = new Date(start).toISOString();
      copy.end_time = new Date(start + dur).toISOString();
    }
    return copy;
  });
  var base = new Date();
  base.setMinutes(0, 0, 0);
  base.setMilliseconds(0);
  var currentHour = base.getHours();
  var hourly = (doc.detection_counts_hourly || doc.hourly || []).map(function (r) {
    var copy = Object.assign({}, r);
    if (!copy.hour && copy.hour_of_day != null) {
      var delta = currentHour - copy.hour_of_day;
      if (delta < 0) delta += 24;
      copy.hour = new Date(base.getTime() - delta * 3600000).toISOString();
    }
    return copy;
  });
  return { species: species, nodes: nodes, detections: detections, hourly: hourly };
}

function fsSortDetections() {
  fsState.detections.sort(function (a, b) {
    return new Date(b.start_time) - new Date(a.start_time);
  });
}

async function fsLoadMock() {
  var url = new URL("data/fish-sounds.json", document.baseURI).href;
  var res = await fetch(url);
  if (!res.ok) throw new Error("sample file HTTP " + res.status);
  var doc = await res.json();
  var data = fsNormalizeMock(doc);
  fsState.species = data.species;
  fsState.nodes = data.nodes;
  fsState.detections = data.detections;
  fsState.hourly = data.hourly;
  fsState.source = "mock";
  fsSortDetections();
}

async function fsLoadLive() {
  var c = fsConfig();
  var sb = window.supabase.createClient(String(c.supabaseUrl).trim(), String(c.supabaseAnonKey).trim());
  var since = new Date(Date.now() - 36 * 3600000).toISOString();
  var species = await sb.from("species").select("*").order("common_name");
  var nodes = await sb.from("hydrophone_nodes").select("*").order("river_mile");
  var detections = await sb.from("detections").select("*").order("start_time", { ascending: false }).limit(80);
  var hourly = await sb.from("detection_counts_hourly").select("*").gte("hour", since);
  [species, nodes, detections, hourly].forEach(function (r) {
    if (r.error) throw new Error(r.error.message || "Supabase query failed");
  });
  fsState.client = sb;
  fsState.species = species.data || [];
  fsState.nodes = nodes.data || [];
  fsState.detections = detections.data || [];
  fsState.hourly = hourly.data || [];
  fsState.source = "live";
  fsSortDetections();
  fsSubscribe(sb);
}

function fsSubscribe(sb) {
  if (fsState.channel) return;
  fsState.channel = sb.channel("fish-detections")
    .on("postgres_changes", { event: "*", schema: "public", table: "detections" }, function (payload) {
      var row = payload.new || payload.old;
      if (!row) return;
      if (payload.eventType === "DELETE") {
        fsState.detections = fsState.detections.filter(function (d) { return d.id !== row.id; });
      } else {
        var idx = -1;
        for (var i = 0; i < fsState.detections.length; i++) if (fsState.detections[i].id === row.id) idx = i;
        if (idx >= 0) fsState.detections[idx] = Object.assign({}, fsState.detections[idx], row);
        else fsState.detections.unshift(row);
        delete fsState.clipCache[row.id];
      }
      fsSortDetections();
      if (typeof cur !== "undefined" && cur === "sounds" && typeof render === "function") render();
    })
    .subscribe();
}

async function ensureFishData() {
  if (fsState.ready || fsState.loading) return;
  fsState.loading = true;
  try {
    if (fsCanLive()) {
      try {
        await fsLoadLive();
        fsState.notice = "";
      } catch (err) {
        await fsLoadMock();
        fsState.notice = "Live feed unavailable (" + err.message + "). Showing bundled sample detections.";
      }
    } else {
      await fsLoadMock();
      fsState.notice = "Sample data. Set supabaseUrl and supabaseAnonKey in config.js for the live hydrophone feed.";
    }
  } catch (err) {
    fsState.notice = "Could not load fish sounds (" + err.message + ").";
    fsState.species = fsState.species || [];
    fsState.nodes = fsState.nodes || [];
    fsState.detections = fsState.detections || [];
    fsState.hourly = fsState.hourly || [];
  } finally {
    fsState.loading = false;
    fsState.ready = true;
    if (!fsNode(fsState.selectedNodeId) && fsState.nodes[0]) fsState.selectedNodeId = fsState.nodes[0].id;
    if (!fsState.selectedId && fsState.detections[0]) fsState.selectedId = fsState.detections[0].id;
    if (typeof cur !== "undefined" && cur === "sounds" && typeof render === "function") render();
  }
}

function fsClipUrl(det) {
  if (!det || !det.clip_path) return null;
  if (/^https?:/i.test(det.clip_path)) return det.clip_path;
  if (fsState.source !== "live") return null;
  var base = String(fsConfig().supabaseUrl || "").replace(/\/$/, "");
  if (!base) return null;
  return base + "/storage/v1/object/public/audio/" + String(det.clip_path).replace(/^\//, "");
}

function fsSynthSamples(det) {
  var species = fsSpecies(det.species_id) || {};
  var sampleRate = 8000;
  var dur = 1.6;
  if (det.start_time && det.end_time) {
    dur = (new Date(det.end_time) - new Date(det.start_time)) / 1000;
  } else if (det.duration_s) dur = det.duration_s;
  dur = Math.max(0.8, Math.min(4, dur || 1.6));
  var n = Math.floor(sampleRate * dur);
  var out = new Float32Array(n);
  var fLo = det.freq_low_hz || species.freq_low_hz || 180;
  var fHi = det.freq_high_hz || species.freq_high_hz || 700;
  var f0 = (Number(fLo) + Number(fHi)) / 2;
  var label = String(det.label || "").toLowerCase();
  for (var i = 0; i < n; i++) out[i] += (Math.random() * 2 - 1) * 0.015;
  function tone(i0, len, freq, amp, fade) {
    for (var i = 0; i < len; i++) {
      var idx = i0 + i;
      if (idx < 0 || idx >= n) continue;
      var e = 1;
      var f = fade || Math.floor(len * 0.08);
      if (i < f) e = i / f;
      else if (i > len - f) e = Math.max(0, (len - i) / f);
      var t = idx / sampleRate;
      out[idx] += Math.sin(2 * Math.PI * freq * t) * amp * e;
    }
  }
  if (label.indexOf("boat") >= 0 || label.indexOf("whistle") >= 0) {
    tone(Math.floor(0.12 * sampleRate), Math.floor(dur * 0.78 * sampleRate), f0, 0.45, Math.floor(0.05 * sampleRate));
    tone(Math.floor(0.12 * sampleRate), Math.floor(dur * 0.78 * sampleRate), f0 * 2, 0.12, Math.floor(0.05 * sampleRate));
  } else if (label.indexOf("growl") >= 0) {
    var gLen = Math.floor(dur * 0.7 * sampleRate);
    var g0 = Math.floor(0.1 * sampleRate);
    for (var g = 0; g < gLen; g++) {
      var env = Math.sin(Math.PI * g / gLen);
      var trem = 0.6 + 0.4 * Math.sin(2 * Math.PI * 18 * (g / sampleRate));
      out[g0 + g] += (Math.random() * 2 - 1) * 0.22 * env * trem;
      out[g0 + g] += Math.sin(2 * Math.PI * f0 * ((g0 + g) / sampleRate)) * 0.2 * env;
    }
  } else if (label.indexOf("chorus") >= 0) {
    tone(0, n, f0, 0.28, Math.floor(0.04 * sampleRate));
    tone(0, n, f0 * 1.25, 0.12, Math.floor(0.04 * sampleRate));
    var pulse = Math.floor(sampleRate * 0.045);
    for (var p = 0; p < n; p += pulse) tone(p, Math.floor(pulse * 0.45), f0, 0.25, Math.floor(pulse * 0.1));
  } else {
    var count = label.indexOf("croak") >= 0 ? 9 : 5;
    var gap = Math.floor(n / (count + 1));
    var plen = Math.floor(sampleRate * (label.indexOf("croak") >= 0 ? 0.045 : 0.07));
    for (var k = 0; k < count; k++) {
      tone(gap * (k + 1), plen, f0, 0.5, Math.floor(plen * 0.2));
      tone(gap * (k + 1), plen, f0 * 1.5, 0.12, Math.floor(plen * 0.2));
    }
  }
  var peak = 0.001;
  for (var j = 0; j < n; j++) peak = Math.max(peak, Math.abs(out[j]));
  var gain = 0.85 / peak;
  for (var q = 0; q < n; q++) out[q] *= gain;
  return { samples: out, sampleRate: sampleRate, synthetic: true, audio: null };
}

async function fsLoadClip(det) {
  if (fsState.clipCache[det.id]) return fsState.clipCache[det.id];
  if (fsState.source !== "live") {
    fsState.clipCache[det.id] = fsSynthSamples(det);
    return fsState.clipCache[det.id];
  }
  var url = fsClipUrl(det);
  if (!url) throw new Error("no clip path on this detection");
  var res = await fetch(url);
  if (!res.ok) throw new Error("clip HTTP " + res.status);
  var raw = await res.arrayBuffer();
  var ctx = fsAudioCtx();
  var audio = await ctx.decodeAudioData(raw.slice(0));
  var pack = {
    audio: audio,
    samples: audio.getChannelData(0),
    sampleRate: audio.sampleRate,
    synthetic: false
  };
  fsState.clipCache[det.id] = pack;
  return pack;
}

function fsAudioCtx() {
  if (!fsState.audioCtx) {
    var AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) throw new Error("Web Audio is not available in this browser");
    fsState.audioCtx = new AC();
  }
  return fsState.audioCtx;
}

function fftRadix2(re, im) {
  var n = re.length;
  for (var i = 1, j = 0; i < n; i++) {
    var bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) {
      var tr = re[i]; re[i] = re[j]; re[j] = tr;
      var ti = im[i]; im[i] = im[j]; im[j] = ti;
    }
  }
  for (var len = 2; len <= n; len <<= 1) {
    var ang = -2 * Math.PI / len;
    var wlenRe = Math.cos(ang), wlenIm = Math.sin(ang);
    for (var k = 0; k < n; k += len) {
      var wRe = 1, wIm = 0;
      var half = len >> 1;
      for (var m = 0; m < half; m++) {
        var ur = re[k + m], ui = im[k + m];
        var vr = re[k + m + half] * wRe - im[k + m + half] * wIm;
        var vi = re[k + m + half] * wIm + im[k + m + half] * wRe;
        re[k + m] = ur + vr;
        im[k + m] = ui + vi;
        re[k + m + half] = ur - vr;
        im[k + m + half] = ui - vi;
        var next = wRe * wlenRe - wIm * wlenIm;
        wIm = wRe * wlenIm + wIm * wlenRe;
        wRe = next;
      }
    }
  }
}

function fsSpecColor(t) {
  var stops = [
    [0, [7, 20, 28]],
    [0.35, [8, 70, 98]],
    [0.62, [10, 126, 164]],
    [0.82, [140, 220, 214]],
    [1, [255, 224, 130]]
  ];
  var i = 0;
  while (i < stops.length - 1 && t > stops[i + 1][0]) i++;
  var a = stops[i], b = stops[Math.min(i + 1, stops.length - 1)];
  var u = b[0] === a[0] ? 0 : (t - a[0]) / (b[0] - a[0]);
  return [
    Math.round(a[1][0] + (b[1][0] - a[1][0]) * u),
    Math.round(a[1][1] + (b[1][1] - a[1][1]) * u),
    Math.round(a[1][2] + (b[1][2] - a[1][2]) * u)
  ];
}

function drawFishSpectrogram(canvas, samples, sampleRate, band) {
  var cssH = 180;
  var cssW = canvas.clientWidth || canvas.parentElement && canvas.parentElement.clientWidth || 420;
  if (cssW < 40) cssW = 420;
  var dpr = Math.min(2, window.devicePixelRatio || 1);
  canvas.width = Math.floor(cssW * dpr);
  canvas.height = Math.floor(cssH * dpr);
  canvas.style.width = "100%";
  canvas.style.height = cssH + "px";
  var ctx = canvas.getContext("2d");
  ctx.fillStyle = "#07141C";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  var fftSize = 512;
  if (samples.length < fftSize) return;
  var maxFreq = Math.min(4000, sampleRate / 2);
  var maxBin = Math.max(2, Math.floor(maxFreq / (sampleRate / fftSize)));
  var targetCols = 180;
  var hop = Math.max(64, Math.floor((samples.length - fftSize) / targetCols));
  var cols = Math.max(1, Math.floor((samples.length - fftSize) / hop));
  var re = new Float32Array(fftSize);
  var im = new Float32Array(fftSize);
  var spec = new Array(cols);
  var peak = 1e-9;
  for (var c = 0; c < cols; c++) {
    var off = c * hop;
    for (var i = 0; i < fftSize; i++) {
      var w = 0.5 * (1 - Math.cos((2 * Math.PI * i) / (fftSize - 1)));
      re[i] = (samples[off + i] || 0) * w;
      im[i] = 0;
    }
    fftRadix2(re, im);
    var mags = new Float32Array(maxBin);
    for (var b = 1; b < maxBin; b++) {
      var mag = Math.hypot(re[b], im[b]) / fftSize;
      mags[b] = mag;
      if (mag > peak) peak = mag;
    }
    spec[c] = mags;
  }
  var plotL = Math.floor(36 * dpr);
  var plotB = Math.floor(16 * dpr);
  var plotT = Math.floor(8 * dpr);
  var plotR = Math.floor(6 * dpr);
  var plotW = canvas.width - plotL - plotR;
  var plotH = canvas.height - plotT - plotB;
  var img = ctx.createImageData(plotW, plotH);
  for (var x = 0; x < plotW; x++) {
    var col = spec[Math.min(cols - 1, Math.floor(x / plotW * cols))];
    for (var y = 0; y < plotH; y++) {
      var freq = (1 - y / plotH) * maxFreq;
      var bin = freq / (sampleRate / fftSize);
      var b0 = Math.max(0, Math.min(maxBin - 1, Math.floor(bin)));
      var db = 20 * Math.log10(col[b0] / peak + 1e-8);
      var t = Math.max(0, Math.min(1, (db + 68) / 68));
      var rgb = fsSpecColor(t);
      var p = (y * plotW + x) * 4;
      img.data[p] = rgb[0];
      img.data[p + 1] = rgb[1];
      img.data[p + 2] = rgb[2];
      img.data[p + 3] = 255;
    }
  }
  ctx.putImageData(img, plotL, plotT);
  ctx.fillStyle = "#D5E8F0";
  ctx.font = Math.floor(10 * dpr) + "px sans-serif";
  ctx.fillText((maxFreq / 1000).toFixed(1) + " kHz", 2, plotT + Math.floor(10 * dpr));
  ctx.fillText("0", 8 * dpr, plotT + plotH);
  ctx.fillText("time", plotL, canvas.height - 3);
  if (band && band.hi > band.lo && band.hi > 0) {
    var yHi = plotT + (1 - Math.min(band.hi, maxFreq) / maxFreq) * plotH;
    var yLo = plotT + (1 - Math.max(band.lo, 0) / maxFreq) * plotH;
    ctx.strokeStyle = "rgba(255,224,130,0.95)";
    ctx.lineWidth = Math.max(1, dpr);
    ctx.strokeRect(plotL + 0.5, yHi + 0.5, plotW - 1, Math.max(1, yLo - yHi));
  }
}

function fsHourBuckets() {
  var now = new Date();
  now.setMinutes(0, 0, 0);
  now.setMilliseconds(0);
  var buckets = [];
  for (var i = 23; i >= 0; i--) {
    buckets.push({ t: new Date(now.getTime() - i * 3600000), count: 0 });
  }
  var nodeId = fsState.selectedNodeId;
  fsState.hourly.forEach(function (r) {
    if (r.node_id !== nodeId) return;
    if (fsState.speciesFilter && r.species_id !== fsState.speciesFilter) return;
    var idx = -1;
    var key = fsFloorHour(r.hour);
    for (var b = 0; b < buckets.length; b++) if (buckets[b].t.getTime() === key) idx = b;
    if (idx >= 0) buckets[idx].count += Number(r.detections) || 0;
  });
  return buckets;
}

function fsSpeciesTotals() {
  var totals = {};
  fsState.hourly.forEach(function (r) {
    if (r.node_id !== fsState.selectedNodeId) return;
    if (fsState.speciesFilter && r.species_id !== fsState.speciesFilter) return;
    var key = fsFloorHour(r.hour);
    var now = new Date();
    now.setMinutes(0, 0, 0);
    now.setMilliseconds(0);
    if (key < now.getTime() - 23 * 3600000 || key > now.getTime()) return;
    totals[r.species_id] = (totals[r.species_id] || 0) + (Number(r.detections) || 0);
  });
  return totals;
}

function fsChartSvg(buckets) {
  var w = 440, h = 148, padL = 32, padB = 22, padT = 8, padR = 4;
  var max = 1;
  buckets.forEach(function (b) { if (b.count > max) max = b.count; });
  var innerW = w - padL - padR;
  var innerH = h - padT - padB;
  var bw = innerW / buckets.length;
  var parts = [];
  parts.push('<svg class="fs-chart" viewBox="0 0 ' + w + ' ' + h + '" role="img" aria-label="Calls detected per hour">');
  [0, 0.5, 1].forEach(function (g) {
    var y = padT + innerH - g * innerH;
    var label = Math.round(max * g);
    parts.push('<line x1="' + padL + '" y1="' + y + '" x2="' + (w - padR) + '" y2="' + y + '" stroke="#D0DAE4" stroke-width="1"/>');
    parts.push('<text x="' + (padL - 4) + '" y="' + (y + 3) + '" text-anchor="end" font-size="9" fill="#5A6B7C">' + label + "</text>");
  });
  buckets.forEach(function (b, i) {
    var bh = (b.count / max) * innerH;
    var x = padL + i * bw + 1;
    var y = padT + innerH - bh;
    var label = b.t.toLocaleTimeString([], { hour: "numeric" });
    parts.push('<rect x="' + x.toFixed(1) + '" y="' + y.toFixed(1) + '" width="' + Math.max(1, bw - 2).toFixed(1) + '" height="' + Math.max(0, bh).toFixed(1) + '" rx="2" fill="' + (b.count ? "#0A7EA4" : "#E2EAF0") + '"><title>' + fsEsc(label) + ": " + b.count + " calls detected</title></rect>");
    if (i % 4 === 0) parts.push('<text x="' + (x + bw / 2).toFixed(1) + '" y="' + (h - 6) + '" text-anchor="middle" font-size="9" fill="#5A6B7C">' + fsEsc(label) + "</text>");
  });
  parts.push("</svg>");
  return parts.join("");
}

function fsStatusDot(status) {
  if (status === "online") return "#43A047";
  if (status === "degraded") return "#FF8F00";
  return "#999";
}

function pageFishSounds() {
  var head = hdr("Fish Sounds", "Tappan Zee to Poughkeepsie · West Point / Cornwall centered");
  if (!fsState.ready) {
    setTimeout(ensureFishData, 0);
    return head + '<div class="page on"><div class="card"><div class="tl">Loading</div><div class="tp">Fetching the hydrophone feed…</div></div></div>';
  }
  setTimeout(mountFishSounds, 30);
  return head + fsBody();
}

function fsBody() {
  var live = fsState.source === "live";
  var bannerClass = live && !fsState.notice ? "fs-banner live" : "fs-banner";
  var bannerText = fsState.notice || (live ? "Live detections · Supabase Realtime on the detections table." : "Sample data.");
  var h = '<div class="page on" id="fs-page">';
  h += '<div class="' + bannerClass + '">' + fsEsc(bannerText) + "</div>";

  h += '<div class="fs-map-wrap" id="fs-map-wrap"><div id="fs-map"></div></div>';

  h += '<div class="card"><div class="tl">Hydrophone nodes</div><div class="fs-nodes">';
  fsState.nodes.forEach(function (n) {
    var on = n.id === fsState.selectedNodeId ? " on" : "";
    h += '<button type="button" class="fc' + on + '" data-fs-node="' + fsEsc(n.id) + '">' + fsEsc(n.name) + "</button>";
  });
  h += "</div>";
  var node = fsNode(fsState.selectedNodeId);
  if (node) {
    h += '<div class="sl" style="margin-top:8px">RM ' + fsEsc(node.river_mile) + " · " + fsEsc(node.hardware || "hydrophone") + " · " + fsEsc(node.sample_rate_hz || "?") + " Hz · " + fsEsc(node.status || "unknown");
    if (node.last_heartbeat) h += " · heartbeat " + fsEsc(fsRelTime(node.last_heartbeat));
    h += "</div>";
  }
  h += "</div>";

  var buckets = fsHourBuckets();
  var total = 0;
  buckets.forEach(function (b) { total += b.count; });
  h += '<div class="card"><div class="tl">Calls detected per hour</div>';
  h += '<label class="sl" for="fs-species-filter">Species filter</label>';
  h += '<select id="fs-species-filter" class="fs-select">';
  h += '<option value="">All species</option>';
  fsState.species.forEach(function (s) {
    var sel = fsState.speciesFilter === s.id ? " selected" : "";
    h += '<option value="' + fsEsc(s.id) + '"' + sel + ">" + fsEsc(s.common_name) + "</option>";
  });
  h += "</select>";
  h += fsChartSvg(buckets);
  h += '<div class="fs-total">' + total + " calls detected · last 24 hours · " + fsEsc(node ? node.name : "") + "</div>";
  var totals = fsSpeciesTotals();
  var bits = Object.keys(totals).map(function (id) {
    var s = fsSpecies(id);
    return (s ? s.common_name : id) + " " + totals[id];
  });
  if (bits.length) h += '<div class="sl" style="margin-top:6px">' + fsEsc(bits.join(" · ")) + "</div>";
  h += '<div class="tp" style="margin-top:10px">Calls detected per hour is an activity index: how many calls the model marked in that hour. It is not a count of individual fish. One fish can call many times, and a chorus can be many fish in one detection.</div>';
  h += "</div>";

  h += '<div class="card"><div class="tl">Detections</div>';
  if (!fsState.detections.length) {
    h += '<div class="sl">No detections yet.</div>';
  } else {
    fsState.detections.slice(0, 40).forEach(function (d) {
      var sp = fsSpecies(d.species_id);
      var nd = fsNode(d.node_id);
      var on = d.id === fsState.selectedId ? " on" : "";
      var pct = Math.round((Number(d.confidence) || 0) * 100);
      h += '<button type="button" class="fs-det' + on + '" data-fs-det="' + fsEsc(d.id) + '">';
      h += '<div class="fs-det-top"><strong>' + fsEsc(sp ? sp.common_name : (d.label || "Unidentified")) + "</strong><span>" + pct + "%</span></div>";
      h += '<div class="sl">' + fsEsc(nd ? nd.name : d.node_id) + " · " + fsEsc(fsRelTime(d.start_time)) + " · " + fsEsc(d.label || "") + " · " + fsEsc(d.review_status || "unreviewed") + "</div>";
      h += "</button>";
    });
  }
  h += "</div>";

  h += fsDetailHtml();

  h += '<div class="card"><div class="tl">Species</div><div class="sl" style="margin:-4px 0 10px">From the species table. Soniferous means this network treats the fish as a sound producer.</div>';
  fsState.species.forEach(function (s) {
    h += '<article class="fs-species">';
    h += '<div class="fs-sp-head"><div><div class="sn">' + fsEsc(s.common_name) + '</div><div class="sl"><em>' + fsEsc(s.scientific_name || "") + "</em></div></div>";
    h += '<span class="fs-badge' + (s.soniferous ? " on" : "") + '">' + (s.soniferous ? "Soniferous" : "Not soniferous") + "</span></div>";
    if (s.call_description) h += '<p class="fs-desc">' + fsEsc(s.call_description) + "</p>";
    var band = s.freq_low_hz != null && s.freq_high_hz != null ? (s.freq_low_hz + "–" + s.freq_high_hz + " Hz") : "No call band";
    h += '<div class="sl">' + fsEsc(band) + (s.season ? " · " + fsEsc(s.season) : "") + "</div>";
    if (s.fishsounds_url) h += '<a class="fs-link" href="' + fsEsc(s.fishsounds_url) + '" target="_blank" rel="noopener noreferrer">FishSounds catalog</a>';
    h += "</article>";
  });
  h += "</div>";

  h += '<div class="card"><div class="tl">About this feed</div><div class="tp">Nodes on this stretch: Tappan Zee (RM 27), West Point / Cornwall (RM 53), and Poughkeepsie (RM 75). Clips live in the public Supabase Storage bucket named audio. The spectrogram is computed in your browser with Web Audio and is not uploaded. Configure the project in config.js.</div></div>';
  h += "</div>";
  return h;
}

function fsDetailHtml() {
  var det = null;
  for (var i = 0; i < fsState.detections.length; i++) if (fsState.detections[i].id === fsState.selectedId) det = fsState.detections[i];
  if (!det) {
    return '<div class="card" id="fs-detail"><div class="tl">Clip</div><div class="sl">Select a detection to see its spectrogram and play the clip.</div></div>';
  }
  var sp = fsSpecies(det.species_id);
  var nd = fsNode(det.node_id);
  var pct = Math.round((Number(det.confidence) || 0) * 100);
  var h = '<div class="card" id="fs-detail">';
  h += '<div class="tl">Clip · ' + fsEsc(sp ? sp.common_name : (det.label || "Unidentified")) + "</div>";
  h += '<div class="sl">' + fsEsc(nd ? nd.name : det.node_id) + " · " + fsEsc(new Date(det.start_time).toLocaleString()) + "</div>";
  h += '<div class="param-grid" style="margin-top:10px">';
  h += '<div class="param-item"><div class="param-val">' + pct + '%</div><div class="param-name">Confidence</div></div>';
  h += '<div class="param-item"><div class="param-val" style="font-size:14px">' + fsEsc(det.freq_low_hz != null ? det.freq_low_hz + "–" + det.freq_high_hz + " Hz" : "—") + '</div><div class="param-name">Call band</div></div>';
  h += '<div class="param-item"><div class="param-val" style="font-size:14px">' + fsEsc(det.review_status || "unreviewed") + '</div><div class="param-name">Review</div></div>';
  h += '<div class="param-item"><div class="param-val" style="font-size:13px">' + fsEsc((det.model_name || "model") + (det.model_version ? " " + det.model_version : "")) + '</div><div class="param-name">Classifier</div></div>';
  h += "</div>";
  h += '<canvas id="fs-spec" class="fs-spec" aria-label="Spectrogram of the selected clip"></canvas>';
  h += '<div class="sl" id="fs-spec-status">Drawing spectrogram…</div>';
  h += '<button type="button" class="fs-play" id="fs-play">Play clip</button>';
  if (fsState.source !== "live") {
    h += '<div class="tp" style="margin-top:10px">Sample clip, synthesized in your browser from this species\' frequency band so the spectrogram and player work without a recording. A configured project plays the hydrophone file from the audio bucket instead.</div>';
  } else {
    h += '<div class="tp" style="margin-top:10px">Spectrogram generated in the browser from the hydrophone clip. Nothing is uploaded.</div>';
  }
  h += "</div>";
  return h;
}

function mountFishSounds() {
  if (typeof cur !== "undefined" && cur !== "sounds") return;
  if (!document.getElementById("fs-map")) return;
  initFishMap();
  document.querySelectorAll("[data-fs-node]").forEach(function (el) {
    el.addEventListener("click", function () { setFishNode(el.getAttribute("data-fs-node")); });
  });
  document.querySelectorAll("[data-fs-det]").forEach(function (el) {
    el.addEventListener("click", function () { selectFishDetection(el.getAttribute("data-fs-det"), true); });
  });
  var filter = document.getElementById("fs-species-filter");
  if (filter) filter.addEventListener("change", function () {
    fsState.speciesFilter = filter.value;
    render();
  });
  var play = document.getElementById("fs-play");
  if (play) play.addEventListener("click", playFishClip);
  drawSelectedFishSpectrogram();
  if (fsState.scrollDetail) {
    fsState.scrollDetail = false;
    var detail = document.getElementById("fs-detail");
    if (detail) detail.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}

function setFishNode(id) {
  if (!id || id === fsState.selectedNodeId) return;
  fsState.selectedNodeId = id;
  render();
}

function selectFishDetection(id, scroll) {
  fsState.selectedId = id;
  fsState.scrollDetail = !!scroll;
  var det = null;
  for (var i = 0; i < fsState.detections.length; i++) if (fsState.detections[i].id === id) det = fsState.detections[i];
  if (det && det.node_id && fsNode(det.node_id)) fsState.selectedNodeId = det.node_id;
  render();
}

function teardownFishSounds() {
  if (fsState.fsMap) {
    try { fsState.fsMap.remove(); } catch (e) {}
    fsState.fsMap = null;
  }
  if (fsState.playing) {
    try { fsState.playing.stop(); } catch (e) {}
    fsState.playing = null;
  }
}

function fsTiles() {
  var night = typeof dark !== "undefined" && dark;
  if (night) {
    return L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      attribution: '&copy; OpenStreetMap &copy; CARTO',
      subdomains: "abcd",
      maxZoom: 19
    });
  }
  return L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19
  });
}

function initFishMap() {
  var el = document.getElementById("fs-map");
  if (!el) return;
  if (typeof L === "undefined") {
    el.innerHTML = '<div class="map-fallback">Map library did not load.</div>';
    return;
  }
  teardownFishSounds();
  var map = L.map(el, { zoomControl: true, attributionControl: true });
  fsTiles().addTo(map);
  var stretch = L.latLngBounds([41.05, -74.12], [41.74, -73.86]);
  map.fitBounds(stretch, { padding: [16, 16] });
  L.control.scale({ imperial: true, metric: false }).addTo(map);
  fsState.nodes.forEach(function (n) {
    if (n.lat == null || n.lon == null) return;
    var selected = n.id === fsState.selectedNodeId;
    var color = fsStatusDot(n.status);
    var icon = L.divIcon({
      className: "pin-icon",
      html: '<div style="width:18px;height:18px;border-radius:50%;background:' + color + ";border:3px solid " + (selected ? "#0A7EA4" : "#fff") + ";box-shadow:0 0 0 5px " + color + '33"></div>',
      iconSize: [18, 18],
      iconAnchor: [9, 9]
    });
    var marker = L.marker([Number(n.lat), Number(n.lon)], { icon: icon, title: n.name });
    var popup = "<strong>" + fsEsc(n.name) + "</strong><br>RM " + fsEsc(n.river_mile) + "<br>" + fsEsc(n.status || "") + "<br>" + fsEsc(n.hardware || "");
    marker.bindPopup(popup);
    marker.on("click", function () {
      var nodeId = n.id;
      setTimeout(function () { setFishNode(nodeId); }, 0);
    });
    marker.addTo(map);
  });
  fsState.fsMap = map;
  setTimeout(function () {
    if (!fsState.fsMap) return;
    fsState.fsMap.invalidateSize();
    fsState.fsMap.fitBounds(stretch, { padding: [16, 16] });
  }, 60);
}

async function drawSelectedFishSpectrogram() {
  var canvas = document.getElementById("fs-spec");
  var det = null;
  for (var i = 0; i < fsState.detections.length; i++) if (fsState.detections[i].id === fsState.selectedId) det = fsState.detections[i];
  if (!canvas || !det) return;
  var token = ++fsState.drawToken;
  var status = document.getElementById("fs-spec-status");
  try {
    var pack = await fsLoadClip(det);
    if (token !== fsState.drawToken || !document.body.contains(canvas)) return;
    var sp = fsSpecies(det.species_id) || {};
    drawFishSpectrogram(canvas, pack.samples, pack.sampleRate, {
      lo: det.freq_low_hz || sp.freq_low_hz || 0,
      hi: det.freq_high_hz || sp.freq_high_hz || 0
    });
    if (status) {
      status.textContent = pack.synthetic
        ? "In-browser spectrogram of the sample clip. Yellow box is the call band."
        : "In-browser spectrogram of the hydrophone clip. Yellow box is the call band.";
    }
  } catch (err) {
    if (status) status.textContent = "Could not build a spectrogram (" + err.message + ").";
  }
}

async function playFishClip() {
  var det = null;
  for (var i = 0; i < fsState.detections.length; i++) if (fsState.detections[i].id === fsState.selectedId) det = fsState.detections[i];
  var btn = document.getElementById("fs-play");
  if (!det) return;
  try {
    var pack = await fsLoadClip(det);
    var ctx = fsAudioCtx();
    if (ctx.state === "suspended") await ctx.resume();
    if (!pack.audio) {
      var buffer = ctx.createBuffer(1, pack.samples.length, pack.sampleRate);
      buffer.copyToChannel ? buffer.copyToChannel(pack.samples, 0) : buffer.getChannelData(0).set(pack.samples);
      pack.audio = buffer;
    }
    if (fsState.playing) {
      try { fsState.playing.stop(); } catch (e) {}
    }
    var src = ctx.createBufferSource();
    src.buffer = pack.audio;
    src.connect(ctx.destination);
    src.start();
    fsState.playing = src;
    if (btn) btn.textContent = pack.synthetic ? "Playing sample clip…" : "Playing clip…";
    src.onended = function () { if (btn) btn.textContent = "Play clip"; };
  } catch (err) {
    if (btn) btn.textContent = "Playback failed";
    var status = document.getElementById("fs-spec-status");
    if (status) status.textContent = "Playback failed (" + err.message + ").";
  }
}
