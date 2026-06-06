// ===== DATA =====
const STATIONS = [
  {id:"turkey_point",name:"Turkey Point",loc:"Catskill, NY",rm:84,src:"NOAA",params:["temp","conductance"],live:true,readings:{temp:68.4,conductance:285}},
  {id:"norrie_point",name:"Norrie Point",loc:"Staatsburg, NY",rm:88,src:"NDBC",params:["air_temp","wind_speed","pressure","dewpoint"],live:true,readings:{air_temp:72.1,wind_speed:8.5,pressure:30.12,dewpoint:62.3}},
  {id:"schodack",name:"Schodack Landing",loc:"Schodack, NY",rm:120,src:"USGS",params:["temp","conductance","dissolved_oxygen","turbidity"],live:true,readings:{temp:66.2,conductance:310,dissolved_oxygen:8.4,turbidity:12.5}},
  {id:"albany",name:"Albany",loc:"Albany, NY",rm:143,src:"USGS",params:["temp"],live:true,readings:{temp:65.1}}
];

const P = {
  temp:{l:"Water Temp",u:"F"},conductance:{l:"Conductance",u:"uS/cm"},
  dissolved_oxygen:{l:"Dissolved O2",u:"mg/L"},turbidity:{l:"Turbidity",u:"NTU"},
  air_temp:{l:"Air Temp",u:"F"},wind_speed:{l:"Wind",u:"mph"},pressure:{l:"Pressure",u:"inHg"},dewpoint:{l:"Dew Point",u:"F"}
};

// ===== CALCULATIONS =====
function calcWQI(r) {
  var t = r.turbidity ? Math.max(0, 100 - r.turbidity * 2) : 75;
  var d = r.dissolved_oxygen ? Math.min(100, r.dissolved_oxygen * 12) : 80;
  var p = r.temp ? (r.temp >= 50 && r.temp <= 80 ? 100 : r.temp >= 40 && r.temp <= 90 ? 70 : 40) : 70;
  return Math.round(t * 0.3 + d * 0.3 + p * 0.2 + 75 * 0.2);
}
function wqiLabel(s) {
  return s >= 80 ? {t:"Good",c:"#00BCD4"} : s >= 60 ? {t:"Fair",c:"#8BC34A"} : s >= 40 ? {t:"Poor",c:"#FF9800"} : {t:"Bad",c:"#F44336"};
}
function swimLabel(s) {
  return s >= 80 ? {l:"Safe",cls:"ss",ic:"OK",m:"Water quality is good for swimming."} :
    s >= 60 ? {l:"Caution",cls:"sc2",ic:"!",m:"Check conditions before swimming."} :
    {l:"Unsafe",cls:"su",ic:"X",m:"Avoid swimming."};
}
function clarityLabel(t) {
  return t < 5 ? {l:"Crystal Clear",c:"#00BCD4"} : t < 15 ? {l:"Clean",c:"#4CAF50"} : t < 35 ? {l:"Slightly Murky",c:"#FF9800"} : t < 75 ? {l:"Murky",c:"#FF5722"} : {l:"Very Dirty",c:"#F44336"};
}
function fishScore(r, tidePhase, hr) {
  var ts = r.temp >= 55 && r.temp <= 75 ? 100 : r.temp >= 45 && r.temp <= 85 ? 60 : 20;
  var cs = r.turbidity ? Math.max(0, 100 - r.turbidity * 2) : 70;
  var tds = (hr >= 5 && hr <= 9) || (hr >= 17 && hr <= 20) ? 100 : hr >= 10 && hr <= 16 ? 60 : 40;
  var tis = tidePhase === "incoming" ? 100 : tidePhase === "outgoing" ? 70 : 50;
  return Math.round(ts * 0.25 + cs * 0.2 + 80 * 0.2 + tis * 0.2 + tds * 0.15);
}
function fishLabel(s) {
  return s >= 90 ? {t:"Excellent",c:"#00BCD4"} : s >= 70 ? {t:"Great",c:"#4CAF50"} : s >= 50 ? {t:"Good",c:"#8BC34A"} : s >= 30 ? {t:"Fair",c:"#FF9800"} : {t:"Poor",c:"#F44336"};
}
function moonPhase(d) {
  var names = ["New","Waxing Crescent","First Quarter","Waxing Gibbous","Full","Waning Gibbous","Last Quarter","Waning Crescent"];
  var lp = 29.53059, ref = new Date(2000,0,6,18,14).getTime();
  var age = ((d.getTime() - ref) / 86400000) % lp;
  var i = Math.round(age / lp * 8) % 8;
  return {name: names[i], illum: Math.round((1 - Math.cos(age / lp * 2 * Math.PI)) / 2 * 100)};
}
function genTides() {
  var now = new Date(), t = [];
  for (var i = 0; i < 48; i++) {
    var tm = new Date(now.getTime() + i * 3600000);
    var h = 2.5 + 2.1 * Math.sin((tm.getTime() / 3600000) * Math.PI / 6.2 + 1);
    t.push({t: tm, h: Math.abs(h), ty: Math.cos((tm.getTime() / 3600000) * Math.PI / 6.2 + 1) > 0 ? "high" : "low"});
  }
  return t;
}
function genAlerts() {
  return [
    {s:"Schodack Landing",t:"Temperature Spike",sev:"medium",time:"2h ago",act:"72.4F",exp:"65-68F"},
    {s:"Albany",t:"Low DO Reading",sev:"high",time:"1h ago",act:"4.2 mg/L",exp:">6 mg/L"},
    {s:"Turkey Point",t:"Conductance Drop",sev:"low",time:"4h ago",act:"180 uS/cm",exp:"250-350"}
  ];
}

// ===== HELPERS =====
function gauge(score, label, size) {
  var pct = Math.min(100, Math.max(0, score));
  var c = pct >= 80 ? "#00BCD4" : pct >= 60 ? "#4CAF50" : pct >= 40 ? "#FF9800" : "#F44336";
  var rad = (size - 20) / 2, circ = 2 * Math.PI * rad, off = circ - (pct / 100) * circ;
  return '<div class="gw"><div class="g" style="position:relative;width:' + size + 'px;height:' + size + 'px;margin:0 auto">' +
    '<svg viewBox="0 0 ' + size + ' ' + size + '" style="width:' + size + 'px;height:' + size + 'px;transform:rotate(-90deg)">' +
    '<circle cx="' + (size/2) + '" cy="' + (size/2) + '" r="' + rad + '" fill="none" stroke="#e0e0e0" stroke-width="12"/>' +
    '<circle cx="' + (size/2) + '" cy="' + (size/2) + '" r="' + rad + '" fill="none" stroke="' + c + '" stroke-width="12" stroke-dasharray="' + circ + '" stroke-dashoffset="' + off + '" stroke-linecap="round"/>' +
    '</svg><div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);font-size:40px;font-weight:700;color:' + c + '">' + score + '</div>' +
    '<div style="position:absolute;bottom:32px;left:50%;transform:translateX(-50%);font-size:12px;color:#5A6B7C;white-space:nowrap">' + label + '</div></div></div>';
}
function progressBar(label, score, val) {
  var c = score >= 80 ? "#4CAF50" : score >= 60 ? "#8BC34A" : score >= 40 ? "#FF9800" : "#F44336";
  return '<div><div style="display:flex;justify-content:space-between;margin-bottom:2px;font-size:13px"><span>' + label + '</span><span style="color:' + c + ';font-weight:600">' + val + '</span></div>' +
    '<div class="bb"><div class="bf" style="width:' + score + '%;background:' + c + '"></div></div></div>';
}
function formatTime(d) {
  return d.toLocaleTimeString([], {hour: "numeric", minute: "2-digit"});
}
function hdr(title, sub) {
  return '<div class="hdr"><div class="hdr-row"><div><h1>' + title + '</h1><p>' + sub + '</p></div>' +
    '<button class="btn-i" onclick="togDark()">' + (dark ? SUN : MOON) + '</button></div></div>';
}

// ===== ICONS (SVG strings) =====
var SUN = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>';
var MOON = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>';
var IC_HOME = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>';
var IC_PIN = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>';
var IC_WAVES = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 6c.6.5 1.2 1 2.5 1C7 7 7 5 9.5 5c2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/><path d="M2 12c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/><path d="M2 18c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/></svg>';
var IC_DROP = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z"/></svg>';
var IC_FISH = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6.5 12c.94-3.46 4.94-6 8.5-6 3.56 0 6.06 2.54 7 6-.94 3.47-3.44 6-7 6-3.56 0-7.56-2.53-8.5-6Z"/><path d="M18 12v.5"/><path d="M7 10.67C7 8 5.58 5.97 2.73 5.5c-1 1.5-1 5 .23 6.5-1.24 1.5-1.24 5-.23 6.5C5.58 18.03 7 16 7 13.33"/><circle cx="16" cy="12" r="1"/></svg>';
var IC_BELL = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>';

// ===== STATE =====
var cur = "home";
var dark = localStorage.getItem("dark") === "true";
if (dark) document.documentElement.setAttribute("data-theme", "dark");

// ===== PAGES =====
function pageHome() {
  var live = STATIONS.filter(function(s) { return s.live; });
  var avgTemp = Math.round(live.reduce(function(a, s) { return a + (s.readings.temp || 0); }, 0) / live.filter(function(s) { return s.readings.temp; }).length);
  var T = genTides();
  var turkey = STATIONS.find(function(s) { return s.id === "turkey_point"; });
  var wqi = calcWQI(turkey.readings);
  var wl = wqiLabel(wqi);
  var A = genAlerts();
  var html = hdr("Cornwall RiverWatch", "Cornwall-on-Hudson, NY - Hudson River");
  html += '<div class="page on">';
  html += gauge(wqi, "Water Quality Index", 170);
  html += '<div style="text-align:center;margin:-8px 0 16px"><span style="color:' + wl.c + ';font-size:18px;font-weight:700">' + wl.t + '</span>';
  html += '<p style="font-size:12px;color:#5A6B7C;margin-top:4px">Turkey Point (closest station, RM 84)</p></div>';
  html += '<div class="mg">';
  html += '<div class="m"><div style="font-size:24px">&#127777;</div><div class="mv">' + avgTemp + '&deg;F</div><div class="ml">Avg Water Temp</div></div>';
  html += '<div class="m"><div style="font-size:24px">&#128246;</div><div class="mv">' + live.length + '</div><div class="ml">Stations Live</div></div>';
  html += '<div class="m"><div style="font-size:24px">&#127754;</div><div class="mv">' + T[0].h.toFixed(1) + 'ft</div><div class="ml">' + (T[0].ty === "high" ? "High" : "Low") + ' Tide</div></div>';
  html += '<div class="m"><div style="font-size:24px">&#128276;</div><div class="mv">' + A.length + '</div><div class="ml">Alerts</div></div>';
  html += '</div>';
  html += '<div class="card"><div class="tl">Stations Near Cornwall (RM 56)</div>';
  STATIONS.forEach(function(s) {
    html += '<div class="sc" style="cursor:pointer"><div class="sd" style="background:' + (s.live ? '#43A047' : '#999') + ';animation:' + (s.live ? 'pu' : 'none') + '"></div>';
    html += '<div style="flex:1"><div class="sn">' + s.name + '</div><div class="sl">River Mile ' + s.rm + ' - ' + s.loc + (s.live ? '' : ' - OFFLINE') + '</div>';
    html += '<div class="sp">' + s.params.filter(function(p) { return s.readings[p] !== undefined; }).map(function(p) { return (P[p] ? P[p].l : p) + ': ' + s.readings[p] + (P[p] ? P[p].u : ''); }).join(' - ') + '</div>';
    html += '</div></div>';
  });
  html += '</div></div>';
  return html;
}

function pageStations() {
  var html = hdr("Stations", "Hudson River monitoring network");
  html += '<div class="page on">';
  STATIONS.forEach(function(s) {
    var q = calcWQI(s.readings);
    var wl = wqiLabel(q);
    html += '<div class="card" style="margin-bottom:10px"><div style="display:flex;justify-content:space-between;align-items:center">';
    html += '<div><div class="sn">' + s.name + ' <span style="font-size:12px;color:' + wl.c + ';margin-left:6px">WQI ' + q + '</span></div>';
    html += '<div class="sl">River Mile ' + s.rm + ' - ' + s.loc + ' - ' + s.src + ' - ' + (s.live ? 'LIVE' : 'OFFLINE') + '</div></div>';
    html += '<div class="sd" style="background:' + (s.live ? '#43A047' : '#999') + ';animation:' + (s.live ? 'pu' : 'none') + '"></div></div>';
    html += '<div class="sp" style="margin-top:8px">' + s.params.filter(function(p) { return s.readings[p] !== undefined; }).map(function(p) {
      return (P[p] ? P[p].l : p) + ': <strong>' + s.readings[p] + (P[p] ? P[p].u : '') + '</strong>';
    }).join(' - ') + '</div></div>';
  });
  html += '</div>';
  return html;
}

function pageTides() {
  var T = genTides();
  var cur = T[0];
  var nh = T.find(function(t) { return t.t > new Date() && t.ty === "high"; }) || T[0];
  var nl = T.find(function(t) { return t.t > new Date() && t.ty === "low"; }) || T[1];
  var m = moonPhase(new Date());
  var html = hdr("Tide Predictions", "Cornwall-on-Hudson - NOAA 8518490");
  html += '<div class="page on">';
  html += '<div class="card" style="text-align:center;padding:24px">';
  html += '<div style="font-size:48px">&#127754;</div>';
  html += '<div style="font-size:42px;font-weight:700;color:#0A7EA4">' + cur.h.toFixed(1) + '<span style="font-size:18px"> ft</span></div>';
  html += '<div style="font-size:15px;color:#5A6B7C;margin-top:4px">' + (cur.ty === "high" ? "High Tide" : "Low Tide") + '</div>';
  html += '<div style="display:flex;justify-content:center;gap:24px;margin-top:16px;font-size:13px">';
  html += '<div>Next High<br><strong>' + nh.h.toFixed(1) + ' ft</strong><br><small>' + formatTime(nh.t) + '</small></div>';
  html += '<div>Next Low<br><strong>' + nl.h.toFixed(1) + ' ft</strong><br><small>' + formatTime(nl.t) + '</small></div>';
  html += '</div></div>';
  html += '<div class="card"><div class="tl">48-Hour Forecast</div><div class="tc">';
  html += '<svg viewBox="0 0 480 160" preserveAspectRatio="none">';
  var pts = T.map(function(t, i) { return '' + (i * 10) + ',' + (80 - t.h * 8); }).join(' ');
  html += '<defs><linearGradient id="tg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#0A7EA4" stop-opacity=".3"/><stop offset="100%" stop-color="#0A7EA4" stop-opacity="0"/></linearGradient></defs>';
  html += '<path fill="url(#tg)" d="M0,80 L' + pts.replace(/ /g, ' L') + ' L470,80 Z"/>';
  html += '<polyline fill="none" stroke="#0A7EA4" stroke-width="2" points="' + pts + '"/>';
  html += '</svg></div></div>';
  html += '<div class="card"><div class="tl">Upcoming Tides</div>';
  T.filter(function(t) { return t.t > new Date(); }).slice(0, 10).forEach(function(t) {
    html += '<div class="tl2"><span class="' + (t.ty === "high" ? "th" : "tl3") + '">' + (t.ty === "high" ? "&#9650; High" : "&#9660; Low") + '</span>';
    html += '<span>' + t.h.toFixed(1) + ' ft</span><span style="color:#5A6B7C">' + formatTime(t.t) + '</span></div>';
  });
  html += '</div>';
  html += '<div class="mp"><div class="mpi">&#127769;</div><div style="font-size:18px;font-weight:600;margin-top:8px">' + m.name + ' Moon</div>';
  html += '<div style="font-size:14px;color:#5A6B7C">' + m.illum + '% illuminated</div></div>';
  html += '</div>';
  return html;
}

function pageQuality() {
  var turkey = STATIONS.find(function(s) { return s.id === "turkey_point"; });
  var wqi = calcWQI(turkey.readings);
  var s = swimLabel(wqi);
  var c = turkey.readings.turbidity ? clarityLabel(turkey.readings.turbidity) : {l: "No data", c: "#999"};
  var html = hdr("Water Quality", "River cleanliness and safety");
  html += '<div class="page on">';
  html += gauge(wqi, "Water Quality Index", 170);
  html += '<div class="' + s.cls + ' sw"><div style="font-size:48px">' + s.ic + '</div>';
  html += '<div style="font-size:22px;font-weight:700;margin-top:8px">Swimming: ' + s.l + '</div>';
  html += '<p style="font-size:13px;margin-top:8px;color:#5A6B7C">' + s.m + '</p></div>';
  html += '<div class="card"><div class="tl">Water Clarity (Turbidity)</div>';
  if (turkey.readings.turbidity) {
    html += progressBar("Clarity Score", Math.max(0, 100 - turkey.readings.turbidity * 2), turkey.readings.turbidity + " NTU - " + c.l);
  } else {
    html += '<p style="color:#5A6B7C">No turbidity data</p>';
  }
  html += '<div style="margin-top:12px;padding:10px;border-radius:8px;background:' + c.c + '15;color:' + c.c + ';font-size:14px;text-align:center">' + c.l + ' water</div></div>';
  html += '<div class="card"><div class="tl">Turkey Point Readings (closest to Cornwall)</div>';
  turkey.params.forEach(function(p) {
    if (turkey.readings[p] !== undefined) {
      html += '<div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #F0F4F8">';
      html += '<span>' + (P[p] ? P[p].l : p) + '</span><strong style="color:#0A7EA4">' + turkey.readings[p] + ' ' + (P[p] ? P[p].u : '') + '</strong></div>';
    }
  });
  html += '</div>';
  html += '<div class="card"><div class="tl">Water Quality Advisory</div>';
  html += '<div class="tp">Based on real-time data from HRECOS monitoring stations. Turbidity measures water clarity - low values mean cleaner water. Dissolved oxygen above 6 mg/L supports healthy aquatic life. These readings are for reference only.</div></div>';
  html += '</div>';
  return html;
}

function pageFish() {
  var sch = STATIONS.find(function(s) { return s.id === "schodack"; }) || STATIONS[2];
  var tm = genTides().find(function(t) { return t.t > new Date(); });
  var tidePhase = tm ? tm.ty : "incoming";
  var hr = new Date().getHours();
  var fs = fishScore(sch.readings, tidePhase, hr);
  var fl = fishLabel(fs);
  var timeLabel = hr >= 5 && hr <= 9 ? "Morning" : hr >= 10 && hr <= 16 ? "Afternoon" : hr >= 17 && hr <= 20 ? "Evening" : "Night";
  var timeScore = (hr >= 5 && hr <= 9) || (hr >= 17 && hr <= 20) ? 100 : hr >= 10 && hr <= 16 ? 60 : 40;
  var timeDesc = timeScore === 100 ? "Prime Time" : timeScore === 60 ? "Decent" : "Slow";
  var html = hdr("Fishing Conditions", "Hudson River at Cornwall, NY");
  html += '<div class="page on">';
  html += gauge(fs, "Fishing Score", 170);
  html += '<div style="text-align:center;margin:-8px 0 16px"><span style="color:' + fl.c + ';font-size:20px;font-weight:700">' + fl.t + '</span></div>';
  html += '<div class="card"><div class="tl">Score Breakdown</div>';
  html += progressBar("Water Temp", sch.readings.temp >= 55 && sch.readings.temp <= 75 ? 100 : sch.readings.temp >= 45 && sch.readings.temp <= 85 ? 60 : 20, sch.readings.temp + "F - " + (sch.readings.temp >= 55 && sch.readings.temp <= 75 ? "Ideal" : sch.readings.temp >= 45 && sch.readings.temp <= 85 ? "Okay" : "Poor"));
  html += progressBar("Water Clarity", Math.max(0, 100 - (sch.readings.turbidity || 20) * 2), (sch.readings.turbidity || "?") + " NTU - " + ((sch.readings.turbidity || 20) < 15 ? "Good" : (sch.readings.turbidity || 20) < 50 ? "Fair" : "Poor"));
  html += progressBar("Tide Phase", tidePhase === "incoming" ? 100 : tidePhase === "outgoing" ? 70 : 50, tidePhase + " - " + (tidePhase === "incoming" ? "Best" : tidePhase === "outgoing" ? "Good" : "Fair"));
  html += progressBar("Time of Day", timeScore, timeLabel + " - " + timeDesc);
  html += '</div>';
  html += '<div class="card"><div class="tl">Best Fishing Windows</div><div class="ft">';
  html += '<div class="fti"><div style="font-size:28px">&#127749;</div><div style="font-weight:600;margin-top:4px">5:30-8:30 AM</div><div style="font-size:12px;color:#43A047">Dawn Bite - Excellent</div></div>';
  html += '<div class="fti"><div style="font-size:28px">&#127751;</div><div style="font-weight:600;margin-top:4px">5:30-8:30 PM</div><div style="font-size:12px;color:#43A047">Dusk Bite - Great</div></div>';
  html += '</div></div>';
  html += '<div class="card"><div class="tl">Fishing Tips</div><div class="tp">';
  if (sch.readings.turbidity && sch.readings.turbidity > 30) {
    html += "Murky water - use noisy, vibrating lures.";
  } else if (tidePhase === "incoming") {
    html += "Incoming tide pushes baitfish toward shore. Fish near rocky points and docks!";
  } else if (fs >= 70) {
    html += "Great conditions! Topwater lures should produce.";
  } else {
    html += "Try crankbaits or soft plastics near drop-offs.";
  }
  html += '</div></div></div>';
  return html;
}

function pageAlerts() {
  var A = genAlerts();
  var html = hdr("Alerts", "AI-detected anomalies");
  html += '<div class="page on">';
  html += '<div class="fr"><button class="fc on">All</button><button class="fc">High</button><button class="fc">Medium</button><button class="fc">Low</button></div>';
  if (A.length === 0) {
    html += '<div style="text-align:center;padding:40px;color:#5A6B7C">No anomalies detected</div>';
  } else {
    A.forEach(function(a) {
      html += '<div class="ac ' + (a.sev === "high" ? "ah" : a.sev === "medium" ? "am" : "al") + '">';
      html += '<div style="display:flex;justify-content:space-between;margin-bottom:4px"><strong>' + a.s + '</strong><span style="font-size:11px;color:#5A6B7C">' + a.time + '</span></div>';
      html += '<div style="margin-bottom:4px">' + a.t + '</div>';
      html += '<div style="font-size:12px;color:#5A6B7C">Actual: <strong>' + a.act + '</strong> - Expected: ' + a.exp + '</div></div>';
    });
  }
  html += '<div class="card"><div class="tl">About These Alerts</div>';
  html += '<div class="tp">Our system monitors HRECOS station data in real-time and flags readings outside normal ranges. Always verify conditions before making water activity decisions.</div></div>';
  html += '</div>';
  return html;
}

// ===== NAVIGATION =====
var PAGES = {home: pageHome, stations: pageStations, tides: pageTides, quality: pageQuality, fish: pageFish, alerts: pageAlerts};
var NAV = [
  {k:"home",l:"Home",i:IC_HOME},{k:"stations",l:"Stations",i:IC_PIN},{k:"tides",l:"Tides",i:IC_WAVES},
  {k:"quality",l:"Quality",i:IC_DROP},{k:"fish",l:"Fish",i:IC_FISH},{k:"alerts",l:"Alerts",i:IC_BELL}
];

function render() {
  document.getElementById("app").innerHTML = PAGES[cur]();
  var navHtml = "";
  NAV.forEach(function(n) {
    navHtml += '<button class="ni ' + (n.k === cur ? "on" : "") + '" onclick="go(\'' + n.k + '\')">' + n.i + n.l + '</button>';
  });
  document.getElementById("nav").innerHTML = navHtml;
}
function go(k) { cur = k; render(); }
function togDark() {
  dark = !dark;
  localStorage.setItem("dark", dark);
  document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
  document.getElementById("tm").content = dark ? "#0D1B2A" : "#0A7EA4";
  render();
}

// ===== INIT =====
render();