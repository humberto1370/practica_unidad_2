"""HTTP gateway and independently deployed PostgreSQL resource services."""
import json
import os
import re
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from urllib.request import Request, build_opener, ProxyHandler
from urllib.error import HTTPError, URLError

RESOURCE = os.getenv('RESOURCE', 'gateway')
FIELDS = {
    'materias': {'nombre', 'profesor', 'color'},
    'tareas': {'materia_id', 'titulo', 'descripcion', 'fecha', 'prioridad', 'completada'},
    'horario': {'materia_id', 'dia', 'hora', 'aula'},
}
REQUIRED = {'materias': {'nombre'}, 'tareas': {'materia_id', 'titulo', 'fecha', 'prioridad'}, 'horario': {'materia_id', 'dia', 'hora'}}
UPSTREAM = {r: f'http://horarioservicio{i}:8000' for i, r in enumerate(FIELDS, 1)}

def validate(resource, data, creating):
    if not isinstance(data, dict) or not data or set(data) - FIELDS[resource]:
        raise ValueError('Campos vacíos o desconocidos.')
    if creating and REQUIRED[resource] - set(data):
        raise ValueError('Faltan campos obligatorios.')
    for key, value in data.items():
        if key in {'materia_id', 'dia', 'hora'}:
            if type(value) is not int or value < 1:
                raise ValueError(f'{key} debe ser un entero positivo.')
        elif key == 'completada':
            if type(value) is not bool:
                raise ValueError('completada debe ser booleano.')
        elif not isinstance(value, str):
            raise ValueError(f'{key} debe ser texto.')
    for key, limit in {'nombre':100,'profesor':100,'titulo':160,'aula':80}.items():
        if key in data and (len(data[key]) > limit or (key in {'nombre','titulo'} and not data[key].strip())):
            raise ValueError(f'{key} vacío o demasiado largo.')
    if 'color' in data and not re.fullmatch(r'#[0-9a-fA-F]{6}', data['color']):
        raise ValueError('Color inválido.')
    if 'fecha' in data:
        date.fromisoformat(data['fecha'])
    if 'prioridad' in data and data['prioridad'] not in {'alta','media','baja'}:
        raise ValueError('Prioridad inválida.')
    if 'dia' in data and not 1 <= data['dia'] <= 5:
        raise ValueError('Día fuera de rango.')
    if 'hora' in data and not 7 <= data['hora'] <= 20:
        raise ValueError('Hora fuera de rango.')

class Handler(BaseHTTPRequestHandler):
    def respond(self, status, payload):
        body = json.dumps(payload, default=str, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def handle_request(self):
        path = urlsplit(self.path).path
        if path == '/health' and self.command == 'GET':
            if RESOURCE != 'gateway':
                import psycopg
                with psycopg.connect(os.environ['DATABASE_URL']) as conn:
                    conn.execute('SELECT 1')
            return self.respond(200, {'status':'ok','service':RESOURCE})
        if RESOURCE == 'gateway':
            if path.startswith('/api/'):
                resource = path.split('/')[2]
                if resource not in UPSTREAM:
                    return self.respond(404, {'error':'API no encontrada.'})
                body = self.read_body() if self.command in {'POST','PATCH'} else None
                request = Request(UPSTREAM[resource] + self.path, data=body, method=self.command,
                                  headers={'Content-Type':'application/json'})
                try:
                    with build_opener(ProxyHandler({})).open(request, timeout=8) as response:
                        return self.respond(response.status, json.loads(response.read()))
                except HTTPError as error:
                    return self.respond(error.code, json.loads(error.read()))
                except (URLError, TimeoutError):
                    return self.respond(502, {'error':'Microservicio no disponible.'})
            if self.command != 'GET':
                return self.respond(405, {'error':'Método no permitido.'})
            files = {'/':'index.html','/app.js':'app.js','/styles.css':'styles.css'}
            if path not in files:
                return self.respond(404, {'error':'Página no encontrada.'})
            file = Path(__file__).parent / 'web' / files[path]
            content = file.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', {'html':'text/html; charset=utf-8','js':'text/javascript; charset=utf-8','css':'text/css; charset=utf-8'}[file.suffix[1:]])
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            return self.wfile.write(content)
        match = re.fullmatch(r'/api/' + RESOURCE + r'(?:/(\d+))?', path)
        if not match:
            return self.respond(404, {'error':'Ruta no encontrada.'})
        import psycopg
        from psycopg.rows import dict_row
        record_id = int(match[1]) if match[1] else None
        with psycopg.connect(os.environ['DATABASE_URL'], row_factory=dict_row) as conn:
            if self.command == 'GET':
                query = f'SELECT * FROM {RESOURCE}'
                params = []
                if record_id:
                    query += ' WHERE id=%s'
                    params.append(record_id)
                elif RESOURCE in {'tareas','horario'}:
                    values = parse_qs(urlsplit(self.path).query)
                    if 'materia_id' in values:
                        query += ' WHERE materia_id=%s'
                        params.append(int(values['materia_id'][0]))
                query += ' ORDER BY id'
                rows = conn.execute(query, params).fetchall()
                if record_id and not rows:
                    return self.respond(404, {'error':'Registro no encontrado.'})
                return self.respond(200, rows[0] if record_id else rows)
            if self.command == 'DELETE' and record_id:
                row = conn.execute(f'DELETE FROM {RESOURCE} WHERE id=%s RETURNING id', [record_id]).fetchone()
                conn.commit()
                return self.respond(200 if row else 404, row or {'error':'Registro no encontrado.'})
            if self.command not in {'POST','PATCH'} or (self.command == 'POST' and record_id) or (self.command == 'PATCH' and not record_id):
                return self.respond(405, {'error':'Método no permitido.'})
            data = json.loads(self.read_body())
            validate(RESOURCE, data, self.command == 'POST')
            keys = list(data)
            if self.command == 'POST':
                query = f"INSERT INTO {RESOURCE} ({','.join(keys)}) VALUES ({','.join(['%s']*len(keys))}) RETURNING *"
                params = list(data.values())
            else:
                query = f"UPDATE {RESOURCE} SET {','.join(k+'=%s' for k in keys)} WHERE id=%s RETURNING *"
                params = list(data.values()) + [record_id]
            row = conn.execute(query, params).fetchone()
            conn.commit()
            return self.respond((201 if self.command == 'POST' else 200) if row else 404, row or {'error':'Registro no encontrado.'})

    def read_body(self):
        size = int(self.headers.get('Content-Length', '0'))
        if not 0 < size <= 65536:
            raise ValueError('Cuerpo vacío o demasiado grande.')
        return self.rfile.read(size)

    def dispatch(self):
        try:
            self.handle_request()
        except (ValueError, UnicodeDecodeError) as error:
            self.respond(400, {'error':str(error)})
        except Exception as error:
            code = getattr(error, 'sqlstate', None)
            if code in {'23505','23503','23514','22001','22007','22P02','23502'}:
                self.respond(409 if code in {'23505','23503'} else 400, {'error':'Horario ocupado o datos relacionados inválidos.' if code in {'23505','23503'} else 'Datos inválidos.'})
            else:
                print(type(error).__name__, str(error), flush=True)
                self.respond(503, {'error':'Servicio temporalmente no disponible.'})

    do_GET = do_POST = do_PATCH = do_DELETE = dispatch

if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', 8000), Handler).serve_forever()
