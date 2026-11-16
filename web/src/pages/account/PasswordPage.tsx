import { t } from "@/lib/i18n";
import { useTranslation } from "react-i18next";
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "@/components/layout/LanguageLink";
import { ApiError } from "@/api/client";
import { PATHS } from "@/app/paths";
import { FormScene } from "@/components/layout/FormScene";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { useChangePassword } from "@/features/auth/session";
import { LINK, RequireSession } from "./AccountShell";

const PASSWORD_MIN = 8;

/** Lo que se le dice a la persona según lo que respondió la API. */
function message(error: Error) {
  if (!(error instanceof ApiError)) return t("pages.auth.LoginPage.somethingWentWrongTryAgain");
  if (error.status === 403) return t("pages.account.PasswordPage.theCurrentPasswordIsIncorrectYourSession");
  return error.message;
}

/** Cambiar la contraseña (HU-160). Diseño: design/pantallas/cuenta.py, `change_password`. */
export function PasswordPage() {
  useTranslation();
  const navigate = useNavigate();
  const change = useChangePassword();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [repeat, setRepeat] = useState("");
  const [tried, setTried] = useState(false);

  const errors = {
    current: current ? undefined : t("pages.account.PasswordPage.enterYourCurrentPassword"),
    next:
      next.length < PASSWORD_MIN
        ? t("pages.auth.SignupPage.thePasswordMustContainAtLeastCharacters", { v0: PASSWORD_MIN })
        : next === current
          ? t("pages.account.PasswordPage.theNewPasswordMustDifferFromThe")
          : undefined,
    repeat: repeat === next ? undefined : t("pages.account.PasswordPage.theNewPasswordsDoNotMatch"),
  };
  const valid = Object.values(errors).every((error) => error === undefined);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setTried(true);
    if (!valid) return;
    change.mutate(
      { current_password: current, new_password: next },
      {
        onSuccess: () =>
          navigate(PATHS.account, { state: { notice: t("pages.account.PasswordPage.yourPasswordHasBeenChangedOtherSessions") } }),
      },
    );
  };

  return (
    <RequireSession>
      {() => (
        <FormScene scene="region" mood="idle" rejected={change.error}>
          <title>{t("pages.account.PasswordPage.changePasswordAgrosense")}</title>
          <header>
            <p className="text-[15px] font-bold tracking-wide text-texto-secundario uppercase">{t("nav.account")}</p>
            <h1 className="text-[clamp(1.75rem,2.6vw,2.25rem)]">{t("pages.account.AccountPage.changePassword")}</h1>
            {/* En pantallas angostas cada línea cuenta: la frase de apoyo solo va donde sobra alto. */}
            {!change.error && <p className="hidden md:block">{t("pages.account.PasswordPage.yourSessionsOnOtherDevicesWillBe")}</p>}
          </header>
          {change.error && <Alert>{message(change.error)}</Alert>}
          <form onSubmit={submit} noValidate className="flex flex-col gap-3">
            <TextField
              label={t("pages.account.PasswordPage.currentPassword")}
              name="current_password"
              type="password"
              autoComplete="current-password"
              maxLength={128}
              value={current}
              onChange={(event) => setCurrent(event.target.value)}
              error={tried ? errors.current : undefined}
            />
            <TextField
              label={t("pages.account.PasswordPage.newPassword")}
              name="new_password"
              type="password"
              autoComplete="new-password"
              maxLength={128}
              value={next}
              onChange={(event) => setNext(event.target.value)}
              hint={t("pages.auth.SignupPage.atLeast8CharactersPasswordRecoveryIs")}
              error={tried ? errors.next : undefined}
            />
            <TextField
              label={t("pages.account.PasswordPage.repeatTheNewPassword")}
              name="repeat_password"
              type="password"
              autoComplete="new-password"
              maxLength={128}
              value={repeat}
              onChange={(event) => setRepeat(event.target.value)}
              error={tried ? errors.repeat : undefined}
            />
            <Button type="submit" className="mt-1" loading={change.isPending} loadingText={t("pages.account.AccountPage.saving")}>
              {t("pages.account.PasswordPage.savePassword")}
            </Button>
          </form>
          <Link to={PATHS.account} className={`${LINK} min-h-11 self-start py-2`}>
            {t("pages.account.PasswordPage.backToMyAccount")}
          </Link>
        </FormScene>
      )}
    </RequireSession>
  );
}
