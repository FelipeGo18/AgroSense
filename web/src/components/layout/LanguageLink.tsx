import {
  Link as RouterLink,
  NavLink as RouterNavLink,
  Navigate as RouterNavigate,
  useNavigate as useRouterNavigate,
  useSearchParams as useRouterSearchParams,
  createSearchParams,
  type LinkProps,
  type NavLinkProps,
  type NavigateProps,
  type NavigateFunction,
  type NavigateOptions,
  type To,
  type SetURLSearchParams,
} from "react-router";
import { useCallback } from "react";
import { useTranslation } from "react-i18next";
import { languagePath } from "@/lib/i18n";

function translatePath(to: To, language: string): To {
  if (typeof to === "string") {
    // Las rutas relativas, fragmentos y enlaces externos conservan la semántica del router.
    if (!to.startsWith("/") || to.startsWith("//")) return to;
    return languagePath(to, language);
  }
  const query = new URLSearchParams(to.search);
  if (language === "en") query.set("lang", "en");
  else query.delete("lang");
  return { ...to, search: query.size ? `?${query}` : "" };
}

export function Link({ to, ...props }: LinkProps) {
  const { i18n } = useTranslation();
  return <RouterLink {...props} to={translatePath(to, i18n.resolvedLanguage ?? "es")} />;
}

export function NavLink({ to, ...props }: NavLinkProps) {
  const { i18n } = useTranslation();
  return <RouterNavLink {...props} to={translatePath(to, i18n.resolvedLanguage ?? "es")} />;
}

export function Navigate({ to, ...props }: NavigateProps) {
  const { i18n } = useTranslation();
  return <RouterNavigate {...props} to={translatePath(to, i18n.resolvedLanguage ?? "es")} />;
}

export function useNavigate(): NavigateFunction {
  const navigate = useRouterNavigate();
  const { i18n } = useTranslation();
  const language = i18n.resolvedLanguage ?? "es";
  return useCallback(
    (to: To | number, options?: NavigateOptions) => {
      if (typeof to === "number") return navigate(to);
      return navigate(translatePath(to, language), options);
    },
    [navigate, language],
  ) as NavigateFunction;
}

export function useSearchParams(defaultInit?: Parameters<typeof useRouterSearchParams>[0]) {
  const [params, setParams] = useRouterSearchParams(defaultInit);
  const { i18n } = useTranslation();
  const language = i18n.resolvedLanguage ?? "es";
  const set: SetURLSearchParams = useCallback(
    (next, options) => {
      setParams((previous) => {
        const updated = createSearchParams(typeof next === "function" ? next(previous) : next);
        if (language === "en") updated.set("lang", "en");
        else updated.delete("lang");
        return updated;
      }, options);
    },
    [setParams, language],
  );
  return [params, set] as const;
}
