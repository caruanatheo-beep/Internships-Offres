"use strict";
const $ = (id) => document.getElementById(id);
const controls = ["search", "category", "family", "period", "start", "sort"];
const normalize = (s) => String(s || "").normalize("NFKD").replace(/\p{M}/gu, "").toLowerCase().replace(/[^\p{L}\p{N}]+/gu, " ").trim();
let offers = [], page = 1;
const size = 50;
function safeLink(value) {
  try { const u = new URL(value); return u.protocol === "https:" && !u.username && !u.password ? u.href : null; }
  catch { return null; }
}
function render() {
  const terms = normalize($("search").value).split(/\s+/).filter(Boolean);
  const today = new Intl.DateTimeFormat("en-CA", {timeZone: "Europe/Paris", year: "numeric", month: "2-digit", day: "2-digit"}).format(new Date());
  const week = new Date(today + "T12:00:00Z"); week.setUTCDate(week.getUTCDate() - 6);
  const first = week.toISOString().slice(0,10);
  let selected = offers.filter((j) => terms.every((t) => normalize(j.title + " " + j.company + " " + j.location).includes(t))
    && (!$("category").value || j.categories.includes($("category").value))
    && (!$("family").value || j.family === $("family").value)
    && (!$("start").value || j.start_month && j.start_month >= $("start").value)
    && (!$("period").value || $("period").value === "daily" && j.published === today
      || $("period").value === "weekly" && j.published >= first && j.published <= today));
  if ($("sort").value === "recent") selected.sort((a,b) => b.published.localeCompare(a.published));
  const pages = Math.max(1, Math.ceil(selected.length / size)); page = Math.min(page, pages);
  const fragment = document.createDocumentFragment();
  for (const j of selected.slice((page-1)*size, page*size)) {
    const href = safeLink(j.url); if (!href) continue;
    const card = $("offer-template").content.firstElementChild.cloneNode(true); card.href = href;
    for (const [selector, value] of [[".company",j.company],["h3",j.title],[".kind",j.kind],[".location",j.location],[".start",j.start],[".family",j.family],[".date",j.date_label]]) {
      const node = card.querySelector(selector); node.textContent = value; node.title = value;
    }
    const img = card.querySelector("img"), initials = card.querySelector(".initials");
    initials.textContent = j.company.split(/\s+/).slice(0,2).map(s=>s[0] || "").join("").toUpperCase();
    img.hidden = true;
    if (/^logos\/[a-zA-Z0-9._-]+\.png$/.test(j.logo)) {
      img.loading = "eager";
      img.onload = () => { img.hidden = false; initials.hidden = true; };
      img.src = j.logo;
    }
    fragment.append(card);
  }
  $("offers").replaceChildren(fragment);
  $("count").textContent = selected.length ? `Offres ${(page-1)*size+1}–${Math.min(page*size,selected.length)} sur ${selected.length}` : "Aucune offre pour ces critères";
  $("page").textContent = `Page ${page} / ${pages}`;
  $("previous").disabled = page <= 1; $("next").disabled = page >= pages;
}
function options(id, pairs) {
  $(id).replaceChildren($(id).options[0]);
  for (const [value,label] of pairs) { const o = document.createElement("option"); o.value = value; o.textContent = label; $(id).append(o); }
}
async function load() {
  $("reload").disabled = true;
  try {
    const response = await fetch("offers.json", {cache: "no-cache", credentials: "omit"});
    if (!response.ok) throw new Error("load");
    const data = await response.json();
    if (!Array.isArray(data.offers)) throw new Error("schema");
    offers = data.offers;
    const family = $("family").value, start = $("start").value;
    options("family", [...new Set(offers.map(j=>j.family).filter(Boolean))].sort().map(v=>[v,v]));
    const months = new Set(offers.map(j=>j.start_month).filter(Boolean));
    const now = new Date();
    for (let n=0;n<24;n++) months.add(new Date(Date.UTC(now.getFullYear(),now.getMonth()+n,1)).toISOString().slice(0,7));
    options("start", [...months].sort().map(v=>[v,new Intl.DateTimeFormat("fr-FR",{month:"long",year:"numeric",timeZone:"UTC"}).format(new Date(v+"-01T12:00:00Z"))]));
    $("family").value = family; $("start").value = start;
    if ($("family").selectedIndex < 0) $("family").selectedIndex = 0;
    if ($("start").selectedIndex < 0) $("start").selectedIndex = 0;
    $("updated").textContent = "Mis à jour le " + new Intl.DateTimeFormat("fr-FR", {dateStyle:"short",timeStyle:"short",timeZone:"Europe/Paris"}).format(new Date(data.updated)) + " · Paris";
    const s = data.sources;
    $("sources").textContent = s.checked ? `${s.checked} sources vérifiées · ${s.unavailable} indisponibles · ${s.retained} avec offres conservées` : "";
    $("message").textContent = ""; render();
  } catch { $("message").textContent = "Impossible de charger les nouvelles données. Réessaie dans un instant. Les offres déjà affichées sont conservées."; }
  finally { $("reload").disabled = false; }
}
for (const id of controls) $(id).addEventListener(id === "search" ? "input" : "change", () => {page=1;render();});
$("reload").addEventListener("click", load);
$("previous").addEventListener("click",()=>{page--;render();$("count").scrollIntoView({block:"start"});});
$("next").addEventListener("click",()=>{page++;render();$("count").scrollIntoView({block:"start"});});
load();
