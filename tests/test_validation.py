import importlib.util
import unittest
from pathlib import Path
spec = importlib.util.spec_from_file_location('server', Path(__file__).parents[1] / 'backend/server.py')
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)

class ValidationTests(unittest.TestCase):
    def test_rejects_unknown_fields(self):
        with self.assertRaises(ValueError):
            server.validate('materias', {'nombre':'Redes', 'id':2}, True)
    def test_rejects_invalid_schedule(self):
        for fields in [{'materia_id':1,'dia':6,'hora':9}, {'materia_id':True,'dia':1,'hora':9}, {'materia_id':1,'dia':1,'hora':22}]:
            with self.assertRaises(ValueError): server.validate('horario', fields, True)
    def test_rejects_invalid_task(self):
        for update in [{'fecha':'2026-02-30'}, {'completada':'false'}, {'prioridad':'urgente'}, {'titulo':'   '}]:
            with self.assertRaises(ValueError): server.validate('tareas', update, False)
    def test_valid_task(self):
        server.validate('tareas', {'materia_id':1,'titulo':'Proyecto','fecha':'2026-10-20','prioridad':'alta'}, True)

if __name__ == '__main__': unittest.main()
