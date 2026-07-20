# Velaris — Sistema de gestión para Hair Recovery

Sistema de gestión web para **Hair Recovery**, una clínica de estética capilar de Rosario con 30 años en el rubro. Velaris centraliza en una sola plataforma la gestión operativa, administrativa y médica: pacientes, turnos, historias clínicas, ventas, stock y reportes.

> **Proyecto académico** desarrollado para la materia **Práctica Profesionalizante I** — Tecnicatura Superior en Desarrollo de Software (Terciario Urquiza, 2do 1ra, 2026). La organización es real; los datos utilizados son simulados.

## Funcionalidades

- **Usuarios y roles** — autenticación y permisos según rol: CEO, Recepcionista, Médico, Enfermero, Instrumentador y Administrativo.
- **Pacientes** — alta, búsqueda por DNI, nombre o apellido, y ficha completa del paciente.
- **Turnos** — gestión de 4 agendas según la prestación: Consultorio, MTC (Microtrasplante Capilar), NTF (Nutrifol) y PRP (Plasma Rico en Plaquetas), cada una con su duración y cantidad de sesiones.
- **Historia clínica** — evoluciones médicas, archivos adjuntos y seguimiento de tratamientos.
- **Recetas** — generación de recetas médicas en PDF con número de receta y código QR de validación.
- **Ventas y caja** — facturación de productos y de sesiones de tratamiento, movimientos de caja y cierre diario.
- **Stock** — control de productos y medicamentos con alertas de stock mínimo.
- **Reportes** — estadísticas de ventas, pacientes, turnos, stock y productividad.

## Tecnologías

| Capa | Tecnología |
|---|---|
| Backend | Python + Django 6.0 |
| Frontend | HTML, CSS y Bootstrap 5 sobre plantillas de Django |
| Base de datos | SQLite (desarrollo) → PostgreSQL (entrega final) |
| Formularios | django-crispy-forms + crispy-bootstrap5 |
| Generación de PDF | WeasyPrint / ReportLab |
| Control de versiones | Git + GitHub |

## Requisitos previos

- Python 3.10 o superior
- Git

## Instalación y puesta en marcha

Cloná el repositorio y entrá a la carpeta del proyecto:

```
git clone https://github.com/marcosnicolasdev-code/velaris.git
cd velaris
```

Creá y activá el entorno virtual:

```
python -m venv venv
source venv/Scripts/activate
```

> En Windows con Git Bash: `source venv/Scripts/activate`
> En Mac o Linux: `source venv/bin/activate`

Instalá las dependencias:

```
pip install -r requirements.txt
```

Aplicá las migraciones y creá un usuario administrador:

```
python manage.py migrate
python manage.py createsuperuser
```

Levantá el servidor de desarrollo:

```
python manage.py runserver
```

Abrí `http://127.0.0.1:8000` en el navegador. El panel de administración está en `http://127.0.0.1:8000/admin`.

> La base de datos ya viene configurada con SQLite: **no hace falta instalar ni configurar nada adicional**.

## Estructura del proyecto

```
velaris/
├── velaris/          # Configuración del proyecto (settings, urls)
├── usuarios/         # Autenticación, roles y permisos
├── pacientes/        # Alta, búsqueda y ficha del paciente
├── turnos/           # Agendas, tratamientos y sesiones
├── ventas/           # Facturación, caja y movimientos
├── stock/            # Productos y medicamentos
├── docs/             # Documentación técnica
│   └── schema.sql    # Modelo relacional del sistema
├── manage.py         # Utilidad de administración de Django
├── requirements.txt  # Dependencias del proyecto
└── README.md
```

Próximas apps a incorporar: `historia_clinica` (evoluciones y recetas) y `reportes`.

## Modelo de datos

El modelo relacional completo está en [`docs/schema.sql`](docs/schema.sql), con las 16 tablas del sistema, sus claves primarias, claves foráneas y restricciones.

Decisiones de diseño principales:

- **Claves primarias autoincrementales** en las entidades internas; claves naturales (`dni`, `codigoProducto`, `idTratamiento`) donde el identificador existe fuera del sistema.
- **`detalleVenta`** resuelve la relación muchos a muchos entre ventas y productos, guardando la cantidad y el precio unitario al momento de la venta.
- **`venta.dni` admite NULL** para permitir ventas ocasionales sin paciente asociado.
- **Restricciones `CHECK`** en los campos de valores limitados: estado del turno, estado de pago, método de pago y tipo de movimiento de caja.

## Alcance

Queda **fuera del alcance** de este proyecto académico:

- Firma digital o electrónica con validez legal en las recetas (se emite el PDF con número de receta y QR de validación propio).
- Integración con facturación fiscal AFIP (se emiten comprobantes internos).
- Aplicación móvil nativa.

## Equipo

| Integrante | Rol |
|---|---|
| **Marcos Nicolás Gómez Ramunno** — [@marcosnicolasdev-code](https://github.com/marcosnicolasdev-code) | Coordinación técnica, base de datos y desarrollo |
| **Ailén Martín Ciliberto** | Análisis funcional y estructura de información |
| **Sofía Ailén Ponce** | Documentación técnica y diagramas |
| **Cristian Iván Reynoso** | Diseño de interfaz y experiencia de usuario |

Profesor: **Diego Serván**

## Estado del proyecto

🚧 **En desarrollo** — Práctica Profesionalizante I (2026).

Documentación y modelo de datos definidos. Estructura de apps creada. Desarrollo de funcionalidades en curso.
