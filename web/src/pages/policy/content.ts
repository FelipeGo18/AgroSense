/**
 * El texto de la política de tratamiento de datos (HU-163, R9). Dice, con más detalle, lo mismo que el consentimiento
 * de «Crear cuenta». Misma redacción que el diseño: design/pantallas/politica.py.
 *
 * Cada frase sale de las specs (R9 de specs/01-reglas.md, HU-160 a HU-165, HU-170, HU-178, HU-200 y
 * specs/02-contratos.md): aquí no se promete nada que el sistema no haga. Si cambia lo que se guarda, cambia este
 * texto y sube la versión del consentimiento.
 *
 * **Falta la revisión legal** (Ley 1581 de 2012 de Colombia, decisión 11) y el canal de contacto del responsable: la
 * página lo dice mientras `LEGAL_REVIEW_PENDING` sea verdadero.
 */

/** Mientras sea verdadero, la página avisa que el texto todavía no pasó por revisión legal. */
export const LEGAL_REVIEW_PENDING = true;

export const POLICY_SINCE = "11 de octubre de 2026";

/** Qué dice una frase: algo que se guarda, algo que nunca se guarda o una explicación. */
export type Mark = "kept" | "never" | "note";

export const SECTIONS: { title: string; items: { mark: Mark; text: string }[] }[] = [
  {
    title: "Qué guardamos cuando tiene cuenta",
    items: [
      { mark: "kept", text: "Su usuario, el nombre con que quiere que lo llamemos y sus prioridades." },
      { mark: "kept", text: "Sus lotes: el nombre, el contorno que dibujó en el mapa, su área y si tienen riego." },
      { mark: "kept", text: "Sus siembras y cosechas, con el diagnóstico que vio al sembrar." },
      { mark: "kept", text: "Sus sesiones abiertas, para que pueda entrar desde varios dispositivos." },
      { mark: "kept", text: "La actividad de su cuenta durante 180 días: qué se hizo y cuándo, no lo que escribió." },
      { mark: "kept", text: "Los reportes que nos escriba." },
    ],
  },
  {
    title: "Qué no guardamos",
    items: [
      { mark: "never", text: "Correo, celular, documento ni dirección. No los pedimos." },
      { mark: "never", text: "Su contraseña: se guarda una huella que no se puede leer. Por eso no se puede recuperar." },
      { mark: "never", text: "Lo que consulta sin cuenta: se envía solo para calcular y no queda guardado." },
      { mark: "never", text: "Quién hizo cada consulta. Solo se cuenta cuántas hubo por día, municipio y cultivo." },
    ],
  },
  {
    title: "Para qué los usamos",
    items: [
      { mark: "note", text: "Para mostrarle su finca y para que las estrategias de rotación usen su historial real." },
      {
        mark: "note",
        text: "Lo que siembra se suma, sin su nombre, a los totales de su municipio. Esos totales solo se muestran cuando hay al menos 5 cuentas.",
      },
      { mark: "note", text: "No se usan para nada más." },
    ],
  },
  {
    title: "Quién puede verlos",
    items: [
      { mark: "note", text: "Usted, con su usuario y su contraseña." },
      { mark: "note", text: "Se guardan en una base de datos en la nube y viajan cifrados entre AgroSense y esa base." },
      {
        mark: "note",
        text: "Soporte puede ver sus lotes para ayudarle. Cada vez que lo hace queda escrito en «Mi actividad», donde usted lo puede ver.",
      },
    ],
  },
  {
    title: "Cuánto tiempo y cómo borrarlos",
    items: [
      { mark: "note", text: "Se guardan mientras tenga la cuenta. La actividad se borra sola a los 180 días." },
      { mark: "note", text: "En «Mi cuenta» puede ver lo que guardamos, cambiar su nombre y su usuario, y borrar su cuenta." },
      {
        mark: "note",
        text: "Borrar la cuenta lo borra todo: usuario, sesiones, lotes, siembras, reportes y actividad. No se puede deshacer.",
      },
    ],
  },
  {
    title: "En su navegador",
    items: [
      { mark: "note", text: "Una sola cookie, la de su sesión. No hay cookies de publicidad ni de seguimiento." },
      {
        mark: "note",
        text: "El modo ligero, el sonido y, sin cuenta, sus prioridades se recuerdan en este dispositivo y no salen de él.",
      },
    ],
  },
];
