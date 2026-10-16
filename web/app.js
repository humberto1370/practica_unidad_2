'use strict';
const $ = s => document.querySelector(s);
const state = {materias: [], tareas: [], horario: []};
const days = ['Lunes','Martes','Miércoles','Jueves','Viernes'];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const subject = id => state.materias.find(m => m.id === id);
const localDate = () => {const d = new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;};
let messageTimer, editing, dragged;
function notify(text) {$('#message').textContent=text;$('#message').hidden=false;clearTimeout(messageTimer);messageTimer=setTimeout(()=>$('#message').hidden=true,5500);}
async function api(resource, method='GET', data, id) {
 const response = await fetch(`/api/${resource}${id ? '/'+id : ''}`, {method,headers:{'Content-Type':'application/json'},...(data ? {body:JSON.stringify(data)}:{})});
 const result=await response.json();if(!response.ok) throw new Error(result.error || 'No se pudo guardar.');return result;
}
async function load() {
 try {const result=await Promise.all(['materias','tareas','horario'].map(r=>api(r)));['materias','tareas','horario'].forEach((r,i)=>state[r]=result[i]);render();}
 catch(e) {notify('No se pudieron cargar los datos: '+e.message);}
}
function render() {
 const pending=state.tareas.filter(t=>!t.completada);
 $('#pending').textContent=pending.length;$('#urgent').textContent=pending.filter(t=>t.prioridad==='alta').length;$('#subjects').textContent=state.materias.length;$('#done').textContent=state.tareas.length-pending.length;
 const filter=$('#subject-filter').value;
 $('#subject-filter').innerHTML='<option value="">Todas las materias</option>'+state.materias.map(m=>`<option value="${m.id}">${esc(m.nombre)}</option>`).join('');$('#subject-filter').value=filter;
 renderTasks();renderSchedule();
 $('#subject-list').innerHTML=state.materias.map(m=>`<article class="subject-card" style="--color:${m.color}"><span class="subject-symbol">▤</span><button class="icon" data-edit-subject="${m.id}" aria-label="Editar ${esc(m.nombre)}">⋯</button><h3>${esc(m.nombre)}</h3><p>${esc(m.profesor)||'Sin profesor asignado'}</p><p>${pending.filter(t=>t.materia_id===m.id).length} tareas pendientes · ${state.horario.filter(h=>h.materia_id===m.id).length} clases / semana</p></article>`).join('')||'<p class="empty">Agrega tu primera materia para comenzar.</p>';
}
function renderTasks() {
 const selected=$('#subject-filter').value,status=$('#status-filter').value,search=$('#search').value.toLocaleLowerCase();
 const weights={alta:0,media:1,baja:2};
 const tasks=state.tareas.filter(t=>(!selected||t.materia_id===Number(selected))&&(status==='all'||t.completada===(status==='done'))&&t.titulo.toLocaleLowerCase().includes(search));
 tasks.sort((a,b)=>$('#sort').value==='priority' ? weights[a.prioridad]-weights[b.prioridad]||a.fecha.localeCompare(b.fecha):a.fecha.localeCompare(b.fecha)||weights[a.prioridad]-weights[b.prioridad]);
 $('#task-count').textContent=tasks.length;
 $('#task-list').innerHTML=tasks.map(t=>{const m=subject(t.materia_id);const late=t.fecha<localDate()&&!t.completada;return `<article class="task ${t.completada?'completed':''}"><input type="checkbox" data-complete="${t.id}" ${t.completada?'checked':''} aria-label="Completar ${esc(t.titulo)}"><div class="task-main"><div class="task-title">${esc(t.titulo)}</div><div class="task-meta"><span><i class="dot" style="background:${m?.color||'#6366f1'}"></i>${esc(m?.nombre)}</span><span class="${late?'overdue':''}">${late?'Vencida · ':''}${new Date(t.fecha+'T12:00:00').toLocaleDateString('es-MX',{day:'numeric',month:'short',year:'numeric'})}</span></div></div><span class="badge ${t.prioridad}">${t.prioridad[0].toUpperCase()+t.prioridad.slice(1)}</span><button class="icon" data-edit-task="${t.id}" aria-label="Editar ${esc(t.titulo)}">⋯</button></article>`;}).join('')||'<div class="empty">No hay tareas con estos filtros.</div>';
}
function renderSchedule() {
 let html='<div class="day">HORA</div>'+days.map(d=>`<div class="day">${d}</div>`).join('');
 for(let hour=7;hour<=20;hour++) {html+=`<div class="hour">${hour}:00</div>`;for(let day=1;day<=5;day++) {
 const block=state.horario.find(h=>h.dia===day&&h.hora===hour),m=block&&subject(block.materia_id),count=m?state.tareas.filter(t=>t.materia_id===m.id&&!t.completada).length:0;
 html+=`<button class="slot" data-day="${day}" data-hour="${hour}" ${block?`data-class="${block.id}"`:''} aria-label="${days[day-1]} ${hour}:00${m?', '+esc(m.nombre):', agregar clase'}">${m?`<div class="class-card" draggable="true" data-drag="${block.id}" style="--color:${m.color}"><strong>${esc(m.nombre)}</strong><small>${esc(block.aula)||'Sin aula'} · ${count} pendientes</small></div>`:''}</button>`;
 }}$('#schedule').innerHTML=html;
}
function openEditor(resource,id,defaults={}) {
 if(resource!=='materias'&&!state.materias.length)return notify('Primero agrega una materia.');
 const record=id?state[resource].find(x=>x.id===id):defaults;
 editing={resource,id};const noun={materias:'materia',tareas:'tarea',horario:'clase'}[resource];$('#modal-title').textContent=(id?'Editar ':'Nueva ')+noun;
 const input=(label,name,value='',type='text',extra='')=>`<label>${label}<input name="${name}" type="${type}" value="${esc(value)}" ${extra}></label>`;
 const options=state.materias.map(m=>`<option value="${m.id}" ${record.materia_id===m.id?'selected':''}>${esc(m.nombre)}</option>`).join('');
 let fields='';
 if(resource==='materias') fields=input('Nombre','nombre',record.nombre,'text','required maxlength="100"')+input('Profesor/a','profesor',record.profesor,'text','maxlength="100"')+input('Color','color',record.color||'#6366f1','color');
 else {fields=`<label>Materia<select name="materia_id" required>${options}</select></label>`;
 if(resource==='tareas') fields+=input('Título','titulo',record.titulo,'text','required maxlength="160"')+`<label>Descripción<textarea name="descripcion" rows="3">${esc(record.descripcion)}</textarea></label>`+input('Fecha de entrega','fecha',record.fecha||localDate(),'date','required')+`<label>Prioridad<select name="prioridad">${['alta','media','baja'].map(p=>`<option ${p===(record.prioridad||'media')?'selected':''}>${p}</option>`).join('')}</select></label>`;
 else fields+=`<label>Día<select name="dia">${days.map((d,i)=>`<option value="${i+1}" ${record.dia===i+1?'selected':''}>${d}</option>`).join('')}</select></label><label>Hora<select name="hora">${Array.from({length:14},(_,i)=>i+7).map(h=>`<option value="${h}" ${h===(record.hora||9)?'selected':''}>${h}:00 – ${h+1}:00</option>`).join('')}</select></label>`+input('Aula','aula',record.aula,'text','maxlength="80"');
 }$('#fields').innerHTML=fields;$('#delete-record').hidden=!id;$('#editor').showModal();
}
$('#edit-form').addEventListener('submit',async event=>{event.preventDefault();const data=Object.fromEntries(new FormData(event.target));for(const key of ['materia_id','dia','hora'])if(key in data)data[key]=Number(data[key]);$('#save').disabled=true;try {await api(editing.resource,editing.id?'PATCH':'POST',data,editing.id);$('#editor').close();await load();notify('Cambios guardados.');}catch(e){notify(e.message);}finally{$('#save').disabled=false;}});
$('#delete-record').onclick=async()=>{if(!confirm(editing.resource==='materias'?'Se eliminarán también las tareas y clases de esta materia. ¿Continuar?':'¿Eliminar este registro?'))return;try{await api(editing.resource,'DELETE',null,editing.id);$('#editor').close();await load();notify('Registro eliminado.');}catch(e){notify(e.message);}};
$('#close-modal').onclick=$('#cancel-modal').onclick=()=>$('#editor').close();
$('#new-task').onclick=()=>openEditor('tareas');$('#new-class').onclick=()=>openEditor('horario');$('#new-subject').onclick=()=>openEditor('materias');
for(const id of ['search','subject-filter','status-filter','sort'])$('#'+id).addEventListener(id==='search'?'input':'change',renderTasks);
document.addEventListener('click',event=>{const button=event.target.closest('button');if(!button)return;const d=button.dataset;if(d.editTask)openEditor('tareas',Number(d.editTask));if(d.editSubject)openEditor('materias',Number(d.editSubject));if(d.day)openEditor('horario',d.class?Number(d.class):null,{dia:Number(d.day),hora:Number(d.hour)});});
document.addEventListener('change',async event=>{const id=event.target.dataset.complete;if(!id)return;event.target.disabled=true;try{await api('tareas','PATCH',{completada:event.target.checked},id);await load();}catch(e){event.target.checked=!event.target.checked;notify(e.message);}finally{event.target.disabled=false;}});
document.addEventListener('dragstart',event=>{const card=event.target.closest('[data-drag]');if(card){dragged=Number(card.dataset.drag);event.dataTransfer.setData('text/plain',String(dragged));event.dataTransfer.effectAllowed='move';}});
document.addEventListener('dragover',event=>{const slot=event.target.closest('.slot');if(slot&&!slot.dataset.class){event.preventDefault();slot.classList.add('drop');}});
document.addEventListener('dragleave',event=>event.target.closest('.slot')?.classList.remove('drop'));
document.addEventListener('dragend',()=>{dragged=null;document.querySelectorAll('.drop').forEach(s=>s.classList.remove('drop'));});
document.addEventListener('drop',async event=>{const slot=event.target.closest('.slot');if(!slot)return;event.preventDefault();slot.classList.remove('drop');const id=dragged;if(!id||slot.dataset.class)return;try{await api('horario','PATCH',{dia:Number(slot.dataset.day),hora:Number(slot.dataset.hour)},id);await load();notify('Clase movida.');}catch(e){notify(e.message);}});
$('#today').textContent=new Date().toLocaleDateString('es-MX',{weekday:'long',day:'numeric',month:'long',year:'numeric'});
load();
