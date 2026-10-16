"""End-to-end HTTP checks; creates and cleans its own records."""
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
BASE = os.getenv('BASE_URL', 'http://localhost:8080')
results = []
def request(path, method='GET', data=None, expected=200):
    req = Request(BASE+path, method=method, data=json.dumps(data).encode() if data is not None else None, headers={'Content-Type':'application/json'})
    try:
        with urlopen(req, timeout=10) as response: status, body = response.status, json.load(response)
    except HTTPError as error: status, body = error.code, json.load(error)
    assert status == expected, (path, status, body)
    results.append({'method':method,'path':path,'status':status,'response':body})
    return body
subject_id = None
try:
    request('/health')
    for route in ('materias','tareas','horario'): assert isinstance(request('/api/'+route), list)
    m=request('/api/materias','POST',{'nombre':'Verificación automática','profesor':'Prueba','color':'#6366f1'},201)
    subject_id=m['id']
    task=request('/api/tareas','POST',{'materia_id':subject_id,'titulo':'Tarea de prueba','fecha':'2026-10-20','prioridad':'alta'},201)
    assert request(f'/api/tareas?materia_id={subject_id}')[0]['id']==task['id']
    assert request('/api/tareas/'+str(task['id']),'PATCH',{'completada':True})['completada'] is True
    request('/api/horario','POST',{'materia_id':subject_id,'dia':6,'hora':9},400)
    request('/api/tareas','POST',{'materia_id':subject_id,'titulo':'Fecha inválida','fecha':'2026-02-30','prioridad':'alta'},400)
    request('/api/materias','POST',{'nombre':'','color':'red'},400)
    request('/api/tareas/999999','GET',expected=404)
    # Test collision with an existing seed class, without modifying it.
    blocks=request('/api/horario')
    if blocks:
        block=blocks[0]
        request('/api/horario','POST',{'materia_id':subject_id,'dia':block['dia'],'hora':block['hora']},409)
    occupied={(b['dia'],b['hora']) for b in blocks}
    free=[(d,h) for d in range(1,6) for h in range(7,21) if (d,h) not in occupied]
    assert len(free)>=2, 'Se requieren dos bloques libres para la prueba.'
    block=request('/api/horario','POST',{'materia_id':subject_id,'dia':free[0][0],'hora':free[0][1],'aula':'QA'},201)
    assert request('/api/horario/'+str(block['id']),'PATCH',{'dia':free[1][0],'hora':free[1][1]})['hora']==free[1][1]
    request('/api/desconocida','GET',expected=404)
finally:
    if subject_id:
        request('/api/materias/'+str(subject_id),'DELETE')
        assert request(f'/api/tareas?materia_id={subject_id}') == []
        assert request(f'/api/horario?materia_id={subject_id}') == []
Path('docs/evidencias/http.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
print(f'{len(results)} solicitudes verificadas. Evidencia: docs/evidencias/http.json')
