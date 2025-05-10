let ADMIN_TOKEN;

// Пытаемся запросить список с переданным токеном
function fetchCodes(token) {
  return fetch('/api/admin/reward-codes', {
    headers: { 'Authorization': 'Bearer ' + token }
  });
}

// Блокируем prompt, пока не введён валидный токен
async function askForToken() {
  while (true) {
    const t = prompt("Введите ADMIN_TOKEN");
    // Если пользователь ничего не ввёл (t == null или пустая строка), прыгаем к началу цикла и спрашиваем снова
    if (!t) continue;
    try {
      const res = await fetchCodes(t);
      if (res.ok) {
        ADMIN_TOKEN = t;
        return;
      } else {
        alert("Неверный токен, попробуйте ещё раз");
      }
    } catch {
      alert("Сетевая ошибка");
    }
  }
}


// Перезагружаем таблицу кодов
async function reloadCodes() {
  const res = await fetchCodes(ADMIN_TOKEN); // запрашиваем коды с токеном админа
  if (!res.ok) return;
  const list = await res.json();
  const table = document.getElementById('codes-table');
  // Удаляем старые строки, оставляем только заголовок
  table.querySelectorAll('tr:not(:first-child)').forEach(r => r.remove());
  list.forEach(row => {
    const tr = table.insertRow();
    tr.insertCell().innerText = row.code;
    tr.insertCell().innerText = row.user_id;
    tr.insertCell().innerText = row.reward_name;
    tr.insertCell().innerText = row.issued_at;
    const btnCell = tr.insertCell();
    const btn = document.createElement('button');
    btn.innerText = 'Удалить';
    btn.onclick = async () => {
      await fetch('/api/admin/reward-codes', {
        method: 'DELETE',
        headers: {
          'Authorization': 'Bearer ' + ADMIN_TOKEN,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ code: row.code })
      });
      tr.remove();
    };
    btnCell.appendChild(btn);
  });
}



// Начисление баллов пользователю
async function awardPoints(user_id, points) {
  const res = await fetch('/api/admin/award-points', {
    method: 'POST',
    headers: {
      'Authorization': 'Bearer ' + ADMIN_TOKEN,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ user_id, points })
  });
  if (!res.ok) throw new Error('award-failed');
  return await res.json();
}

// Обработчик кнопки "Начислить баллы"
function setupAwardButton() {
  const btn = document.getElementById('award-btn');
  btn.addEventListener('click', async () => {
    // унарный плюс (+) перед строкой преобразует её в число. Если строка не число — NaN.
    const uid  = +document.getElementById('user-id-input').value;
    const pts  = +document.getElementById('points-input').value;
    if (!uid || !pts) {
      alert('Пожалуйста, укажите и User ID, и количество баллов');
      return;
    }
    try {
      await awardPoints(uid, pts);
      alert(`Пользователю ${uid} начислено ${pts} баллов`);
    } catch {
      alert('Не удалось начислить баллы');
    }
  });
}

// самовызывающаяся асинхронная функция
(async () => {
  await askForToken();
  await reloadCodes();
  setupAwardButton();
  // 4) Авто-обновление таблицы каждые 5 секунд
  setInterval(reloadCodes, 5000);
})();

