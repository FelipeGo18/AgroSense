import ts from "typescript";
import en from "@/locales/en.json";
import es from "@/locales/es.json";
import calculations from "../../../backend/api/calculations.py?raw";

const files = import.meta.glob<string>("../**/*.{ts,tsx}", { query: "?raw", import: "default", eager: true });
const labels = new Set(["aria-label", "title", "placeholder", "label", "loadingText", "legend", "description", "alt"]);
const names = new Set(["AgroSense", "· AgroSense", ", Boyacá"]);
const keys = new Set(Object.keys(en));
const spanish = new Set(
  Object.entries(es)
    .filter(([key, value]) => value !== en[key as keyof typeof en])
    .map(([, value]) => value),
);
const properNames = new Set([
  "Tunja",
  "Aquitania",
  "Duitama",
  "Samacá",
  "Sogamoso",
  "Toca",
  "Ventaquemada",
  "Boyacá",
  "NASA POWER",
  "SMAP (NASA)",
  "NASADEM (NASA)",
  "EVA",
  "EVA (UPRA)",
  "SoilGrids (ISRIC)",
  "SIPSA (DANE)",
  "GPM IMERG · NASA",
  "NASADEM · NASA",
  "SoilGrids · ISRIC",
  "SIPSA · DANE",
  "GitHub",
  "Instagram",
  "LinkedIn",
  "YouTube",
]);
const uiField = /^(?:name|label|title|text|hint|message|note|description|caption|placeholder|loadingText|legend|alt)$/i;
const uiConstant = /(?:^|_)(?:NAME|NAMES|LABEL|LABELS|TITLE|TITLES|TEXT|TEXTS|HINT|HINTS|MESSAGE|MESSAGES|NOTE|NOTES|CAPTION|CAPTIONS|PLACEHOLDER)(?:_|$)/;

function audit(text: string, path: string) {
  const missing: string[] = [];
  const source = ts.createSourceFile(path, text, ts.ScriptTarget.Latest, true);
  const report = (node: ts.Node, value: string) =>
    missing.push(`${path}:${source.getLineAndCharacterOfPosition(node.getStart(source)).line + 1}: ${value}`);
  const translator = (node: ts.Node) => ts.isCallExpression(node) && ["t", "i18n.t"].includes(node.expression.getText(source));
  const contextualText = (node: ts.Node) => {
    for (let parent: ts.Node | undefined = node.parent; parent; parent = parent.parent) {
      if (ts.isPropertyAssignment(parent) && uiField.test(parent.name.getText(source).replaceAll('"', ""))) return true;
      if (ts.isVariableDeclaration(parent) && uiConstant.test(parent.name.getText(source))) return true;
      if (ts.isFunctionLike(parent)) break;
    }
    return false;
  };
  const visit = (node: ts.Node) => {
    if (ts.isJsxText(node)) {
      const value = node.text.trim().replace(/\s+/g, " ");
      if (/\p{L}/u.test(value) && !names.has(value)) report(node, value);
    }
    if (ts.isJsxAttribute(node) && labels.has(node.name.getText(source)) && node.initializer && ts.isStringLiteral(node.initializer)) {
      if (/\p{L}/u.test(node.initializer.text)) report(node, node.initializer.text);
    }
    if (translator(node)) {
      const key = (node as ts.CallExpression).arguments[0];
      if (key && ts.isStringLiteral(key) && !keys.has(key.text)) report(node, `missing key: ${key.text}`);
    }
    if (
      ts.isStringLiteral(node) ||
      ts.isNoSubstitutionTemplateLiteral(node) ||
      ts.isTemplateHead(node) ||
      ts.isTemplateMiddle(node) ||
      ts.isTemplateTail(node)
    ) {
      const value = node.text.trim();
      const parent = node.parent;
      const propertyKey = (ts.isPropertyAssignment(parent) || ts.isPropertySignature(parent)) && parent.name === node;
      const translated =
        translator(parent) ||
        (ts.isPropertyAssignment(parent) && ts.isCallExpression(parent.parent.parent) && translator(parent.parent.parent));
      // Esta frase es un discriminador de protocolo, no texto visible. La prueba de abajo la vincula al backend.
      const protocol =
        path.endsWith("pages/diagnosis/DiagnosisPage.tsx") &&
        ts.isVariableDeclaration(parent) &&
        parent.name.getText(source) === "SOWING_DATE_OUT_OF_RANGE_MESSAGE";
      const contextual = contextualText(node);
      const human = contextual || /\b(?:de la|del suelo|de los|de su|sin datos|fecha de|no se|para su)\b/i.test(value);
      const codeToken = /^(?:[a-z][a-z0-9_.:/-]*|#[\da-fA-F]+)$/.test(value);
      const machine = keys.has(value) || (codeToken && (!contextual || /[_.:/-]/.test(value)) && !spanish.has(value));
      if (
        !propertyKey &&
        !translated &&
        !protocol &&
        human &&
        /\p{L}/u.test(value) &&
        !machine &&
        !properNames.has(value) &&
        !names.has(value)
      )
        report(node, value);
    }
    ts.forEachChild(node, visit);
  };
  visit(source);
  return missing;
}

it("ninguna pantalla deja textos fijos en JSX, constantes, objetos o plantillas ni usa claves inexistentes (HU-233)", () => {
  const missing: string[] = [];
  for (const [path, text] of Object.entries(files)) {
    // entry-server solo genera el HTML en el build; mocks conserva las respuestas originales de la API.
    if (/\.test\.|schema\.d\.ts$|\/mocks\/|\/entry-server\.tsx$/.test(path)) continue;
    missing.push(...audit(text, path));
  }
  expect(missing).toEqual([]);
});

it.each([
  'const LAYER_NAME = { ndvi: "Verdor" };',
  'const STATUS_TEXT = { loading: "Cargando la imagen" };',
  'const STATUS_TEXT = { idle: "listo" };',
  'const caption = `Fecha de la imagen: ${date}`;',
])("detecta texto fuera de JSX: %s", (source) => expect(audit(source, "Panel.tsx")).not.toEqual([]));

it("acepta constantes que guardan claves y plantillas que traducen su texto", () => {
  expect(audit('const TITLE = "labels.example"; const caption = `${t("labels.example")}: ${date}`;', "Panel.tsx")).toEqual([]);
});

it("el discriminador de fecha coincide con el mensaje real del backend", () => {
  const message = files["../pages/diagnosis/DiagnosisPage.tsx"].match(/const SOWING_DATE_OUT_OF_RANGE_MESSAGE = "([^"]+)"/)?.[1];
  expect(message).toBeTruthy();
  const handler = calculations.slice(calculations.indexOf("def _check_sowing_date("), calculations.indexOf("# El código oficial"));
  expect(handler).toContain(JSON.stringify(message));
});
