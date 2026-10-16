CREATE TABLE materias (
 id SERIAL PRIMARY KEY, nombre VARCHAR(100) NOT NULL CHECK (length(trim(nombre)) > 0),
 profesor VARCHAR(100) NOT NULL DEFAULT '', color VARCHAR(7) NOT NULL DEFAULT '#6366f1',
 CHECK (color ~ '^#[0-9a-fA-F]{6}$')
);
CREATE TABLE tareas (
 id SERIAL PRIMARY KEY, materia_id INTEGER NOT NULL REFERENCES materias(id) ON DELETE CASCADE,
 titulo VARCHAR(160) NOT NULL CHECK (length(trim(titulo)) > 0), descripcion TEXT NOT NULL DEFAULT '',
 fecha DATE NOT NULL, prioridad VARCHAR(10) NOT NULL CHECK (prioridad IN ('alta','media','baja')),
 completada BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE TABLE horario (
 id SERIAL PRIMARY KEY, materia_id INTEGER NOT NULL REFERENCES materias(id) ON DELETE CASCADE,
 dia INTEGER NOT NULL CHECK (dia BETWEEN 1 AND 5), hora INTEGER NOT NULL CHECK (hora BETWEEN 7 AND 20),
 aula VARCHAR(80) NOT NULL DEFAULT '', UNIQUE(dia,hora)
);
CREATE INDEX tareas_materia ON tareas(materia_id);
CREATE INDEX tareas_fecha ON tareas(fecha);
-- Horario transcrito de la imagen del grupo 73U. Sin docentes ni tareas iniciales.
-- Horario transcrito de la imagen del grupo 73U. Sin docentes ni tareas iniciales.
INSERT INTO materias(nombre,color) VALUES
 ('Álgebra lineal','#6366f1'),
 ('Cálculo vectorial','#10b981'),
 ('Estadística inferencial','#f59e0b'),
 ('Algoritmia y estructuras de datos','#ec4899'),
 ('Analítica de datos','#0ea5e9'),
 ('Cómputo en la nube','#8b5cf6'),
 ('Tutoría generacional III','#64748b');
INSERT INTO horario(materia_id,dia,hora,aula) VALUES
 (1,1,12,'C5'),
 (1,2,10,'C5'),
 (1,2,11,'C5'),
 (1,3,11,'C5'),
 (1,4,13,'C5'),
 (2,1,11,'C5'),
 (2,2,13,'C5'),
 (2,3,10,'C5'),
 (2,4,12,'C5'),
 (2,5,14,'C5'),
 (3,2,9,'C5'),
 (3,3,12,'C5'),
 (3,4,8,'C5'),
 (3,4,9,'C5'),
 (3,5,8,'C5'),
 (4,1,13,'ALC'),
 (4,3,14,'C5'),
 (4,4,11,'C5'),
 (4,5,11,'ALC'),
 (4,5,12,'ALC'),
 (5,1,9,'ALD'),
 (5,1,10,'ALD'),
 (5,2,12,'C5'),
 (5,3,13,'C5'),
 (5,5,9,'ALD'),
 (6,2,8,'C5'),
 (6,3,8,'ALC'),
 (6,3,9,'ALC'),
 (6,4,10,'C5'),
 (6,5,10,'ALC'),
 (7,5,13,'C5');
