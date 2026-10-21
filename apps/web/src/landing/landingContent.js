import { LANDING_SECTION_IDS } from "../app/routePaths.js";

export const LANDING_NAV = [
  { label: "Beneficios", sectionId: LANDING_SECTION_IDS.benefits },
  { label: "Funcionalidades", sectionId: LANDING_SECTION_IDS.features },
  { label: "Planes", sectionId: LANDING_SECTION_IDS.plans },
  { label: "Cómo funciona", sectionId: LANDING_SECTION_IDS.howItWorks },
];

/** @typedef {'available' | 'demo' | 'planned'} FeatureAvailability */

/** @type {{ id: string; title: string; description: string; availability: FeatureAvailability }[]} */
export const LANDING_FEATURES = [
  {
    id: "branches",
    title: "Sucursales",
    description: "Alta y consulta conectadas al backend dentro de su tenant autorizado.",
    availability: "available",
  },
  {
    id: "roles",
    title: "Personal y permisos",
    description: "Roles y permisos validados en servidor en cada operación gym.",
    availability: "available",
  },
  {
    id: "members",
    title: "Socios",
    description: "Pantallas demo con datos ficticios; la operación real llegará en fases posteriores.",
    availability: "demo",
  },
  {
    id: "memberships",
    title: "Membresías",
    description: "Exploración visual de planes y asignaciones — no es contratación operativa aún.",
    availability: "demo",
  },
  {
    id: "attendance",
    title: "Asistencias",
    description: "Indicadores y registros de ejemplo para anticipar el módulo de control de acceso.",
    availability: "demo",
  },
  {
    id: "reports",
    title: "Reportes",
    description: "Exportaciones e indicadores administrativos en diseño para releases futuros.",
    availability: "planned",
  },
];

export const AVAILABILITY_LABELS = {
  available: "Disponible hoy",
  demo: "Demostración UI",
  planned: "Planificado",
};

/** @type {{ id: string; title: string; body: string; icon: string; size: 'large' | 'medium' }[]} */
export const LANDING_BENEFITS = [
  {
    id: "central",
    title: "Administración centralizada",
    body: "Un solo acceso para coordinar la operación de su gimnasio con contexto claro por tenant.",
    icon: "hub",
    size: "large",
  },
  {
    id: "branches",
    title: "Control de sucursales",
    body: "Organice ubicaciones, códigos y estados con datos conectados al backend cuando corresponda.",
    icon: "branch",
    size: "large",
  },
  {
    id: "roles",
    title: "Roles y permisos",
    body: "El servidor valida quién puede operar; el navegador no define autorizaciones.",
    icon: "shield",
    size: "medium",
  },
  {
    id: "process",
    title: "Procesos más ordenados",
    body: "Flujos de login, selección de gimnasio y trabajo diario con menos fricción administrativa.",
    icon: "flow",
    size: "medium",
  },
  {
    id: "scale",
    title: "Preparación para crecer",
    body: "Arquitectura multi-sucursal lista para incorporar socios, membresías y reportes.",
    icon: "growth",
    size: "medium",
  },
  {
    id: "visibility",
    title: "Visibilidad administrativa",
    body: "Interfaz coherente para el equipo, con distinción honesta entre lo operativo y lo planificado.",
    icon: "insight",
    size: "medium",
  },
];

export const CONTRACT_STEPS = [
  {
    title: "Conocer Gym ERP y consultar planes",
    detail:
      "Revise beneficios, funcionalidades y referencias de planes. Mientras el catálogo se publica, puede escribirnos por WhatsApp.",
  },
  {
    title: "Elegir plan mensual o anual",
    detail:
      "Cuando exista catálogo aprobado, podrá comparar opciones SaaS mensuales y anuales según el tamaño de su operación.",
  },
  {
    title: "Enviar solicitud de contratación",
    detail:
      "El formulario público de solicitudes se implementará en una fase posterior; hoy el canal activo es contacto comercial directo.",
  },
  {
    title: "Revisión del equipo Gym ERP",
    detail: "Toda solicitud será evaluada manualmente antes de proponer activación o condiciones.",
  },
  {
    title: "Pago por transferencia o efectivo",
    detail:
      "Sin pasarela en línea en esta etapa. El pago se coordina por canales externos acordados.",
  },
  {
    title: "Aprobación y activación",
    detail:
      "Tras confirmar el pago acordado, activamos el tenant con revisión administrativa — no es automático.",
  },
  {
    title: "Iniciar sesión y administrar",
    detail: "Acceda con su cuenta gym, seleccione tenant y opere sucursales dentro de sus permisos.",
  },
];

export const LANDING_FAQ = [
  {
    question: "¿Qué es Gym ERP?",
    answer:
      "Plataforma SaaS para administrar gimnasios y sucursales: accesos, permisos y módulos operativos en evolución continua.",
  },
  {
    question: "¿A quién está dirigido?",
    answer:
      "A propietarios y equipos administrativos de gimnasios que buscan centralizar sucursales y ordenar la operación.",
  },
  {
    question: "¿Puedo administrar varias sucursales?",
    answer:
      "Sí, dentro del gimnasio (tenant) autorizado. Cada acción respeta el tenant activo y los permisos del servidor.",
  },
  {
    question: "¿Cómo puedo solicitar información?",
    answer:
      "Por WhatsApp al +52 1 221 180 3440 o revisando esta landing. Pronto habrá formulario de solicitud en el sitio.",
  },
  {
    question: "¿Cómo se contratará una suscripción?",
    answer:
      "Consulta de planes, solicitud formal, revisión del equipo, pago externo acordado y activación manual del tenant.",
  },
  {
    question: "¿Se pueden realizar pagos en línea?",
    answer: "No en esta fase. No hay pasarela integrada; los pagos se acuerdan por transferencia o efectivo.",
  },
  {
    question: "¿Cuándo se activa el servicio?",
    answer:
      "Después de aprobación administrativa y confirmación del pago acordado. Los plazos comerciales específicos están por definir.",
  },
  {
    question: "¿Puedo consultar planes por WhatsApp?",
    answer:
      "Sí. Use el botón «Consultar planes por WhatsApp» o el contacto flotante; le responderemos con información comercial disponible.",
  },
];

export const PLANS_PLACEHOLDER_MESSAGE =
  "Tarifas en preparación: estamos definiendo el catálogo SaaS mensual y anual.";

export const PLANS_PLACEHOLDER_DETAIL =
  "Los niveles Básico, Profesional y Empresarial son referencias comerciales futuras. No hay precios publicados ni checkout en esta versión.";

/** @type {{ name: string; blurb: string }[]} */
export const PLANS_SKELETON_TIERS = [
  {
    name: "Básico",
    blurb: "Para gimnasios que inician la digitalización de sucursales y accesos.",
  },
  {
    name: "Profesional",
    blurb: "Para operaciones con varias sucursales y mayor necesidad de coordinación.",
  },
  {
    name: "Empresarial",
    blurb: "Para organizaciones con requisitos ampliados de permisos y escala.",
  },
];
