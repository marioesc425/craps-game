const chipValues = [1, 5, 6, 25, 100, 500];
const chipColors = ['#f3eee0', '#bc4545', '#26968a', '#32804f', '#45423b', '#7855a3'];
const placeNumbers = [4, 5, 6, 8, 9, 10];
const hardNumbers = [6, 10, 8, 4];
const $ = (id) => document.getElementById(id);
const state = { socket: null, playerId: getPlayerId(), name: '', room: '', selected: 1, game: null, reconnect: false };

function getPlayerId() {
  let id = sessionStorage.getItem('goldenRailPlayer');
  if (!id) {
    id = globalThis.crypto?.randomUUID?.() || `p-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    sessionStorage.setItem('goldenRailPlayer', id);
  }
  return id;
}

function buildBoard() {
  const place = $('place-zones');
  const xs = [286, 395, 504, 614, 723, 832];
  placeNumbers.forEach((num, i) => {
    const x = xs[i], width = i === 2 || i === 3 ? 110 : 109;
    place.insertAdjacentHTML('beforeend', `<g data-zone="place_${num}"><rect x="${x}" y="96" width="${width}" height="109"/><text x="${x + width/2}" y="168">${num}</text><text x="${x + width/2}" y="194" class="number-small">PLACE</text></g>`);
  });
  const hard = $('hardway-zones');
  hard.insertAdjacentHTML('beforeend', '<rect x="960" y="250" width="380" height="207" fill="none" stroke="#dfd4b8" stroke-width="3" pointer-events="none"/><text x="1150" y="282" class="hard-label">HARDWAYS</text>');
  const cells = [[962,302,197,78],[1159,302,181,78],[962,380,197,77],[1159,380,181,77]];
  hardNumbers.forEach((num, i) => {
    const [x,y,w,h] = cells[i];
    hard.insertAdjacentHTML('beforeend', `<g data-zone="hard_${num}"><rect x="${x}" y="${y}" width="${w}" height="${h}"/><text x="${x+w/2}" y="${y+34}" class="hard-label">HARD ${num}</text><text x="${x+w/2}" y="${y+62}" class="number-small">${num === 6 || num === 8 ? '9 to 1' : '7 to 1'}</text></g>`);
  });
  $('chip-tray').className = 'chip-tray';
  $('chip-tray').innerHTML = chipValues.map((v, i) => `<button class="chip" data-chip="${i}" style="--chip:${chipColors[i]}" aria-label="$${v} chip">$${v}</button>`).join('') + '<span class="selected-readout">SELECTED <b id="selected-display">$5</b></span>';
}

function showLobbyError(message) {
  $('lobby-error').textContent = message;
  if (state.game) $('status-message').textContent = message;
}

function connect(room, name) {
  if (state.socket && state.socket.readyState < WebSocket.CLOSING) state.socket.close();
  state.name = name;
  state.room = room;
  state.reconnect = false;
  const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
  const socket = new WebSocket(`${scheme}://${location.host}/ws`);
  state.socket = socket;
  $('connection').classList.remove('online');
  $('connection').lastElementChild.textContent = 'Connecting…';
  socket.addEventListener('open', () => {
    socket.send(JSON.stringify({ type: 'join', room: state.room, name: state.name, player_id: state.playerId }));
    $('connection').lastElementChild.textContent = 'Connected';
  });
  socket.addEventListener('message', (event) => {
    const message = JSON.parse(event.data);
    if (message.type === 'state') render(message);
    else if (message.type === 'error') showLobbyError(message.message);
  });
  socket.addEventListener('close', () => {
    $('connection').classList.remove('online');
    $('connection').lastElementChild.textContent = 'Reconnecting…';
    if (state.game && !state.reconnect) {
      state.reconnect = true;
      window.setTimeout(() => connect(state.room, state.name), 2200);
    }
  });
  socket.addEventListener('error', () => {
    $('connection').classList.remove('online');
    $('connection').lastElementChild.textContent = 'Offline';
  });
}

function send(payload) {
  if (state.socket?.readyState === WebSocket.OPEN) state.socket.send(JSON.stringify(payload));
  else showLobbyError('Connecting to the table… try again in a moment.');
}

function canBet(zoneName) {
  const game = state.game;
  const me = game?.players.find(p => p.id === game.you);
  if (!me || game.rolling || chipValues[state.selected] > me.bankroll) return false;
  if ((zoneName === 'pass_line' || zoneName.startsWith('dont_pass')) && game.point !== null) return false;
  if ((zoneName === 'come' || zoneName === 'dont_come') && game.point === null) return false;
  const match = zoneName.match(/^(place|hard)_(\d+)$/);
  const rawNumber = match ? Number(match[2]) : null;
  const betType = match ? (match[1] === 'hard' ? 'hardway' : 'place')
    : zoneName.startsWith('dont_pass') ? 'dont_pass' : zoneName;
  const existing = me.wagers.find(b => b.type === betType && b.number === rawNumber);
  if (chipValues[state.selected] < 5 && !existing) return false;
  if (betType === 'place') {
    const odds = {4:[9,5],5:[7,5],6:[7,6],8:[7,6],9:[7,5],10:[9,5]}[rawNumber];
    if ((Number(existing?.amount || 0) + chipValues[state.selected]) * odds[0] % odds[1]) return false;
  }
  return true;
}

function drawStacks(game) {
  const layer = $('stack-layer');
  layer.innerHTML = '';
  const owners = game.players;
  let stacks = [];
  for (const person of owners) for (const bet of person.wagers) stacks.push({ person, bet });
  for (const {person, bet} of stacks) {
    const colorIndex = owners.findIndex(p => p.id === person.id) % chipColors.length;
    const x = bet.x, y = bet.y;
    const isMine = person.id === game.you;
    const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    group.setAttribute('class', `chip-stack ${isMine ? 'mine' : ''}`);
    group.dataset.owner = person.id;
    group.dataset.betId = bet.id;
    group.setAttribute('transform', `translate(${x} ${y})`);
    group.innerHTML = `<circle r="20" style="fill:${chipColors[colorIndex]};${isMine ? 'stroke:#fff0bd;stroke-width:4' : ''}"/><circle r="15" fill="none" stroke="#fff8" stroke-width="1"/><text y="1" style="fill:${colorIndex === 0 ? '#17221b' : '#fff5df'}">$${bet.amount}</text><text class="owner" y="29">${escapeXml(person.name.slice(0,1).toUpperCase())}</text>${bet.odds ? `<text x="23" y="21" style="fill:#ffe298;font-size:10px">+${bet.odds}</text>` : ''}`;
    layer.appendChild(group);
  }
}

function renderPlayers(game) {
  const list = $('player-list');
  list.innerHTML = game.players.map(person => {
    const betTotal = person.wagers.reduce((s,b) => s + b.amount + b.odds, 0);
    const classes = ['player-card', person.id === game.you ? 'me' : ''].join(' ');
    const dot = ['seat-dot', person.online ? 'online' : '', person.shooter ? 'shooter' : ''].join(' ');
    return `<div class="${classes}"><div class="player-top"><i class="${dot}"></i>${escapeXml(person.name)}${person.id === game.you ? '<span class="you-tag">YOU</span>' : ''}</div><div class="bank">$${person.bankroll.toFixed(2)}</div><div class="player-bets">On table $${betTotal} ${person.shooter ? '· shooter' : ''}</div></div>`;
  }).join('');
  $('player-count').textContent = `${game.players.length} / 6`;
}

function render(game) {
  state.game = game;
  state.room = game.room;
  sessionStorage.setItem('goldenRailRoom', game.room);
  sessionStorage.setItem('goldenRailName', state.name);
  const url = new URL(location.href);
  url.searchParams.set('room', game.room);
  history.replaceState(null, '', url);
  $('lobby').classList.add('hidden');
  $('table-view').classList.remove('hidden');
  $('connection').classList.add('online');
  $('connection').lastElementChild.textContent = 'Live table';
  $('room-display').textContent = game.room;
  $('point-display').textContent = game.point === null ? 'POINT OFF' : `POINT ${game.point}`;
  $('phase-label').textContent = game.rolling ? 'DICE ROLLING' : (game.point === null ? 'COME OUT' : 'POINT PHASE');
  $('roll-display').textContent = game.dice ? `${game.dice[0]} + ${game.dice[1]} = ${game.dice[0] + game.dice[1]}` : '—';
  $('history-display').textContent = `Recent: ${game.history.join(' · ') || '—'}`;
  const shooter = game.players.find(p => p.id === game.shooter);
  $('shooter-display').textContent = game.rolling ? 'Dice are in the air…'
    : shooter && !game.shooter_online ? 'Shooter left — next player can take over'
    : shooter ? `${shooter.name} is shooter` : 'Waiting for players…';
  $('status-message').textContent = game.message;
  const me = game.players.find(p => p.id === game.you);
  $('roll').disabled = !me || game.rolling || (game.shooter !== game.you && game.shooter_online) || !game.players.some(p => p.wagers.length);
  $('roll').innerHTML = game.rolling ? 'Rolling… <b>⚄</b>' : 'Roll dice <b>⚄</b>';
  $('undo').disabled = game.rolling || !game.undo_available;
  for (const button of document.querySelectorAll('.chip')) button.disabled = !me || chipValues[Number(button.dataset.chip)] > me.bankroll || game.rolling;
  for (const button of document.querySelectorAll('.chip')) button.classList.toggle('selected', Number(button.dataset.chip) === state.selected);
  $('selected-display').textContent = `$${chipValues[state.selected]}`;
  drawStacks(game);
  renderPlayers(game);
}

function escapeXml(value) { return String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

buildBoard();
const queryRoom = new URLSearchParams(location.search).get('room');
$('room-code').value = queryRoom || '';
$('player-name').value = localStorage.getItem('goldenRailName') || '';
$('join-form').addEventListener('submit', (event) => {
  event.preventDefault();
  const name = $('player-name').value.trim().slice(0,18) || 'Guest';
  const room = $('room-code').value.trim().toUpperCase();
  localStorage.setItem('goldenRailName', name);
  connect(room, name);
});

$('chip-tray').addEventListener('click', event => {
  const button = event.target.closest('[data-chip]');
  if (!button || button.disabled) return;
  state.selected = Number(button.dataset.chip);
  if (state.game) render(state.game);
});

$('table').addEventListener('click', event => {
  if (!state.tablePointerDown) return;
  state.tablePointerDown = false;
  const stack = event.target.closest('.chip-stack');
  if (stack) {
    if (stack.dataset.owner !== state.game?.you) {
      $('status-message').textContent = 'You can add chips or odds to your own wagers.';
      return;
    }
    send({type:'stack', bet_id:Number(stack.dataset.betId), chip:chipValues[state.selected]});
    return;
  }
  const zone = event.target.closest('[data-zone]');
  if (zone) send({type:'bet', zone:zone.dataset.zone, chip:chipValues[state.selected]});
});

document.addEventListener('pointerdown', event => {
  state.tablePointerDown = Boolean(event.target.closest?.('#table'));
}, true);

$('table').addEventListener('pointerover', event => {
  const zone = event.target.closest('[data-zone]');
  if (zone) {
    const valid = canBet(zone.dataset.zone);
    zone.classList.toggle('valid-hover', valid);
    zone.classList.toggle('invalid-hover', !valid);
    zone.querySelectorAll?.('rect').forEach(rect => {
      rect.classList.toggle('valid-hover', valid);
      rect.classList.toggle('invalid-hover', !valid);
    });
  }
});
$('table').addEventListener('pointerout', event => {
  const zone = event.target.closest('[data-zone]');
  if (zone) {
    zone.classList.remove('valid-hover', 'invalid-hover');
    zone.querySelectorAll?.('rect').forEach(rect => rect.classList.remove('valid-hover', 'invalid-hover'));
  }
});
$('undo').addEventListener('click', () => send({type:'undo'}));
$('roll').addEventListener('click', () => send({type:'roll'}));
$('copy-link').addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(`${location.origin}/?room=${state.room}`);
    $('copy-link').textContent = 'Invite link copied';
    setTimeout(() => $('copy-link').textContent = 'Copy invite link', 1800);
  } catch { $('copy-link').textContent = `Room ${state.room}`; }
});

const savedRoom = sessionStorage.getItem('goldenRailRoom');
const savedName = localStorage.getItem('goldenRailName');
if (savedRoom && savedName) {
  $('player-name').value = savedName;
  $('room-code').value = queryRoom || savedRoom;
  connect(queryRoom || savedRoom, savedName);
}
setInterval(() => {
  if (state.socket?.readyState === WebSocket.OPEN) state.socket.send(JSON.stringify({type:'ping'}));
}, 25000);
