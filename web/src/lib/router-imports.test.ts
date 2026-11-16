import { ESLint } from "eslint";

it("impide imports que pierden el idioma, incluidos los alias", async () => {
  const eslint = new ESLint();
  for (const name of ["Link", "NavLink", "Navigate", "useNavigate", "useSearchParams"]) {
    const [result] = await eslint.lintText(`import { ${name} as navigation } from "react-router"; export const value = navigation;`, {
      filePath: "src/pages/example.tsx",
    });
    expect(result.messages.some(({ ruleId }) => ruleId === "no-restricted-imports")).toBe(true);
  }
  const [allowed] = await eslint.lintText('import { Link } from "@/components/layout/LanguageLink"; export const value = Link;', {
    filePath: "src/pages/example.tsx",
  });
  expect(allowed.messages.filter(({ ruleId }) => ruleId === "no-restricted-imports")).toEqual([]);
});
