import ts from "typescript";
import en from "@/locales/en.json";

const files = import.meta.glob<string>("../**/*.{ts,tsx}", { query: "?raw", import: "default", eager: true });
const labels = new Set(["aria-label", "title", "placeholder", "label", "loadingText", "legend", "description", "alt"]);
const names = new Set(["AgroSense", "· AgroSense", ", Boyacá"]);

it("ninguna pantalla deja texto fijo en JSX ni usa claves de traducción inexistentes (HU-233)", () => {
  const missing: string[] = [];
  for (const [path, text] of Object.entries(files)) {
    if (/\.test\.|schema\.d\.ts$/.test(path)) continue;
    const source = ts.createSourceFile(path, text, ts.ScriptTarget.Latest, true);
    const report = (node: ts.Node, value: string) =>
      missing.push(`${path}:${source.getLineAndCharacterOfPosition(node.getStart(source)).line + 1}: ${value}`);
    const visit = (node: ts.Node) => {
      if (ts.isJsxText(node)) {
        const value = node.text.trim().replace(/\s+/g, " ");
        if (/\p{L}/u.test(value) && !names.has(value)) report(node, value);
      }
      if (ts.isJsxAttribute(node) && labels.has(node.name.getText(source)) && node.initializer && ts.isStringLiteral(node.initializer)) {
        if (/\p{L}/u.test(node.initializer.text)) report(node, node.initializer.text);
      }
      if (ts.isCallExpression(node) && (node.expression.getText(source) === "t" || node.expression.getText(source) === "i18n.t")) {
        const key = node.arguments[0];
        if (key && ts.isStringLiteral(key) && !Object.hasOwn(en, key.text)) report(node, `missing key: ${key.text}`);
      }
      ts.forEachChild(node, visit);
    };
    visit(source);
  }
  expect(missing).toEqual([]);
});
