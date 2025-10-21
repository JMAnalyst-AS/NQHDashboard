// Q1 — Breach / Leak Intelligence (incidents only)
const breaches = Array.isArray(data.breaches) ? data.breaches : [];
if (breaches.length === 0) {
  el('#breaches').innerHTML = '<div class="card">No recent breach/leak headlines yet. Will retry on the next update.</div>';
} else {
  mountList(el('#breaches'), breaches, b =>
    `<div class="title-line">
       <b class="org">${b.org || 'Unknown org'}</b>
     </div>
     <div class="small clamp-2" title="${(b.title || '').replace(/"/g,'&quot;')}">
       ${b.title || ''}
     </div>
     <div class="small dim">${b.source || ''} • ${b.published || ''}</div>`
  );
}
// Q3 – Security News (RSS)
const rss = Array.isArray(data.segment1) ? data.segment1 : [];
if (rss.length === 0) {
  el('#rss-feed').innerHTML = '<div class="card">No recent security news.</div>';
} else {
  mountList(el('#rss-feed'), rss, r => `
    <div class="title-line">
      <a href="${r.url}" target="_blank" class="org">${r.title || 'Untitled'}</a>
    </div>
    <div class="small dim">${r.source || ''} • ${r.published || ''}</div>
  `);
}

