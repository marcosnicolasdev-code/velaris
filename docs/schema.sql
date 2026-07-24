-- Modelo relacional - VELARIS --

-- Tablas independientes --

CREATE TABLE usuario ( 
    idUsuario               INTEGER PRIMARY KEY AUTOINCREMENT,
    nombreUsuario           VARCHAR(50) NOT NULL,
    apellidoUsuario         VARCHAR(50) NOT NULL,
    rolUsuario              VARCHAR(20) NOT NULL,
    contraseña              VARCHAR(20) NOT NULL
);

CREATE TABLE paciente (
    dni                     VARCHAR(20) PRIMARY KEY,
    nombrePaciente          VARCHAR(20) NOT NULL,
    apellidoPaciente        VARCHAR(20) NOT NULL,
    fechaNacimiento         DATE NOT NULL,
    domicilio               VARCHAR(50),
    localidad               VARCHAR(50),
    correoElectronico       VARCHAR(50) NOT NULL,
    telefono                VARCHAR(20) NOT NULL,
    obraSocial              VARCHAR(20),
    sexo                    VARCHAR(1)
);

CREATE TABLE tratamiento (
    idTratamiento           VARCHAR(20) PRIMARY KEY,
    duracionTratamiento     TIME NOT NULL,
    sesionTratamiento       SMALLINT NOT NULL
);

CREATE TABLE producto (
    codigoProducto          SMALLINT PRIMARY KEY,
    nombreProducto          VARCHAR(20) NOT NULL,
    cantidadProducto        SMALLINT NOT NULL,
    categoriaProducto       VARCHAR(20) NOT NULL,
    precioProducto          INT NOT NULL
);

-- Tablas dependientes --

CREATE TABLE profesional (
    idProfesional           INTEGER PRIMARY KEY AUTOINCREMENT,
    idUsuario               INT NOT NULL, 
    matricula               VARCHAR(20) NOT NULL,
    especialidad            VARCHAR(20) NOT NULL,
    FOREIGN KEY (idUsuario) REFERENCES usuario(idUsuario)
);

CREATE TABLE historiaClinica (
    idHistoriaClinica       INTEGER PRIMARY KEY AUTOINCREMENT,
    dni                     VARCHAR(20) NOT NULL,
    FOREIGN KEY (dni) REFERENCES paciente(dni)
);

CREATE TABLE turno (
    idTurno                 INTEGER PRIMARY KEY AUTOINCREMENT,
    idTratamiento           VARCHAR(20) NOT NULL,
    dni                     VARCHAR(20) NOT NULL,
    estado                  VARCHAR(20) NOT NULL
                            CHECK (estado IN ('asignado', 'reservado', 'finalizado', 'ausente', 'cancelado')), 
    fechaAsistencia           DATETIME NOT NULL,
    FOREIGN KEY (idTratamiento) REFERENCES tratamiento(idTratamiento),
    FOREIGN KEY (dni) REFERENCES paciente(dni)
);

CREATE TABLE evaluacionMedica (
    idEvaluacion            INTEGER PRIMARY KEY AUTOINCREMENT,
    idProfesional           INT NOT NULL,
    idHistoriaClinica       INT NOT NULL,
    fechaEvaluacion         DATE NOT NULL,
    descripcion             TEXT NOT NULL,
    FOREIGN KEY (idProfesional) REFERENCES profesional(idProfesional),
    FOREIGN KEY (idHistoriaClinica) REFERENCES historiaClinica(idHistoriaClinica)
);

CREATE TABLE archivo (
    idArchivo               INTEGER PRIMARY KEY AUTOINCREMENT,
    idEvaluacion            INT NOT NULL,
    archivoAdjunto          TEXT NOT NULL,
    FOREIGN KEY (idEvaluacion) REFERENCES evaluacionMedica(idEvaluacion)
);

CREATE TABLE receta (
    numeroReceta            INTEGER PRIMARY KEY AUTOINCREMENT,
    dni                     VARCHAR(20) NOT NULL,
    idProfesional           INT NOT NULL,
    codigoProducto          SMALLINT NOT NULL,
    idHistoriaClinica       INT NOT NULL,
    fechaReceta             DATE NOT NULL,
    dosis                   SMALLINT NOT NULL,
    frecuencia              VARCHAR(20), 
    duracionIndicacion      VARCHAR(20) NOT NULL,
    FOREIGN KEY (dni) REFERENCES paciente(dni),
    FOREIGN KEY (idProfesional) REFERENCES profesional(idProfesional),
    FOREIGN KEY (codigoProducto) REFERENCES producto(codigoProducto),
    FOREIGN KEY (idHistoriaClinica) REFERENCES historiaClinica(idHistoriaClinica)
);

CREATE TABLE planPago (
    idPlan                  INTEGER PRIMARY KEY AUTOINCREMENT,
    dni                     VARCHAR(20) NOT NULL,
    idTratamiento           VARCHAR(20) NOT NULL,
    valorSesion             INT NOT NULL,
    fechaInicioTratamiento  DATE NOT NULL,
    FOREIGN KEY (dni) REFERENCES paciente(dni),
    FOREIGN KEY (idTratamiento) REFERENCES tratamiento(idTratamiento)
);

CREATE TABLE sesion (
    idSesion                INTEGER PRIMARY KEY AUTOINCREMENT,
    idPlan                  INT NOT NULL,
    idTurno                 INT NOT NULL,
    duracionSesion          TIME NOT NULL,
    numeroSesion            SMALLINT NOT NULL,
    estadoPago              VARCHAR(20)
                            CHECK (estadoPago IN ('pendiente', 'abonado')),
    FOREIGN KEY (idPlan) REFERENCES planPago(idPlan),
    FOREIGN KEY (idTurno) REFERENCES turno(idTurno)
);

CREATE TABLE venta (
    idVenta                 INTEGER PRIMARY KEY AUTOINCREMENT,
    dni                     VARCHAR(20),
    metodoPago              VARCHAR(20) NOT NULL
                            CHECK (metodoPago IN ('efectivo', 'debito', 'credito', 'transferencia')),
    fechaVenta              DATE NOT NULL,
    totalVenta              INT NOT NULL,
    FOREIGN KEY (dni) REFERENCES paciente(dni)
);

CREATE TABLE detalleVenta (
    idDetalleVenta          INTEGER PRIMARY KEY AUTOINCREMENT,
    idVenta                 INT NOT NULL,
    codigoProducto          SMALLINT NOT NULL,
    cantidadUnitaria        INT NOT NULL,
    precioUnitario          INT NOT NULL,
    FOREIGN KEY (idVenta) REFERENCES venta(idVenta),
    FOREIGN KEY (codigoProducto) REFERENCES producto(codigoProducto)
);

CREATE TABLE caja (
    idCaja                  INTEGER PRIMARY KEY AUTOINCREMENT,
    idUsuario               INT NOT NULL,
    totalCaja               INT
                            DEFAULT (0),
    aperturaCaja            DATETIME NOT NULL,
    cierreCaja              DATETIME,
    FOREIGN KEY (idUsuario) REFERENCES usuario(idUsuario)
);

CREATE TABLE movimientoCaja (
    idMovimientoCaja        INTEGER PRIMARY KEY AUTOINCREMENT,
    idCaja                  INT NOT NULL,
    tipoMovimiento          VARCHAR(20) NOT NULL
                            CHECK (tipoMovimiento IN ('ingreso', 'egreso')),
    importeMovimiento       INT NOT NULL,
    fechaMovimiento         DATETIME NOT NULL,
    FOREIGN KEY (idCaja) REFERENCES caja(idCaja)
);

