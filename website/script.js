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
  const WALLET_KEY = 'topcit_wallet_amount';
  // Add persistent storage for completed courses
  const COMPLETED_KEY = 'topcit_completed_courses';
  function getCompletedCourses(){
    try{ const arr = JSON.parse(localStorage.getItem(COMPLETED_KEY) || '[]'); return Array.isArray(arr) ? arr : []; }catch(_){ return []; }
  }
  function isCourseCompleted(id){
    return getCompletedCourses().includes(String(id || '').toLowerCase());
  }
  function addCompletedCourse(id){
    const key = String(id || '').toLowerCase();
    const arr = getCompletedCourses();
    if(!arr.includes(key)){
      arr.push(key);
      try{ localStorage.setItem(COMPLETED_KEY, JSON.stringify(arr)); }catch(_){}
    }
  }
  const ONGOING_KEY = 'topcit_ongoing_courses';
  function getOngoingCourses(){
    try{ const arr = JSON.parse(localStorage.getItem(ONGOING_KEY) || '[]'); return Array.isArray(arr) ? arr : []; }catch(_){ return []; }
  }
  function addOngoingCourse(id){
    const key = String(id || '').toLowerCase();
    const arr = getOngoingCourses();
    if(!arr.includes(key)){
      arr.push(key);
      try{ localStorage.setItem(ONGOING_KEY, JSON.stringify(arr)); }catch(_){}
    }
  }
  function removeOngoingCourse(id){
    const key = String(id || '').toLowerCase();
    const arr = getOngoingCourses().filter(x => x !== key);
    try{ localStorage.setItem(ONGOING_KEY, JSON.stringify(arr)); }catch(_){}
  }
  // Dashboard & Learn shared rewards info for linking
  const COURSE_REWARDS = {
    requirements: { xp: 80, coins: 120, title: 'Requirements Engineering' },
    design: { xp: 90, coins: 140, title: 'Software Design & Architecture' },
    programming: { xp: 60, coins: 100, title: 'Programming Fundamentals' },
    databases: { xp: 70, coins: 110, title: 'Database Modeling' },
    networks: { xp: 60, coins: 100, title: 'Networking Fundamentals' },
    os: { xp: 80, coins: 120, title: 'Operating Systems' },
    algorithms: { xp: 100, coins: 160, title: 'Algorithms & Data Structures' },
    security: { xp: 90, coins: 140, title: 'Cybersecurity Essentials' },
    cloud: { xp: 70, coins: 110, title: 'Cloud Computing Basics' }
  };
  function getAllCourseIds(){ return Object.keys(COURSE_REWARDS); }
  function getCourseTitle(id){ return (COURSE_REWARDS[id]?.title) || id; }
  function getCourseRewards(id){ return COURSE_REWARDS[id] || { xp: 0, coins: 0, title: id }; }
  function getCourseUrl(id, status){
    const r = getCourseRewards(id);
    const xp = status === 'completed' ? 0 : r.xp;
    const coins = status === 'completed' ? 0 : r.coins;
    // Use href so URLs stay repo-relative on GitHub Pages (e.g., /repo/course.html)
    const url = new URL('course.html', location.href);
    url.searchParams.set('course', id);
    url.searchParams.set('xp', String(xp));
    url.searchParams.set('coins', String(coins));
    return url.toString();
  }
  function getWallet(){ return parseInt((walletAmountEl?.textContent || '0').replace(/,/g,''),10) || 0; }
  function setWallet(value){
    const safe = Math.max(0, parseInt(value,10) || 0);
    if(walletAmountEl){ walletAmountEl.textContent = safe.toLocaleString(); }
    try{ localStorage.setItem(WALLET_KEY, String(safe)); }catch(_){}
  }
  function loadWallet(){
    const domDefault = parseInt((walletAmountEl?.textContent || '0').replace(/,/g,''),10) || 0;
    const raw = localStorage.getItem(WALLET_KEY);
    const stored = raw ? parseInt(raw,10) : NaN;
    const value = Number.isFinite(stored) ? stored : domDefault;
    if(!Number.isFinite(stored)){
      try{ localStorage.setItem(WALLET_KEY, String(domDefault)); }catch(_){}
    }
    setWallet(value);
  }
  window.addEventListener('storage', (e)=>{
    if(e.key === WALLET_KEY){
      const next = parseInt(e.newValue || '0',10) || 0;
      setWallet(next);
      filterAffordableStoreItems();
      limitDashboardStoreItems();
    }
    if(e.key === COMPLETED_KEY || e.key === ONGOING_KEY){
      // Refresh Dashboard materials, Topics section, and Learn completed grid when progress changes in another tab
      setupDashboardMaterials();
      setupTopicsSection();
      populateCompletedGrid();
    }
  });

  // Filter store items on dashboard by affordability (show only affordable items)
  function filterAffordableStoreItems(){
    const have = getWallet();
    redeemables.forEach(el=>{
      const inDashboardStore = !!el.closest('.store-items');
      if(!inDashboardStore) return; // Rewards page remains unaffected
      const cost = parseInt(el.getAttribute('data-cost') || '0', 10);
      const btn = el.querySelector('button');
      const affordable = have >= cost;
      el.classList.toggle('locked', !affordable);
      if(btn) btn.disabled = !affordable;
      el.style.display = affordable ? '' : 'none';
    });
  }

  // Limit dashboard store to showing only the first 5 visible (affordable) items
  // Accepts either a number (desired max) or an event object.
  function limitDashboardStoreItems(arg){
    const maxCount = (typeof arg === 'number' && Number.isFinite(arg)) ? arg : 5;
    const container = document.querySelector('.store-items');
    if(!container) return;
    const items = Array.from(container.querySelectorAll('.store-item'));
    let shown = 0;
    items.forEach(item=>{
      // Skip items hidden by affordability filter
      if(item.style.display === 'none') return;
      if(shown < maxCount){
        item.style.display = '';
        shown++;
      }else{
        item.style.display = 'none';
      }
    });
  }

  function handleRedeem(el){
    const cost = parseInt(el.getAttribute('data-cost') || '0', 10);
    const have = getWallet();
    if(have < cost){
      showToast('Not enough coins to redeem.', 'error');
      return;
    }
    setWallet(have - cost);
    // Re-filter store items after wallet changes
    filterAffordableStoreItems();
    limitDashboardStoreItems();
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

  // Learn page: navigate to dedicated course page with metadata
  function setupLearnCourses(){
    const onLearnPage = !!document.querySelector('main .card .learn-grid, [data-completed-grid]');
    if(!onLearnPage) return; // Only run on Learn page
  
    // Populate the Completed tab first so we can bind events on clones too
    populateCompletedGrid();
  
    const grids = Array.from(document.querySelectorAll('.learn-grid'));
    grids.forEach(grid => {
      const items = Array.from(grid.querySelectorAll('.learn-item'));
      items.forEach(item => {
        const id = item.getAttribute('data-course-id') || '';
        // Mark completed visually and add a chip
        if(isCourseCompleted(id)){
          item.classList.add('completed');
          const meta = item.querySelector('.meta');
          if(meta && !meta.querySelector('.chip.green')){
            const doneChip = document.createElement('span');
            doneChip.className = 'chip green';
            doneChip.textContent = 'Completed';
            meta.appendChild(doneChip);
          }
        }
        const startBtn = item.querySelector('[data-course-start]');
        if(!startBtn) return;
        // Prevent double-binding
        if(startBtn.dataset.bound) return;
        startBtn.dataset.bound = '1';
        startBtn.addEventListener('click', ()=>{
          if(isCourseCompleted(id)){
            showToast('Course already completed', 'error');
            return;
          }
          const xp = parseInt(startBtn.getAttribute('data-xp') || '0', 10) || 0;
          const coins = parseInt(startBtn.getAttribute('data-coins') || '0', 10) || 0;
          const url = new URL('course.html', location.origin);
          url.searchParams.set('course', id);
          url.searchParams.set('xp', String(xp));
          url.searchParams.set('coins', String(coins));
          location.assign(url.toString());
        });
      });
    });
  }

  // Build the Completed Courses tab by cloning items from the All grid
  function populateCompletedGrid(){
    const container = document.querySelector('[data-completed-grid]');
    const sourceGrid = document.querySelector('[data-all-grid]') || document.querySelector('.learn-grid');
    if(!container || !sourceGrid) return;
    container.innerHTML = '';
    const ids = getCompletedCourses();
    if(ids.length === 0){
      const p = document.createElement('p');
      p.className = 'muted';
      p.textContent = 'No completed courses yet.';
      container.appendChild(p);
      return;
    }
    ids.forEach(id => {
      const src = sourceGrid.querySelector(`.learn-item[data-course-id="${id}"]`);
      if(!src) return;
      const clone = src.cloneNode(true);
      clone.classList.add('completed');
      // Ensure the completed chip exists
      const meta = clone.querySelector('.meta');
      if(meta && !meta.querySelector('.chip.green')){
        const doneChip = document.createElement('span');
        doneChip.className = 'chip green';
        doneChip.textContent = 'Completed';
        meta.appendChild(doneChip);
      }
      // Adjust actions: Start -> Review and remove Finish
      const actions = clone.querySelector('.course-actions');
      if(actions){
        const startBtn = actions.querySelector('[data-course-start]');
        if(startBtn){
          startBtn.textContent = 'Review';
          startBtn.classList.remove('primary');
          startBtn.classList.add('ghost');
          startBtn.removeAttribute('data-xp');
          startBtn.removeAttribute('data-coins');
          startBtn.dataset.bound = '1';
          startBtn.addEventListener('click', ()=>{
            const url = new URL('course.html', location.origin);
            url.searchParams.set('course', id);
            url.searchParams.set('xp', '0');
            url.searchParams.set('coins', '0');
            location.assign(url.toString());
          });
        }
        const finishBtn = actions.querySelector('[data-course-finish]');
        if(finishBtn) finishBtn.remove();
      }
      container.appendChild(clone);
    });
  }

  // Sub-tabs toggling between All and Completed
  function setupLearnTabs(){
    const tabsWrap = document.querySelector('[data-sub-tabs]');
    if(!tabsWrap) return;
    const allGrid = document.querySelector('[data-all-grid]') || document.querySelector('.learn-grid');
    const completedGrid = document.querySelector('[data-completed-grid]');
    const tabs = Array.from(tabsWrap.querySelectorAll('.sub-tab'));
    function activate(name){
      tabs.forEach(btn => btn.classList.toggle('active', (btn.getAttribute('data-tab')||'all') === name));
      if(allGrid) allGrid.style.display = name === 'all' ? '' : 'none';
      if(completedGrid) completedGrid.style.display = name === 'completed' ? '' : 'none';
    }
    tabs.forEach(btn => {
      btn.addEventListener('click', ()=> activate(btn.getAttribute('data-tab') || 'all'));
    });
    activate('all');
  }

  // Dashboard materials sync
  function setupDashboardMaterials(){
    const card = document.querySelector('.materials-card');
    if(!card) return; // Only on Dashboard
    const container = card.querySelector('.materials');
    if(!container) return;

    // Build groups from stored progress
    const completed = getCompletedCourses();
    const ongoingRaw = getOngoingCourses();
    const ongoing = ongoingRaw.filter(id => !completed.includes(id));
    const available = getAllCourseIds().filter(id => !completed.includes(id) && !ongoing.includes(id));

    container.innerHTML = '';

    function buildGroup(title, ids, status){
      const group = document.createElement('div');
      group.className = 'materials-group';
      const titleEl = document.createElement('div');
      titleEl.className = 'group-title';
      titleEl.textContent = title;
      const ul = document.createElement('ul');
      ul.className = 'materials-list';
      if(ids.length === 0){
        const li = document.createElement('li');
        li.className = 'muted';
        li.textContent = 'None';
        ul.appendChild(li);
      }else{
        ids.forEach(id => {
          const li = document.createElement('li');
          const icon = document.createElement('span');
          icon.className = 'icon ms';
          icon.textContent = status === 'completed' ? 'check_circle' : status === 'ongoing' ? 'schedule' : 'menu_book';
          const a = document.createElement('a');
          a.href = getCourseUrl(id, status);
          a.textContent = getCourseTitle(id);
          const meta = document.createElement('span');
          meta.className = 'meta';
          if(status === 'completed'){
            meta.textContent = 'Completed';
          }else if(status === 'ongoing'){
            meta.textContent = 'In progress';
          }else{
            const r = getCourseRewards(id);
            meta.textContent = `XP ${r.xp} • Coins ${r.coins}`;
          }
          li.appendChild(icon);
          li.appendChild(a);
          li.appendChild(meta);
          ul.appendChild(li);
        });
      }
      group.appendChild(titleEl);
      group.appendChild(ul);
      container.appendChild(group);
    }

    buildGroup('Completed Courses', completed, 'completed');
    buildGroup('Ongoing Courses', ongoing, 'ongoing');
    buildGroup('Available Courses', available, 'available');
  }

  // Topics section sync
  function setupTopicsSection(){
    const card = document.querySelector('.topics-card');
    if(!card) return; // Only on Dashboard
    const items = Array.from(card.querySelectorAll('[data-topic]'));
    const completed = getCompletedCourses();
    const ongoingList = getOngoingCourses();

    items.forEach(topic => {
      const titleEl = topic.querySelector('.topic-title');
      const titleText = (titleEl?.textContent || '').toLowerCase();
      let id = '';
      if(titleText.includes('programming')) id = 'programming';
      else if(titleText.includes('databases')) id = 'databases';
      else if(titleText.includes('software design')) id = 'design';
      else if(titleText.includes('it business')) id = 'business';

      const btn = topic.querySelector('.topic-actions .btn');
      const ring = topic.querySelector('[data-ring]');
      const ringLabel = topic.querySelector('.ring-label');

      if(!id){
        if(btn && !btn.dataset.bound){
          btn.dataset.bound = '1';
          btn.addEventListener('click', ()=> location.assign('learn.html'));
        }
        return;
      }

      const isDone = completed.includes(id);
      const isDoing = ongoingList.includes(id) && !isDone;

      if(btn){
        btn.textContent = isDone ? 'Review' : (isDoing ? 'Continue' : 'Start');
        if(!btn.dataset.bound){
          btn.dataset.bound = '1';
          btn.addEventListener('click', ()=>{
            const status = isDone ? 'completed' : (isDoing ? 'ongoing' : 'available');
            location.assign(getCourseUrl(id, status));
          });
        }
      }

      if(ring){
        const r = 52;
        const circumference = 2 * Math.PI * r;
        let target = parseInt(ring.getAttribute('data-progress') || '0', 10) || 0;
        if(isDone) target = 100;
        else if(isDoing) target = Math.max(target, 50);
        ring.setAttribute('data-progress', String(target));
        ring.style.strokeDasharray = String(circumference);
        ring.style.strokeDashoffset = String(circumference * (1 - target/100));
        if(ringLabel) ringLabel.textContent = `${target}%`;
      }
    });
  }

  // Course page: gating tasks and rewards
  function setupCoursePage(){
    const container = document.getElementById('course-page');
    if(!container) return; // Only run on course page
    const params = new URLSearchParams(location.search);
    const id = (params.get('course') || '').toLowerCase();
    const xp = parseInt(params.get('xp') || '0',10) || 0;
    const coins = parseInt(params.get('coins') || '0',10) || 0;
  
    // Track ongoing status when visiting course page
    if(id && !isCourseCompleted(id)){
      addOngoingCourse(id);
    }
  
    const COURSE_META = {
      requirements: { title: 'Requirements Engineering',
        quiz: { question: 'Which is a non-functional requirement?', options: ['Login feature', 'System performance', 'Checkout flow'], correctIndex: 1 },
        bullets: ['Functional vs non-functional', 'User stories & acceptance criteria', 'Validation & traceability'],
        reflection: 'Describe one non-functional requirement (e.g., performance or security).'
      },
      design: { title: 'Software Design & Architecture',
        quiz: { question: 'Which principle reduces coupling?', options: ['Global variables', 'SOLID', 'Hard-coded dependencies'], correctIndex: 1 },
        bullets: ['SOLID principles', 'Layered vs microservices', 'Trade-offs & patterns'],
        reflection: 'Name a design pattern and a case where you’d use it.'
      },
      programming: { title: 'Programming Fundamentals',
        quiz: { question: 'Which structure is LIFO?', options: ['Queue', 'Stack', 'Array'], correctIndex: 1 },
        bullets: ['Data types & control flow', 'Functions & collections', 'Debugging basics'],
        reflection: 'Write a short plan to solve a simple problem.'
      },
      databases: { title: 'Database Modeling',
        quiz: { question: 'Which creates a relationship?', options: ['Index', 'Foreign key', 'View'], correctIndex: 1 },
        bullets: ['ER modeling', 'Normalization basics', 'SQL joins'],
        reflection: 'Sketch a simple ER: Users—Orders (1..*) description.'
      },
      networks: { title: 'Networking Fundamentals',
        quiz: { question: 'DNS is used for?', options: ['Encrypt traffic', 'Name resolution', 'Routing'], correctIndex: 1 },
        bullets: ['OSI vs TCP/IP', 'HTTP/TLS/DNS', 'Routing basics'],
        reflection: 'Explain how a browser finds a host from a URL.'
      },
      os: { title: 'Operating Systems',
        quiz: { question: 'Which schedules CPU time?', options: ['Filesystem', 'Scheduler', 'Pager'], correctIndex: 1 },
        bullets: ['Processes vs threads', 'Memory & paging', 'Filesystem'],
        reflection: 'Describe a race condition and how to avoid it.'
      },
      algorithms: { title: 'Algorithms & Data Structures',
        quiz: { question: 'Average complexity of binary search?', options: ['O(n)', 'O(log n)', 'O(1)'], correctIndex: 1 },
        bullets: ['Complexity overview', 'Sorting/searching', 'Traversal strategies'],
        reflection: 'Pick a structure (tree/graph) and a use case.'
      },
      security: { title: 'Cybersecurity Essentials',
        quiz: { question: 'Password hashing is for:', options: ['Encrypt at rest', 'Store safely', 'Compress data'], correctIndex: 1 },
        bullets: ['OWASP Top 10', 'AuthN/AuthZ', 'Encryption & hashing'],
        reflection: 'List two secure coding practices.'
      },
      cloud: { title: 'Cloud Computing Basics',
        quiz: { question: 'SaaS means:', options: ['Hosted software', 'Virtual machines', 'Object storage'], correctIndex: 0 },
        bullets: ['IaaS/PaaS/SaaS', 'Provisioning & scaling', 'Shared responsibility'],
        reflection: 'Explain the shared responsibility model briefly.'
      }
    };
    const meta = COURSE_META[id] || { title: 'Course', quiz: { question: 'Quick check:', options: ['A','B','C'], correctIndex: 0 }, bullets: ['Read the material'], reflection: 'Write a brief reflection.' };
  
    // Fill header
    const titleEl = container.querySelector('[data-course-title]');
    const xpEl = container.querySelector('[data-course-xp]');
    const coinsEl = container.querySelector('[data-course-coins]');
    if(titleEl) titleEl.textContent = meta.title;
    if(xpEl) xpEl.textContent = `XP ${xp}`;
    if(coinsEl) coinsEl.textContent = `Coins ${coins}`;
  
    // Build tasks content
    const bulletsEl = container.querySelector('[data-task-read-list]');
    if(bulletsEl){ bulletsEl.innerHTML = meta.bullets.map(b=>`<li>${b}</li>`).join(''); }
    const quizQEl = container.querySelector('[data-quiz-question]');
    const quizOptsEl = container.querySelector('[data-quiz-options]');
    if(quizQEl) quizQEl.textContent = meta.quiz.question;
    if(quizOptsEl){
      quizOptsEl.innerHTML = meta.quiz.options.map((opt, i)=>`<label><input type="radio" name="quiz" value="${i}"> ${opt}</label>`).join('');
    }
    const reflectInput = container.querySelector('[data-reflection-input]');
    if(reflectInput && meta.reflection){ reflectInput.setAttribute('placeholder', meta.reflection); }
  
    // State & gating
    let readDone = false, quizDone = false, reflectDone = false;
    const finishBtn = container.querySelector('[data-course-finish]');
  const readBtn = container.querySelector('[data-mark-read]');
  const completionView = container.querySelector('[data-completion]');
  function updateFinish(){
    if(!finishBtn) return;
    const disabled = !(readDone && quizDone && reflectDone);
    // Reflect real disabled state; only enable when all tasks complete
    finishBtn.setAttribute('aria-disabled', disabled ? 'true' : 'false');
    finishBtn.classList.toggle('is-disabled', disabled);
    finishBtn.toggleAttribute('disabled', disabled);
  }
  function indicateMissing(){
    const tasks = [];
    if(!readDone){ tasks.push(container.querySelector('.task:nth-of-type(1)')); }
    if(!quizDone){ tasks.push(container.querySelector('.task:nth-of-type(2)')); }
    if(!reflectDone){ tasks.push(container.querySelector('.task:nth-of-type(3)')); }
    tasks.forEach(t=>{ if(t){ t.classList.add('needs-action'); setTimeout(()=>t.classList.remove('needs-action'), 900); } });
    const missing = [!readDone && 'Read', !quizDone && 'Quiz', !reflectDone && 'Reflection'].filter(Boolean).join(', ');
    showToast(`Please complete: ${missing}.`, 'error');
    const first = tasks.find(Boolean);
    if(first){ first.scrollIntoView({behavior:'smooth', block:'center'}); }
  }
  if(readBtn){ readBtn.addEventListener('click', ()=>{ readDone = true; container.querySelector('[data-read-status]').textContent = 'Marked as read ✓'; readBtn.disabled = true; updateFinish(); }); }
  if(quizOptsEl){ quizOptsEl.addEventListener('change', (e)=>{ const sel = container.querySelector('input[name="quiz"]:checked'); quizDone = !!sel && parseInt(sel.value,10) === meta.quiz.correctIndex; updateFinish(); }); }
  if(reflectInput){ reflectInput.addEventListener('input', ()=>{ reflectDone = (reflectInput.value.trim().length >= 20); updateFinish(); }); }
  updateFinish();
  
  if(finishBtn){
    finishBtn.addEventListener('click', ()=>{
      if(!(readDone && quizDone && reflectDone)){
        indicateMissing();
        return;
      }
      addXp(xp);
      setWallet(getWallet() + coins);
      // Record course completion for Learn page
      addCompletedCourse(id);
      removeOngoingCourse(id);
      if(completionView){
        completionView.style.display = '';
        container.querySelector('[data-course-body]').style.display = 'none';
        const sumEl = container.querySelector('[data-completion-summary]');
        if(sumEl) sumEl.textContent = `+${xp} XP • +${coins} coins`;
      }
      showToast('Course completed!', 'success');
    });
  }
  }




// Profile modal persistence and UI
const PROFILE_KEY = 'topcit_user_profile';
function readProfile(){
  try{ const raw = localStorage.getItem(PROFILE_KEY); return raw ? JSON.parse(raw) : {}; }catch(_){ return {}; }
}
function writeProfile(p){
  try{ localStorage.setItem(PROFILE_KEY, JSON.stringify(p||{})); }catch(_){}
}
function applyHeaderAvatar(profile){
  const btn = document.getElementById('user-menu-btn');
  const avatarEl = btn ? btn.querySelector('.avatar') : null;
  if(!avatarEl) return;
  const hasImg = !!profile?.avatar;
  if(hasImg){
    const img = document.createElement('img');
    img.alt = 'Profile avatar';
    img.src = profile.avatar;
    img.style.width = '100%';
    img.style.height = '100%';
    img.style.objectFit = 'cover';
    avatarEl.textContent = '';
    avatarEl.innerHTML = '';
    avatarEl.appendChild(img);
  }
}
function buildProfileModal(){
  if(document.getElementById('profile-modal')) return; // already built
  const backdrop = document.createElement('div');
  backdrop.className = 'profile-modal-backdrop';
  backdrop.id = 'profile-backdrop';
  const modal = document.createElement('div');
  modal.className = 'profile-modal';
  modal.id = 'profile-modal';
  modal.innerHTML = `
    <div class="head">
      <h3>Profile</h3>
      <button class="icon-btn" id="profile-close" aria-label="Close"><span class="ms">close</span></button>
    </div>
    <div class="body">
      <form class="profile-form" id="profile-form">
        <div class="field span-2 avatar-preview">
          <div class="pic" id="profile-avatar-preview"><span class="ms">account_circle</span></div>
          <div>
            <label for="profile-avatar">Profile Picture</label>
            <input type="file" id="profile-avatar" accept="image/*">
            <small class="muted">Stored locally; persists in this browser.</small>
          </div>
        </div>
        <div class="field">
          <label for="profile-name">Name</label>
          <input type="text" id="profile-name" placeholder="Your name">
        </div>
        <div class="field">
          <label for="profile-email">Email</label>
          <input type="email" id="profile-email" placeholder="name@example.com">
        </div>
        <div class="field span-2">
          <label for="profile-phone">Phone Number</label>
          <input type="tel" id="profile-phone" placeholder="e.g. +63 912 345 6789">
        </div>
      </form>
      <div class="profile-stats">
        <div class="profile-stat"><div class="label">Wallet</div><div class="value" id="profile-wallet">0</div></div>
        <div class="profile-stat"><div class="label">XP Total</div><div class="value" id="profile-xp">0</div></div>
        <div class="profile-stat"><div class="label">Completed</div><div class="value" id="profile-completed-count">0</div></div>
      </div>
      <div class="completed-topics">
        <h4>Completed Topics</h4>
        <ul id="profile-completed-list"></ul>
      </div>
    </div>
    <div class="footer">
      <button class="btn ghost" id="profile-cancel">Cancel</button>
      <button class="btn primary" id="profile-save">Save Changes</button>
    </div>
  `;
  document.body.appendChild(backdrop);
  document.body.appendChild(modal);
  // Bind close/backdrop
  function close(){ backdrop.classList.remove('open'); modal.classList.remove('open'); }
  backdrop.addEventListener('click', close);
  modal.querySelector('#profile-close')?.addEventListener('click', close);
  modal.querySelector('#profile-cancel')?.addEventListener('click', (e)=>{ e.preventDefault(); close(); });
  // File input preview
  const fileInput = modal.querySelector('#profile-avatar');
  const preview = modal.querySelector('#profile-avatar-preview');
  fileInput?.addEventListener('change', ()=>{
    const f = fileInput.files?.[0];
    if(!f) return;
    const reader = new FileReader();
    reader.onload = ()=>{
      const url = String(reader.result||'');
      preview.innerHTML = `<img alt="avatar" src="${url}">`;
      const p = readProfile();
      p.avatar = url;
      writeProfile(p);
      applyHeaderAvatar(p);
    };
    reader.readAsDataURL(f);
  });
}
function openProfileModal(){
  buildProfileModal();
  const backdrop = document.getElementById('profile-backdrop');
  const modal = document.getElementById('profile-modal');
  if(!backdrop || !modal) return;
  // Populate fields
  const p = readProfile();
  const nameEl = modal.querySelector('#profile-name');
  const emailEl = modal.querySelector('#profile-email');
  const phoneEl = modal.querySelector('#profile-phone');
  const preview = modal.querySelector('#profile-avatar-preview');
  if(nameEl) nameEl.value = p.name || '';
  if(emailEl) emailEl.value = p.email || '';
  if(phoneEl) phoneEl.value = p.phone || '';
  preview.innerHTML = p.avatar ? `<img alt="avatar" src="${p.avatar}">` : '<span class="ms">account_circle</span>';
  // Stats
  const walletEl = modal.querySelector('#profile-wallet');
  const xpEl = modal.querySelector('#profile-xp');
  const countEl = modal.querySelector('#profile-completed-count');
  const listEl = modal.querySelector('#profile-completed-list');
  const completed = getCompletedCourses();
  if(walletEl) walletEl.textContent = String(getWallet().toLocaleString());
  const xpDom = document.querySelector('[data-xp-total]');
  const xpVal = xpDom ? parseInt(xpDom.textContent.replace(/,/g,''),10)||0 : 0;
  if(xpEl) xpEl.textContent = xpVal.toLocaleString();
  if(countEl) countEl.textContent = String(completed.length);
  if(listEl){
    listEl.innerHTML = completed.map(id=>`<li>${getCourseTitle(id)}</li>`).join('');
  }
  // Save changes
  modal.querySelector('#profile-save')?.addEventListener('click', (e)=>{
    e.preventDefault();
    const next = { name: nameEl?.value||'', email: emailEl?.value||'', phone: phoneEl?.value||'', avatar: readProfile().avatar };
    writeProfile(next);
    showToast('Profile saved.', 'success');
    // reflect name under XP card if present
    const whoName = document.querySelector('.xp-stats .who .name');
    if(whoName && next.name) whoName.textContent = next.name;
    openProfileModal.close?.();
    const backdrop = document.getElementById('profile-backdrop');
    const modal = document.getElementById('profile-modal');
    if(backdrop && modal){ backdrop.classList.remove('open'); modal.classList.remove('open'); }
  });
  backdrop.classList.add('open');
  modal.classList.add('open');
}
function setupProfileModal(){
  buildProfileModal();
  applyHeaderAvatar(readProfile());
  // Bind Profile trigger from user menu
  const dropdown = document.getElementById('user-dropdown');
  if(dropdown){
    const items = Array.from(dropdown.querySelectorAll('.menu-item'));
    const profileBtn = items.find(b => (b.textContent||'').toLowerCase().includes('profile'));
    profileBtn?.addEventListener('click', openProfileModal);
  }
}
window.addEventListener('load', setupProfileModal);
window.addEventListener('load', setupCoursePage);
window.addEventListener('load', revealCharts);
window.addEventListener('load', animateRings);
window.addEventListener('load', filterAffordableStoreItems);
window.addEventListener('load', () => limitDashboardStoreItems());
window.addEventListener('load', setupLearnCourses);
window.addEventListener('load', setupLearnTabs);
window.addEventListener('load', setupDashboardMaterials);
window.addEventListener('load', setupTopicsSection);
})();


