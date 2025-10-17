// TOPCIT Quest - Basic Interactivity for Prototype
(function(){
  const levelOrder = ["Novice","Coder","Debugger","System Architect","TOPCIT Master"];
  const progressBar = document.querySelector('[data-progress-bar]');
  const currentLevelEl = document.querySelector('[data-current-level]');
  const nextLevelEl = document.querySelector('[data-next-level]');
  const gainedXpEl = document.querySelector('[data-gained-xp]');
  const startStudyBtn = document.getElementById('start-study');
  const walletAmountEl = document.querySelector('[data-wallet-amount]');
  const redeemables = Array.from(document.querySelectorAll('[data-redeem]'));
  const toastContainer = document.getElementById('toast-container');
  const rings = Array.from(document.querySelectorAll('[data-ring]'));
  const xpTotalEl = document.querySelector('[data-xp-total]');
  const userMenuBtn = document.getElementById('user-menu-btn');
  const userDropdown = document.getElementById('user-dropdown');

  // Utility: show toast
  function showToast(message, type = 'success'){
    if(!toastContainer) return;
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.textContent = message;
    toastContainer.appendChild(t);
    setTimeout(()=>{ t.style.opacity = '0'; t.style.transform = 'translateY(6px)'; }, 2200);
    setTimeout(()=>{ t.remove(); }, 2600);
  }

  // Animate charts on load
  function revealCharts(){
    document.querySelectorAll('[data-chart-hours], [data-chart-accuracy]').forEach(chart => {
      // stagger for nicer appearance
      setTimeout(()=> chart.classList.add('revealed'), 150);
    });
  }

  // Animate topic rings
  function animateRings(){
    rings.forEach((c, i)=>{
      const r = 52; // matches SVG r
      const circumference = 2 * Math.PI * r;
      const target = Math.max(0, Math.min(100, parseInt(c.getAttribute('data-progress')||'0',10)));
      c.style.strokeDasharray = String(circumference);
      c.style.strokeDashoffset = String(circumference);
      setTimeout(()=>{
        const offset = circumference * (1 - target/100);
        c.style.strokeDashoffset = String(offset);
      }, 200 + i*100);
    });
  }

  // XP/Level progression simulation
  function parsePercent(){
    const style = progressBar?.getAttribute('style') || '';
    const m = style.match(/width:\s*(\d+)%/);
    return m ? parseInt(m[1],10) : 0;
  }
  function setPercent(p){
    if(progressBar){ progressBar.style.width = `${Math.max(0, Math.min(100, p))}%`; }
  }
  function getLevelIndex(){
    const txt = (currentLevelEl?.textContent || '').trim();
    return Math.max(0, levelOrder.indexOf(txt));
  }
  function setLevel(idx){
    if(currentLevelEl){ currentLevelEl.textContent = levelOrder[idx]; }
    if(nextLevelEl){ nextLevelEl.textContent = levelOrder[Math.min(levelOrder.length-1, idx+1)]; }
  }

  function addXp(amount){
    const inc = Math.max(10, Math.min(200, amount));
    const start = parsePercent();
    let target = start + Math.floor(inc/2); // map XP to percent loosely
    let levelIdx = getLevelIndex();
    if(target >= 100){
      levelIdx = Math.min(levelOrder.length-1, levelIdx + 1);
      target = target - 100;
      setLevel(levelIdx);
      showToast(`Level up! You are now ${levelOrder[levelIdx]}.`, 'success');
    }
    setPercent(target);
    if(gainedXpEl){ gainedXpEl.textContent = `+${inc}`; }
    // increment XP total counter visually
    if(xpTotalEl){
      const current = parseInt(xpTotalEl.textContent.replace(/,/g,''),10) || 0;
      const end = current + inc * 10; // loose mapping XP points
      animateNumber(xpTotalEl, current, end, 600);
    }
  }

  function animateNumber(el, from, to, duration){
    const start = performance.now();
    function tick(now){
      const p = Math.min(1, (now - start) / duration);
      const value = Math.round(from + (to - from) * p);
      el.textContent = value.toLocaleString();
      if(p < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  // Wallet / redeem
  function getWallet(){ return parseInt((walletAmountEl?.textContent || '0').replace(/,/g,''),10) || 0; }
  function setWallet(value){ if(walletAmountEl){ walletAmountEl.textContent = value.toLocaleString(); } }

  function handleRedeem(el){
    const cost = parseInt(el.getAttribute('data-cost') || '0', 10);
    const have = getWallet();
    if(have < cost){
      showToast('Not enough coins to redeem.', 'error');
      return;
    }
    setWallet(have - cost);
    el.classList.add('redeemed');
    const btn = el.querySelector('button');
    if(btn){ btn.disabled = true; btn.textContent = 'Redeemed'; }
    showToast('Item redeemed! Enjoy your reward.', 'success');
  }

  // Bind events
  // User menu toggle
  if(userMenuBtn && userDropdown){
    userMenuBtn.addEventListener('click', ()=>{
      const menuWrap = userMenuBtn.closest('.user-menu');
      if(menuWrap){ menuWrap.classList.toggle('open'); }
      const expanded = userMenuBtn.getAttribute('aria-expanded') === 'true';
      userMenuBtn.setAttribute('aria-expanded', expanded ? 'false' : 'true');
      userDropdown.setAttribute('aria-hidden', expanded ? 'true' : 'false');
    });
    window.addEventListener('click', (e)=>{
      if(!(e.target instanceof Element)) return;
      const wrap = userMenuBtn.closest('.user-menu');
      if(wrap && !wrap.contains(e.target)){
        wrap.classList.remove('open');
        userMenuBtn.setAttribute('aria-expanded','false');
        userDropdown.setAttribute('aria-hidden','true');
      }
    });
  }
  redeemables.forEach(el => {
    el.addEventListener('click', (e)=>{
      // only act on button or container click
      if(e.target instanceof HTMLElement && (e.target.tagName === 'BUTTON' || e.currentTarget === e.target.closest('[data-redeem]'))){
        handleRedeem(el);
      }
    });
  });

  // Initial
  window.addEventListener('load', revealCharts);
  window.addEventListener('load', animateRings);
})();


