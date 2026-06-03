const messages = document.getElementById('messages');
const form = document.getElementById('chatForm');
const input = document.getElementById('chatInput');
const todayBox = document.getElementById('todayBox');

function stars(n){ return '★'.repeat(n) + '☆'.repeat(5-n); }
function escapeHtml(s){ return String(s ?? '').replace(/[&<>"]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m])); }
function bookCard(b){
  const tags = (b.tags || '').split(',').slice(0,5).map(t => `<span class="badge">${escapeHtml(t.trim())}</span>`).join('');
  return `<div class="book">
    <h3>${escapeHtml(b.title)}</h3>
    <div class="meta">${escapeHtml(b.author || '저자 미상')} · ${escapeHtml(b.publisher || '')} · ${escapeHtml(b.year || '')}</div>
    <div>${tags}</div>
    <div class="small"><b>난이도</b> ${stars(Number(b.difficulty || 2))} ${escapeHtml(b.difficulty_label || '')}</div>
    <div class="small"><b>관련 진로</b> ${escapeHtml(b.careers || '')}</div>
    <div class="small"><b>내용 요약</b> ${escapeHtml(b.summary || '')}</div>
    <div class="small"><b>추천 이유</b> ${escapeHtml(b.recommendation_reason || '')}</div>
    <div class="topic"><b>탐구주제</b><br>${escapeHtml(b.exploration_topic || '')}</div>
  </div>`;
}
function addMessage(role, text, books=[]){
  const el = document.createElement('div');
  el.className = `msg ${role}`;
  el.innerHTML = escapeHtml(text);
  if(books && books.length){
    el.innerHTML += `<div class="bookGrid">${books.map(bookCard).join('')}</div>`;
  }
  messages.appendChild(el);
  messages.scrollTop = messages.scrollHeight;
}
async function sendMessage(text){
  const msg = (text || input.value).trim();
  if(!msg) return;
  addMessage('user', msg);
  input.value='';
  try{
    const res = await fetch('/api/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:msg})});
    const data = await res.json();
    addMessage('bot', data.reply || '답변을 만들지 못했어요.', data.books || []);
  }catch(e){
    addMessage('bot', '서버 연결에 문제가 있어요. 잠시 뒤 다시 시도해 주세요.');
  }
}
form.addEventListener('submit', e => { e.preventDefault(); sendMessage(); });
document.querySelectorAll('.quick button').forEach(btn => btn.addEventListener('click', () => sendMessage(btn.dataset.msg)));
async function loadToday(){
  try{
    const res = await fetch('/api/today'); const data = await res.json(); const b = (data.books || [])[0];
    if(!b){todayBox.textContent = '오늘의 책을 불러오지 못했습니다.'; return;}
    todayBox.innerHTML = `<div class="todayTitle">📚 오늘의 책</div><h3>${escapeHtml(b.title)}</h3><div class="meta">${escapeHtml(b.author || '')}</div><div class="small"><b>난이도</b> ${stars(Number(b.difficulty || 2))} ${escapeHtml(b.difficulty_label || '')}</div><div class="small">${escapeHtml(b.recommendation_reason || '')}</div>`;
  }catch(e){ todayBox.textContent = '오늘의 책을 불러오지 못했습니다.'; }
}
loadToday();
