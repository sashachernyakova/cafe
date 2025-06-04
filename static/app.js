
// Утилита для показа «тоста» — всплывающего уведомления, которое само исчезает
function showToast(text, duration = 3000) {
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = text;
  document.body.appendChild(toast); // добавляем в DOM
  // небольшая задержка, чтобы сработал transition
  requestAnimationFrame(() => toast.classList.add('show'));
  // удаляем через duration
  setTimeout(() => {
    toast.classList.remove('show');
     // когда CSS-переход завершится (opacity:1→0), удаляем элемент из DOM
    toast.addEventListener('transitionend', () => toast.remove());
  }, duration);
}

// Ждём полной загрузки DOM, прежде чем обращаться к элементам страницы
document.addEventListener('DOMContentLoaded', () => {
  // ===== 0) Инициализация Telegram WebApp + USER_ID 
  const tg = window.Telegram.WebApp; // SDK Telegram встраивается через <script>
  tg.expand(); // разворачиваем WebApp на весь экран
  const USER_ID = tg.initDataUnsafe.user.id; // получаем ID текущего пользователя
  const CHAT_ID = tg.initDataUnsafe.user.id;

  // Вставляем инструкцию в секцию «Мероприятия»
  {
    const eventsTab = document.getElementById('tab-events');
    const info = document.createElement('p');
    info.textContent = `Ваш ID: ${USER_ID}. Для начисления баллов предоставьте администратору ваш ID.`;
    info.style.fontSize = '14px';
    info.style.margin = '8px 0';
    eventsTab.prepend(info); // в начало вставляем
  }

  // ===== 1) Нижняя навигация =====
  document.querySelectorAll('.bottom-nav button').forEach(btn => {
    // убираем активный класс со всех
    btn.addEventListener('click', () => {
      document.querySelectorAll('.bottom-nav button')
        .forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content')
        .forEach(tab => tab.classList.remove('active'));
      // добавляем активному
      btn.classList.add('active');
      document.getElementById(btn.dataset.target).classList.add('active');
    });
  });

  // ===== 2) Меню =====
  let menuItems = { food: [], drinks: [] };
  fetch('/api/menu')
    .then(r => r.json())
    .then(items => { // items — это результат работы r.json()
      menuItems.food   = items.filter(i => i.category === 'food');
      menuItems.drinks = items.filter(i => i.category === 'drinks');
      renderMenu('food');
      renderMenu('drinks');
      // сразу после отрисовки меню загружаем корзину
      reloadCart();
    });

  function renderMenu(type) {
    const c = document.getElementById(`menu-${type}`);
    c.innerHTML = menuItems[type].map(item => `
      <div class="product-card"
           data-id="${item.id}"
           data-tooltip="
ккал: ${item.calories}
б:   ${item.proteins}
ж:   ${item.fats}
у:   ${item.carbs}">
        <img src="${item.img}" alt="${item.name}">
        <div class="product-info">
          <span class="name">${item.name}</span>
          <span class="price">${item.price}</span>
        </div>
        <button class="add-btn">＋</button>
      </div>
    `).join(''); // склеивает массив строк в одну HTML-строку
    c.querySelectorAll('.add-btn').forEach(btn =>
      btn.addEventListener('click', () =>
        addToCart(+btn.closest('.product-card').dataset.id) // ищем ближайший родительский элемент с классом .product-card
      )
    );
  }

  // отвечате за отображение менб напиткой или еды
  document.querySelectorAll('.menu-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.menu-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.menu-content').forEach(c => c.classList.remove('active'));
      tab.classList.add('active'); // добавляем класс active именно той кнопке, на которую кликнули.
      document.getElementById(`menu-${tab.dataset.menu}`).classList.add('active');
    });
  });

  // ===== 3) Корзина (CRUD на сервере) =====
  function reloadCart() {
    fetch(`/api/cart?user_id=${USER_ID}`)
      .then(r => r.json())
      .then(renderCart); // вызываем renderCart с тем значением, которое вернулось из r.json()
  }

  function addToCart(id) {
    fetch(`/api/cart?user_id=${USER_ID}`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ item_id: id, qty_change: 1 })
    }).then(reloadCart);
  }

  function removeFromCart(id) {
    fetch(`/api/cart?user_id=${USER_ID}`, {
      method: 'DELETE',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ item_id: id, qty_change: -1 })
    }).then(reloadCart);
  }

  function payOrder() {
    fetch('/api/pay', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        user_id: USER_ID,
        chat_id: CHAT_ID
      })
    }).then(response => response.json())
      .then(data => {
        if (data.status === "invoice_sent") {
          showToast("Счёт отправлен в Telegram bot, пожалуйста, оплатите его там.");
        } else {
          showToast("Ошибка при отправке счёта.");
        }
      });
  }

  function renderCart(serverCart) {
    const listEl  = document.getElementById('cart-list');
    const totalEl = document.getElementById('cart-total');
    listEl.innerHTML = '';
    const all = [...menuItems.food, ...menuItems.drinks];
    let sum = 0, count = 0;

    serverCart.forEach(({ item_id, qty }) => {
      const it = all.find(x => x.id === item_id);
      if (!it) return;
      const price = parseInt(it.price.replace(/\D/g,''),10); // убираем все не-числовые символы
      sum += price * qty;
      count += qty;

      const row = document.createElement('div');
      row.className = 'cart-item';
      row.innerHTML = `
        <div class="info">${it.name} — ${it.price}</div>
        <div class="controls">
          <button class="dec">–</button>
          <span class="qty">${qty}</span>
          <button class="inc">＋</button>
        </div>
      `;
      row.querySelector('.inc').addEventListener('click', () => addToCart(item_id));
      row.querySelector('.dec').addEventListener('click', () => removeFromCart(item_id));
      listEl.append(row);
    });

    totalEl.textContent = sum
      ? `Итого: ${sum.toLocaleString('ru-RU')} ₽` // с разделителем тысящ
      : 'Корзина пуста';

    // кнопка «Оплатить»
    const oldBtn = document.getElementById('pay-btn');
    if (oldBtn) oldBtn.remove();
    if (sum) {
      const payBtn = document.createElement('button');
      payBtn.id = 'pay-btn';
      payBtn.className = 'pay-btn';      
      payBtn.textContent = 'Оплатить';
      payBtn.addEventListener('click', payOrder);
      totalEl.parentNode.append(payBtn);
    }

    // бейджик
    const badge = document.getElementById('cart-badge');
    if (count) {
      badge.textContent = count;
      badge.style.display = 'block';
    } else {
      badge.style.display = 'none';
    }
  }

  // ===== 5) Награды =====
  let availableRewards = []
  let userRewards = [] // массив id наград, которые уже взял пользователь
  let userRewardData = []; // подробные объекты взятых наград (включая код)

  function reloadRewards() {
    fetch(`/api/user_points?user_id=${USER_ID}`)
      .then(r => r.json())
      .then(({ points }) => {
        document.getElementById('user-points').textContent = `Ваши баллы: ${points}`;
        return Promise.all([
          fetch('/api/rewards').then(r => r.json()),
          fetch(`/api/user_rewards?user_id=${USER_ID}`).then(r => r.json())
        ]);
      })
      .then(([allR, myR]) => {
        availableRewards = allR.map(r => ({
          id:   r.id,
          name: r.name,
          cost: +r.cost.replace(/\D/g,''),  // число
          img:  r.img
        }));
        userRewardData = myR;            // объекты с code
        userRewards     = myR.map(r => r.id); // только массив id выданных наград
        renderRewards();
      });
  }

  function claimReward(id) {
    fetch(`/api/user_rewards?user_id=${USER_ID}`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ reward_id: id })
    }).then(reloadRewards);
  }

  function renderRewards() {
    // 1) Извлекаем из элемента текста вида "Ваши баллы: 150" число 150
    const remaining = +document.getElementById('user-points').textContent.match(/\d+/)[0];

    // «Выбрать награды»
    const sel = document.getElementById('rewards-select');
    sel.innerHTML = availableRewards.map(r => {
      const disabled = remaining < r.cost;
      return `
        <div class="product-card" data-id="${r.id}">
          <img src="${r.img}" alt="${r.name}">
          <div class="product-info">
            <span class="name">${r.name}</span>
            <span class="price">${r.cost} баллов</span>
          </div>
          <button class="add-btn" ${disabled ? 'disabled' : ''}>
            ${disabled ? 'Не хватает баллов' : 'Получить'}
          </button>
        </div>
      `;
    }).join('');
    sel.querySelectorAll('.add-btn')
      .forEach(btn => btn.addEventListener('click', () =>
        claimReward(+btn.closest('.product-card').dataset.id)
      ));

    // «Полученные»
    const rec = document.getElementById('rewards-received');
    rec.innerHTML = userRewardData.length
      ? userRewardData.map(r => `
        <div class="product-card">
          <img src="${r.img}" alt="${r.name}">
          <div class="product-info">
            <span class="name">${r.name}</span>
            <small>Код: ${r.code}</small>
          </div>
        </div>
      `).join('')
      : '<p>Ничего не получено</p>';
  }

  document.querySelectorAll('.rewards-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.rewards-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.rewards-content').forEach(c => c.classList.remove('active'));
      tab.classList.add('active');
      document.getElementById(`rewards-${tab.dataset.rew}`).classList.add('active');
    });
  });
  reloadRewards();
  setInterval(reloadRewards, 5000);


  // ===== 6) Мероприятия =====
  let events = [], userEvents = [];
  function daysUntil(s) { // ДД.ММ.ГГГГ
    const [d,m,y] = s.split('.').map(Number);
    return (new Date(y,m-1,d) - new Date())/(1000*60*60*24); // месяцы в Date — от 0 до 11; переводим разницу из милисекунд
  }

  function reloadEvents() {
    Promise.all([
      fetch('/api/events').then(r=>r.json()),
      fetch(`/api/user_events?user_id=${USER_ID}`).then(r=>r.json())
    ]).then(([allE, myE]) => {
      events     = allE;
      userEvents = myE.map(e => e.id);
      renderEvents();
    });
  }

  function signUpEvent(id) {
    fetch(`/api/user_events?user_id=${USER_ID}`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({ event_id: id })
    }).then(reloadEvents);
  }

  function renderEvents() {
    const sel = document.getElementById('events-select');
    sel.innerHTML = events.map(ev => {
      const joined = userEvents.includes(ev.id);
      return `
        <div class="event-card" data-id="${ev.id}">
          <img src="${ev.img}" alt="${ev.title}">
          <div class="event-info">
            <span class="title">${ev.title}</span>
            <span class="date">${ev.date}</span>
            <span class="points">${ev.points} баллов</span>
          </div>
          <button ${joined?'disabled':''}>
            ${joined?'Вы записаны':'Записаться'}
          </button>
        </div>
      `;
    }).join('');
    sel.querySelectorAll('.event-card button').forEach(btn =>
      btn.addEventListener('click', () => signUpEvent(+btn.closest('.event-card').dataset.id))
    );

    const my = document.getElementById('events-my');
    const sorted = events
      .filter(ev => userEvents.includes(ev.id))
      .sort((a,b) => daysUntil(b.date) - daysUntil(a.date)); // сортируем по оставшимся дням
    my.innerHTML = sorted.length
      ? sorted.map(ev => `
        <div class="event-card">
          <img src="${ev.img}" alt="${ev.title}">
          <div class="event-info">
            <span class="title">${ev.title}</span>
            <span class="date">${ev.date}</span>
            <span class="points">${ev.points} баллов</span>
          </div>
        </div>
      `).join('')
      : '<p>Нет записей</p>';
  }

  // переключение вкладок
  document.querySelectorAll('.events-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.events-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.events-content').forEach(c => c.classList.remove('active'));
      tab.classList.add('active');
      document.getElementById(`events-${tab.dataset.ev}`).classList.add('active');
    });
  });

  // первая загрузка
  reloadEvents();
});