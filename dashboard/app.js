// OSINT TV (Quadrants) — data fetch & render only
const REFRESH_MS = 5 * 60 * 1000;

function el(q){ return document.querySelector(q); }
function mountList(container, arr, map){
  container.innerHTML = '';
  (arr || []).slice(0, 10).forEach(x => {
    const d = document.createElement('div');
    d.className = 'card item';
    d.innerHTML = map(x);
    container.appendChild(d);
  });
}

async function fetchData(){
  try{
    const res = await fetch('./data.json?x=' + Date.now(), { cache:'no-store' });
    if(res.ok){
      const data = await res.json();
      render(data);
    }
  }catch(e){
    console.error('[fetchData]', e);
  }
}

function render(data){
  // Q1 — Breaches
  const breaches = Array.isArray(data.breaches) ? data.breaches : [];
  if (breaches.length === 0) {
    el('#breaches').innerHTML = '<div class="card">No recent breach/leak headlines yet. Will retry on the next update.</div>';  
  } else {
    mountList(el('#breaches'), breaches, b =>
      `<b>${b.org || b.title}</b>
       <div class="small">${b.source || ''} • ${b.published || ''}</div>`
    );
  }

  // Q3 — RSS
  mountList(el('#rss'), data.rss, r =>
    `<b>${r.title || 'Item'}</b>
     <div class="small">${r.source || ''} • ${r.published || ''}</div>`
  );

  // Q4 — Summary
  el('#summary').innerHTML = data.summary || 'No summary yet.';

  // Header timestamp
  el('#timestamp').textContent = `Updated ${new Date(data.generated_at || Date.now()).toLocaleString()}`;
}

// Initial load + periodic refresh
fetchData();
setInterval(fetchData, REFRESH_MS);
