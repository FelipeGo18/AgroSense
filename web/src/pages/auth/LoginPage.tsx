import { useState, useSyncExternalStore, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "@/components/layout/LanguageLink";
import { t } from "@/lib/i18n";
import { ApiError } from "@/api/client";
import { PATHS } from "@/app/paths";
import { FormScene } from "@/components/layout/FormScene";
import { celebrateThen } from "@/components/mascot/reactions";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { useLogin, useSession } from "@/features/auth/session";
import { typedBefore } from "@/lib/firstLoad";
import { afterLoginPath } from "@/features/strategies/entry";
import { useTranslation } from "react-i18next";

const LINK = "font-bold text-oscuro-oliva underline decoration-2 underline-offset-4";

/** Lo que se le dice a la persona según lo que respondió la API. Nunca dice si el usuario existe. */
function message(error: Error) {
  if (!(error instanceof ApiError)) return t("pages.auth.LoginPage.somethingWentWrongTryAgain");
  if (error.status === 401) return t("pages.auth.LoginPage.incorrectUsernameOrPasswordCheckThemAnd");
  return error.message;
}

/** Entrar (HU-162). Diseño: design/pantallas/cuenta.py, `login`. */
export function LoginPage() {
  useTranslation();
  const navigate = useNavigate();
  const { user } = useSession();
  const login = useLogin();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  // Si la página llegó ya dibujada, puede que la persona haya escrito antes de que arrancara la aplicación: se recupera.
  // El primer dibujo coincide con el HTML (campos vacíos); en el siguiente, ya arrancada, se pone lo que había escrito.
  const started = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );
  const [recovered, setRecovered] = useState(false);
  if (started && !recovered) {
    setRecovered(true);
    if (typedBefore("username")) setUsername(typedBefore("username"));
    if (typedBefore("password")) setPassword(typedBefore("password"));
  }

  // Quien ya tiene la sesión abierta no vuelve a entrar. Quien acaba de entrar se queda un instante: la mascota celebra.
  if (user && (login.isIdle || login.isError)) return <Navigate to={PATHS.farm} replace />;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    login.mutate(
      { username, password },
      {
        onSuccess: () => celebrateThen(() => navigate(afterLoginPath())),
      },
    );
  };
  const failed = login.error;

  return (
    <FormScene mood="guide" signs={[t("pages.auth.LoginPage.yourFarmIsWaiting")]} rejected={failed}>
      <title>{t("pages.auth.LoginPage.signInAgrosense")}</title>
      <header>
        <p className="text-[15px] font-bold tracking-wide text-texto-secundario uppercase">{t("login.submit")}</p>
        <h1 className="text-[clamp(1.75rem,2.6vw,2.25rem)]">{t("pages.auth.LoginPage.returnToYourFarm")}</h1>
        {!failed && <p>{t("pages.auth.LoginPage.enterYourUsernameAndPassword")}</p>}
      </header>
      {failed && (
        <Alert>
          <p>{message(failed)}</p>
          {failed instanceof ApiError && failed.status >= 500 && failed.requestId && (
            <p className="font-normal">
              {t("pages.auth.LoginPage.supportCode")} {failed.requestId}
            </p>
          )}
        </Alert>
      )}
      <form onSubmit={submit} noValidate className="flex flex-col gap-3">
        <TextField
          label={t("login.username")}
          name="username"
          placeholder={t("pages.auth.LoginPage.yourUsername")}
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          required
          value={username}
          onChange={(event) => setUsername(event.target.value)}
        />
        <TextField
          label={t("login.password")}
          name="password"
          type="password"
          placeholder={t("pages.auth.LoginPage.yourPassword")}
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        <Button
          type="submit"
          className="mt-1"
          loading={login.isPending}
          loadingText={t("pages.auth.LoginPage.signingIn")}
          disabled={!username.trim() || !password}
        >
          {t("login.submit")}
        </Button>
      </form>
      <p className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
        <span>
          {t("pages.auth.LoginPage.dontHaveAnAccount")}{" "}
          <Link to={PATHS.signup} className={LINK}>
            {t("nav.signup")}
          </Link>
        </span>
        <Link to={PATHS.consult} className={`${LINK} inline-flex min-h-11 items-center`}>
          {t("pages.auth.LoginPage.continueWithoutAnAccount")}
        </Link>
      </p>
      <p className="border-t-2 border-superficie-borde pt-2 text-[15px] leading-snug text-texto-secundario">
        {t("pages.auth.LoginPage.passwordRecoveryIsNotAvailableYetWe")}
      </p>
    </FormScene>
  );
}
