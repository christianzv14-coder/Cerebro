# 🗞️ FORMULARIO 2: PUBLICACIONES (ALP)
> [!TIP]
> Puedes pegar hasta 6 publicaciones aquí. Sepáralas claramente.

## POST #1
- **Fecha (aprox):** 06/01/2026
- **Contenido:** 
(Pega el texto completo aquí)
¿Cross-docking o almacenamiento?
La eficiencia del xdock se rompe antes de lo que crees.

El término “cross-docking” suena eficiente, lean, moderno.
Pero no todos los modelos son iguales.

Según la literatura (Bartholdi & Hackman, Stalk et al., 1992), existen varios tipos:

✅Distributor cross-docking
Recibir componentes de múltiples proveedores y consolidarlos en una unidad de despacho.
Ejemplo: Un distribuidor de insumos médicos recibe productos desde distintos orígenes, arma kits completos y los envía directo a hospitales.

✅Transportation cross-docking
Agrupar envíos de diferentes clientes para optimizar carga (LTL o paquetería).
Común en couriers: reciben miles de paquetes, los ordenan y consolidan por destino.

✅Retail cross-docking
Recepción de múltiples proveedores → despacho directo a tiendas.
Así comenzó Walmart a superar a Kmart en los 90.

✅Opportunistic cross-docking
Traslado directo en el CD desde los muelles de recepción de almacenamiento cuando hay demanda conocida.
Si, esto no es una operación tan común.

En todos los casos, el principio es claro:
El producto no entra al almacén, sólo pasa.

Suena ideal: menos toques, menor costo, mayor velocidad.

Pero…
No siempre es posible y no siempre es conveniente.

¿Cuándo el cross-docking falla?
➡️Demanda volátil
Si varía mucho la demanda, necesitas buffer para responder.
Sin este buffer, hay quiebres frecuentes en tienda porque hay un tiempo más alto para que el proveedor responda versus preparar desde el CD.

➡️Falta de ASN o mala calidad del ingreso
Ejemplo, carga no paletizada lo que implica hacer sorting manual o revisiones a detalle del ingreso.

➡️Proveedor con bajo nivel de servicio
Entregas tardías, faltantes, errores. 
Esto también genera quiebres.

En estos casos el cross docking deja de ser eficiente y es mejor almacenar para luego distribuir.

¿Entonces, estamos subsidiando al proveedor?
Sí, estamos absorbiendo ineficiencias, pero hay formas de mitigarlo.

Algunas estrategias:
🔹Modelo híbrido: xdock + buffer mínimo
Solo xdock para SKUs estables (A-items).
Para productos volátiles: mantén stock de seguridad para abastecer desde el CD. Así reduces inventario sin sacrificar disponibilidad.

🔹Vendor management intensivo
Scorecards con el proveedor, penalizaciones/bonos.
Acuerdos de “cost sharing”: si falla, comparte el costo del almacenamiento.

🔹Exigir estándares mínimos
ASN anticipado.
Paletizado según norma. Acá los manuales de proveedores se vuelven muy relevantes.

El cross docking es una herramienta operativa tremendamente útil, pero como en todas las cosas, no siempre aplica y es importante entender cuando presenta estas dificultades. 
Las eficiencias no se alcanzan forzando un modelo…
Es mejor diseñar un sistema que absorba la incertidumbre sin sacrificar al cliente.
---
## POST #2
- **Fecha (aprox):** 02/01
- **Contenido:** 
(Pega el texto completo aquí)
Me definí un objetivo para este 2026: desarrollar una academia de logística 100% online, hecha por y para quienes viven la operación todos los días.

No para repetir teorías, sino para entregar métodos aplicables, con rigor y sentido común, que se usen al día siguiente de estar haciendo el curso.

Pero no quiero adivinar, quiero construirlo con esta red de expertos y potenciales usuarios de los cursos.

---
## POST #3
- **Fecha (aprox):** 26/12/2025
- **Contenido:** 
(Pega el texto completo aquí)
¿El ABC es suficiente para tu slotting?
¿Y si le introducimos una variable espacial?
Spoiler: si tienes productos muy distintos en tamaño, podría ser útil.

En este post vamos a ampliar la mirada del slotting ABC.
Muchos centros de distribución lo usan:

Productos A (alta rotación) → cerca del despacho.
Productos C (baja rotación) → lejos.
Funciona bien en muchos casos.

Pero tiene una limitación crítica:
Ignora el volumen físico.

Y eso puede costar eficiencia

El problema del producto grande
Si pones un SKU voluminoso en zona premium, ocupa espacio que podría usar decenas de productos pequeños.

Es como estacionar un camión en los estacionamientos del supermercado.

Para esto, existe una métrica muy interesante: Cube per Order Index (COI)
El COI combina dos dimensiones:

Volumen del SKU.
Cantidad de órdenes en las que aparece.
Se calcula así:

COI = Volumen del SKU / Número de órdenes

Luego, se clasifican:

Bajo COI: consumen poco espacio por pedido → van a zonas premium.
Alto COI: consumen mucho espacio por pedido → van a zonas lejanas.

Así, un producto grande y poco frecuente (alto COI) se ubica lejos, aunque sea “importante”.

¿Dada la complejidad, cómo se implementa?
No es tan diferente del ABC:

➡️ Zonas por rango de COI
Define zonas: premium, estándar, baja rotación.
Asigna SKUs por su COI, no por rotación.
Revisa cada 30-60 días para ajustar.

➡️Manejo de nuevos productos
Calcula COI estimado con datos históricos o proyecciones.
Asígnalo a una zona de prueba.
Después de 30 días, reubícalo con datos reales.

¿Cuándo usar ABC vs. COI?

ABC es ideal cuando:
🔹Productos similares en tamaño.
🔹Demanda estable.
🔹Necesitas algo rápido.

COI es superior cuando:
🔹Gran variedad de tamaños (e-commerce, retail, big ticket).
🔹Espacio limitado.
🔹Hay SKUs voluminosos con baja rotación.

Porque considera no solo la frecuencia, sino también el impacto espacial.

Disclaimer: 
He revisado bastante el COI en literatura académica, pero nunca lo he implementado.
requiere buena data de volumetría, algo que en muchos almacenes no es fácil además que la administración es más compleja.

Pero creo que vale la pena explorarlo.
Porque añadir una dimensión extra al slotting puede generar eficiencia real.
---
## POST #4
- **Fecha (aprox):** 19/12/2025
- **Contenido:** 
(Pega el texto completo aquí)
Tu nuevo operario empieza hoy.
¿Le estás enseñando lo más importante? 
En logística, cada error cuesta caro.

En temporada alta, muchos CD’s duplican su dotación con personal temporal.
Y los que lideramos las operaciones, siempre necesitamos que rindan desde el primer día.

Pero hay un problema:

No todas las tareas son iguales.

Algunas son frecuentes pero simples.
Otras son más esporádicas pero críticas.
Y si fallan, generan errores graves.

Y por eso, no todas deben capacitarse igual.

Además:
🔹No puedes enseñarlo todo.
🔹No todos aprenden al mismo ritmo.
🔹Lo más frecuente no siempre es lo más importante.

Entonces, ¿qué priorizas?

Usa 3 criterios para decidir qué capacitar primero
➡️ Frecuencia: ¿cuántas veces se hace?
➡️Impacto del error: ¿qué pasa si se hace mal?
➡️Dificultad de aprendizaje: ¿cuánto tiempo toma dominarla?


Con esto, defines el tipo de capacitación:
✅ Capacitación rápida
Alta frecuencia + bajo impacto.
Ejemplo: picking básico de productos.

✅ Capacitación intensiva
Baja frecuencia + alto impacto.
Ejemplo: inventario cíclico o control de calidad.

✅ Capacitación especializada
Alta dificultad + alto impacto.
Ejemplo: Procesos de consolidación de mercadería.

Cómo aplicar esto mañana mismo:

➡️Lista las 5-7 tareas clave de tu operación.
➡️Evalúa cada una con los 3 criterios (usa escala 1-5).
➡️Clasifícalas: rápida, intensiva o especializada.
➡️Empieza por las de alto impacto, no por las más frecuentes.

Así aseguras que tu equipo esté listo para lo que más importa.

Enseñar no es suficiente.
Necesitas verificar que se aprendió .
Y la mejor forma no es un examen teórico.
Es una prueba práctica supervisada.

Intenta evaluar los siguientes ámbitos: Precisión, velocidad ¿está dentro del rango esperado?, autonomía, manejo de errores.

Así aseguras que tu equipo esté listo para lo que más importa.
---
## POST #5
- **Fecha (aprox):** 12/12/2025
- **Contenido:** 
(Pega el texto completo aquí)
Un CD al 100% de ocupación no es eficiente.
Es inoperable.
Y los problemas comienzan a partir del 80%.

Los que estamos en el mundo de la logística tenemos el concepto de que los CDs debieran estar a un 80% de ocupación máxima.

¿Pero de dónde viene ese número?
¿Es válido para todos los tipos de operación?

Lo que sí sabemos con certeza es que cuando se supera este indicador, comienzan los problemas:

➡️Se pierde el slotting: ya no puedes almacenar productos de alta rotación cerca del despacho. Los pones donde “hay lugar”, no donde deben ir.
➡️Las rutas de picking se alargan: más tiempo buscando, más errores.
➡️La recepción se congestiona: si no hay staging porque no se ha almacenado, los camiones esperan.

Entonces, ¿por qué 80%?

El número tiene un trasfondo matemático, no solo empírico. 
Viene de la teoría de colas, que analiza las filas de espera en sistemas con entradas y salidas variables… igual que en un centro de distribución.

Dado que la fórmula de tiempo de espera tiene en su denominador:

(1 – ocupación del sistema)

Cuando la ocupación se acerca al 100%, el tiempo de espera tiende a infinito.

La teoría muestra que el tiempo de espera crece de forma exponencial a medida que te acercas al 100% de ocupación.

Este mismo concepto nos lleva a que mientras más alta es la rotación, es decir, mientras menor tiempo de espera necesites, el sistema debe tener menor ocupación. 

Podríamos llegar a la siguiente regla:
✅ E-commerce / retail (alta rotación): 70–75%
✅ Industrial / B2B (flujo pallets completos): 80–85%
✅ Cross-dock con alto flujo: ≤ 60%

La ocupación óptima de un centro de distribución no es una cifra arbitraria, sino el resultado de un análisis cuidadoso y fundamentado en principios matemáticos y operativos. 

Adaptar estos porcentajes a las necesidades específicas de cada operación es crucial para mantener la eficiencia y capacidad de respuesta.

Al comprender y aplicar estos conceptos, podemos optimizar nuestras operaciones logísticas, asegurando un flujo continuo y efectivo de mercadería.

---
## POST #6
- **Fecha (aprox):** 5/12/2025
- **Contenido:** 
(Pega el texto completo aquí)
Ruteo dinámico o ruteo estático:
la primera decisión que define tu última milla.

En general se habla bastante de la optimización de rutas en e-commerce y última milla, pero he visto poca conversación de una primera decisión:

¿Usar polígonos fijos o generar rutas dinámicas según el volumen diario? 

Esta elección define todo lo que sigue: eficiencia, costo, experiencia de cliente y capacidad de escalamiento.

Veamos cada uno de los casos:
➡️ Ruteo estático o por polígonos
Consiste en dividir la ciudad en zonas geográficas fijas.
Cada vehículo opera dentro de su polígono, día tras día.

Ventajas:
✅Operativamente más sencillo: puedes armar rutas a medida que llega la mercadería.
✅Los transportistas conocen bien su zona: estacionamientos, tráfico, accesibilidad, puntos críticos.


Desventajas:
⛔Ineficiencias en bordes: entregar una calle en el límite puede ser más eficiente desde el polígono vecino.
⛔Subutilización de flota: si tienes demanda para 1,8 vehículos, pierdes capacidad.
⛔Poca flexibilidad ante peaks o cambios en la demanda.

➡️ Ruteo dinámico
Se espera a tener toda la carga disponible para generar rutas globales, considerando restricciones como:
Capacidad del vehículo, Kilómetros máximos, Tiempo por entrega.

Ventajas:
✅Mayor eficiencia: reduce kilómetros totales y número de vehículos necesarios.
✅Aprovecha mejor la flota: evita subutilización.

Desventajas:
⛔Requiere conocer todo el volumen antes de comenzar a armar rutas por lo que puede atrasar el despacho.
⛔Algunas “optimizaciones” teóricas no son realistas en terreno. Ejemplo, el ruteo asume que el transportista en todas partes es capaz de entregar X paquetes con Y kms, pero no considera efectos como tráfico, estacionamiento, etc.

Entonces, ¿cuál elegir?

Como respuesta tradicional: Depende.

➡️ El ruteo estático podría ser recomendable:
✅ Si existe un volumen estable y bien definido para cada polígono.
✅ Es necesario priorizar la simplicidad operativa de preparación de cada ruta, por ejemplo si tienes que despachar gran cantidad de vehículos.

Es un modelo robusto cuando la incertidumbre es baja y la ejecución debe ser previsible

➡️ El ruteo dinámico podría ser recomendable
✅ Demanda muy variable lo que podría generar que un flujo estático genere mucha ineficiencia.
✅ Necesitas reducir el costo variable y maximizar la utilización de flota.
✅ Puedes controlar los tiempos de preparación.
 
Es ideal cuando la eficiencia global pesa más que la predictibilidad
 
Acá también hay espacio para las soluciones mixtas:
🔹Períodos del año que puede ser más eficiente un método.
🔹Zonas de operación por polígono y zonas por ruteo dinámico.
 
La decisión de como preparar las rutas es estratégica y es la decisión que une el mundo operativo con la ejecución de la última milla.