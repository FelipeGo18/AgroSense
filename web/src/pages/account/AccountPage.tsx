import { locale, t } from "@/lib/i18n";
import { useTranslation } from "react-i18next";
import { useLayoutEffect, useRef, useState, type FormEvent } from "react";
import { useLocation } from "react-router";
import { Link } from "@/components/layout/LanguageLink";
import region from "../../../../design/paisaje/svg/a3-region.svg?url";
import { ApiError } from "@/api/client";
import { PATHS } from "@/app/paths";
import { SceneAmbient } from "@/components/layout/SceneAmbient";
import { Mascot } from "@/components/mascot/Mascot";
import { SceneLife } from "@/components/mascot/SceneLife";
import { useMascotReactions } from "@/components/mascot/reactions";
import { Alert } from "@/components/ui/Alert";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { TextField } from "@/components/ui/TextField";
import { Toggle } from "@/components/ui/Toggle";
import { useDeleteAccount, useLogout, useUpdateProfile, type Profile } from "@/features/auth/session";
import { useDayPhase } from "@/hooks/useDayPhase";
import { useEntrance } from "@/hooks/useEntrance";
import { useLightMode, useReducedMotion } from "@/hooks/useReducedMotion";
import { useSound } from "@/hooks/useSound";
import { AccountShell, LINK } from "./AccountShell";
import { PrioritiesCard } from "./PrioritiesCard";
import { gsap, motionLoaded } from "@/lib/motion";

const USERNAME = /^[a-z0-9._]{3,30}$/;
const DATE = () => new Intl.DateTimeFormat(locale(), { day: "numeric", month: "long", year: "numeric" });
const date = (iso: string) => DATE().format(new Date(iso));

function Title({ children }: { children: string }) {
  useTranslation();
  return <h2 className="text-[24px]">{children}</h2>;
}

function Row({ label, value }: { label: string; value: string }) {
  useTranslation();
  return (
    <div className="border-b-2 border-superficie-panel-suave pb-2">
      <dt className="text-sm text-texto-secundario">{label}</dt>
      <dd className="text-[20px] font-bold break-words">{value}</dd>
    </div>
  );
}

/** Nombre y usuario: se leen y se editan en la misma tarjeta (HU-160). */
function DataCard({ user }: { user: Profile }) {
  useTranslation();
  const update = useUpdateProfile();
  const [editing, setEditing] = useState(false);
  const [displayName, setDisplayName] = useState(user.display_name);
  const [username, setUsername] = useState(user.username);
  const [tried, setTried] = useState(false);

  const errors = {
    displayName: displayName.trim() ? undefined : t("pages.auth.SignupPage.enterTheNameYouWouldLikeUs"),
    username: USERNAME.test(username) ? undefined : t("pages.auth.SignupPage.3To30CharactersLowercaseUnaccentedLetters"),
  };
  const taken = update.error instanceof ApiError && update.error.status === 409;
  const failed = update.error && !taken ? update.error : null;

  // Al pasar de ver a editar (y de vuelta) la tarjeta cambia de alto con suavidad, en vez de saltar.
  const frame = useRef<HTMLDivElement>(null);
  const before = useRef<{ editing: boolean; height: number } | null>(null);
  const animated = !useReducedMotion();
  useLayoutEffect(() => {
    const card = frame.current?.firstElementChild as HTMLElement | null | undefined;
    if (!card) return;
    const from = before.current;
    const changed = from !== null && from.editing !== editing;
    // Si el motor del movimiento nunca llegó (modo ligero desde el principio), no hay nada que detener.
    if (changed && motionLoaded()) {
      gsap.killTweensOf(card);
      gsap.set(card, { clearProps: "height,overflow" });
    }
    const height = card.offsetHeight;
    if (changed && animated) {
      gsap.fromTo(
        card,
        { height: from.height, overflow: "hidden" },
        { height, duration: 0.3, ease: "power2.out", clearProps: "height,overflow" },
      );
    }
    before.current = { editing, height };
  });

  const open = () => {
    setDisplayName(user.display_name);
    setUsername(user.username);
    setTried(false);
    update.reset();
    setEditing(true);
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    setTried(true);
    if (errors.displayName || errors.username) return;
    update.mutate({ display_name: displayName.trim(), username }, { onSuccess: () => setEditing(false) });
  };

  if (editing) {
    return (
      <div ref={frame} data-enter>
        <Card>
          <Title>{t("pages.account.AccountPage.yourDetails")}</Title>
          {failed && <Alert>{failed instanceof ApiError ? failed.message : t("pages.auth.LoginPage.somethingWentWrongTryAgain")}</Alert>}
          <form onSubmit={submit} noValidate className="flex flex-col gap-3">
            <TextField
              label={t("pages.account.AccountPage.name")}
              name="display_name"
              autoComplete="nickname"
              maxLength={40}
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              error={tried ? errors.displayName : undefined}
            />
            <TextField
              label={t("login.username")}
              name="username"
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              maxLength={30}
              value={username}
              onChange={(event) => setUsername(event.target.value.toLowerCase().replace(/\s/g, ""))}
              hint={t("pages.account.AccountPage.youWillUseThisUsernameToSign")}
              error={taken ? t("pages.account.AccountPage.thatUsernameAlreadyExistsTryAnother") : tried ? errors.username : undefined}
            />
            <div className="mt-1 grid gap-3 sm:grid-cols-2">
              <Button type="submit" loading={update.isPending} loadingText={t("pages.account.AccountPage.saving")}>
                {t("pages.account.AccountPage.save")}
              </Button>
              <Button variant="secondary" onClick={() => setEditing(false)} disabled={update.isPending}>
                {t("pages.account.AccountPage.cancel")}
              </Button>
            </div>
          </form>
        </Card>
      </div>
    );
  }
  return (
    <div ref={frame} data-enter>
      <Card>
        <div className="flex items-center justify-between gap-4">
          <Title>{t("pages.account.AccountPage.yourDetails")}</Title>
          <button type="button" onClick={open} className={`${LINK} min-h-11`}>
            {t("pages.account.AccountPage.edit")}
            <span className="sr-only"> {t("pages.account.AccountPage.myNameAndUsername")}</span>
          </button>
        </div>
        <dl className="flex flex-col gap-3">
          <Row label={t("pages.account.AccountPage.name")} value={user.display_name} />
          <Row label={t("login.username")} value={user.username} />
          <Row label={t("pages.account.AccountPage.accountCreated")} value={date(user.created_at)} />
        </dl>
        <p className="text-[15px] text-texto-secundario">{t("pages.account.AccountPage.youCanChangeYourNameAndUsername")}</p>
      </Card>
    </div>
  );
}

/** Qué se guarda y qué no, en palabras claras, con el consentimiento que aceptó (HU-163). */
function StoredCard({ user }: { user: Profile }) {
  useTranslation();
  return (
    <Card>
      <Title>{t("pages.account.AccountPage.whatWeStoreAboutYou")}</Title>
      <ul className="flex flex-col gap-1">
        <li>{t("pages.account.AccountPage.yourUsernameNameAndPriorities")}</li>
        <li>{t("pages.account.AccountPage.yourPlotsIncludingMapLocationsAndIrrigation")}</li>
        <li>{t("pages.account.AccountPage.yourActiveSessionsAndAccountActivity180")}</li>
        <li>{t("pages.account.AccountPage.yourPlantingsContributeAnonymouslyToMunicipalityTotals")}</li>
        <li>{t("pages.account.AccountPage.weDoNotStoreEmailAddressesPhone")}</li>
      </ul>
      <p>
        {t("pages.account.AccountPage.youAgreedToDataProcessingVersion")} {user.consent_version}
        {t("pages.account.AccountPage.on")} {date(user.consent_at)}.
      </p>
      <Link to={PATHS.dataPolicy} className={`${LINK} inline-flex min-h-11 items-center self-start`}>
        {t("pages.account.AccountPage.readTheDataPrivacyPolicy")}
      </Link>
    </Card>
  );
}

/** Preferencias que viven en este navegador, no en la cuenta. */
function PreferencesCard() {
  useTranslation();
  const [light, setLight] = useLightMode();
  const [sound, setSound] = useSound();
  return (
    <Card bodyClassName="gap-5">
      <Title>{t("pages.account.AccountPage.preferencesForThisDevice")}</Title>
      <Toggle label={t("light.label")} note={t("preferences.noMotion")} checked={light} onChange={setLight} />
      <Toggle label={t("sound.label")} note={t("preferences.soundHint")} checked={sound} onChange={setSound} />
    </Card>
  );
}

function SessionCard({ user }: { user: Profile }) {
  useTranslation();
  const logout = useLogout();
  return (
    <Card>
      <Title>{t("pages.account.AccountPage.sessionAndPassword")}</Title>
      <p>
        {t("pages.account.AccountPage.signedInAs")} {user.username}.
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        <ButtonLink to={PATHS.password} variant="secondary">
          {t("pages.account.AccountPage.changePassword")}
        </ButtonLink>
        <Button
          variant="secondary"
          loading={logout.isPending}
          loadingText={t("pages.account.AccountPage.signingOut")}
          onClick={() => logout.mutate()}
        >
          {t("nav.logout")}
        </Button>
      </div>
    </Card>
  );
}

/** Acceso a «Mi actividad» (HU-178): lo que se hizo con la cuenta, también lo que hizo soporte. */
function ActivityCard() {
  useTranslation();
  return (
    <Card>
      <Title>{t("nav.activity")}</Title>
      <p>{t("pages.account.AccountPage.activityOnYourAccountAndPlotsIncluding")}</p>
      <ButtonLink to={PATHS.activity} variant="secondary" className="self-start">
        {t("pages.account.AccountPage.viewMyActivity")}
      </ButtonLink>
    </Card>
  );
}

/** Borrar la cuenta: dice qué se pierde y pide confirmar con la contraseña. No se puede deshacer (R9). */
function DangerCard({ user }: { user: Profile }) {
  useTranslation();
  const remove = useDeleteAccount();
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [missing, setMissing] = useState(false);
  const toggle = (next: boolean) => {
    setOpen(next);
    // Al cerrar no queda la contraseña escrita ni el error de la vez anterior.
    if (!next) {
      setPassword("");
      setMissing(false);
      remove.reset();
    }
  };
  const confirm = () => {
    if (!password) {
      setMissing(true);
      return;
    }
    remove.mutate({ password });
  };
  return (
    <Card className="border-l-8 border-paleta-rojo">
      <Title>{t("pages.account.AccountPage.deleteMyAccount")}</Title>
      <p>{t("pages.account.AccountPage.yourUsernameSessionsPlotsPlantingSeasonsReports")}</p>
      <Button variant="danger" className="self-start" onClick={() => setOpen(true)}>
        {t("pages.account.AccountPage.deleteMyAccount")}
      </Button>
      <ConfirmDialog
        open={open}
        onOpenChange={toggle}
        title={t("pages.account.AccountPage.deleteYourAccount")}
        cancelLabel={t("pages.account.AccountPage.noGoBack")}
        confirmLabel={t("pages.account.AccountPage.yesDeleteEverything")}
        busy={remove.isPending}
        busyLabel={t("common.deleting")}
        onConfirm={confirm}
      >
        <p>{t("pages.account.AccountPage.allOfThisWillBePermanentlyDeleted")}</p>
        <ul className="flex flex-col gap-1.5">
          {[
            t("pages.account.AccountPage.yourUsernameAndName", { v0: user.username }),
            t("pages.account.AccountPage.yourSessionsOnAllDevices"),
            t("pages.account.AccountPage.yourPlotsAndPlantingSeasons"),
            t("pages.account.AccountPage.yourReportsAndActivityHistory"),
          ].map((item) => (
            <li key={item} className="flex gap-3">
              <span aria-hidden="true" className="mt-1.5 block size-3.5 shrink-0 bg-oscuro-rojo" />
              {item}
            </li>
          ))}
        </ul>
        <p className="font-bold">{t("pages.account.AccountPage.thisCannotBeUndone")}</p>
        <TextField
          label={t("pages.account.AccountPage.yourPasswordToConfirm")}
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => {
            setPassword(event.target.value);
            setMissing(false);
          }}
          error={missing ? t("pages.account.AccountPage.enterYourPasswordToDeleteTheAccount") : undefined}
        />
        {remove.error && (
          <Alert>{remove.error instanceof ApiError ? remove.error.message : t("pages.auth.LoginPage.somethingWentWrongTryAgain")}</Alert>
        )}
      </ConfirmDialog>
    </Card>
  );
}

/** Mi cuenta (HU-160, HU-163). Diseño: design/pantallas/cuenta.py, `profile`. */
export function AccountPage() {
  useTranslation();
  // Al volver de cambiar la contraseña se avisa que quedó guardada.
  const notice = (useLocation().state as { notice?: string } | null)?.notice;
  return <AccountShell>{(user) => <Account user={user} notice={notice} />}</AccountShell>;
}

function Account({ user, notice }: { user: Profile; notice?: string }) {
  useTranslation();
  const page = useEntrance<HTMLDivElement>();
  // La franja tiene la misma vida que el paisaje de los formularios: la hora del día, la mariposa, el viento y una
  // mascota que mira el campo que se edita, se ríe si la tocan y se duerme si nadie hace nada.
  const stage = useRef<HTMLDivElement>(null);
  const { act, poke } = useMascotReactions(stage, null);
  const night = useDayPhase() === "night";
  return (
    <div ref={stage}>
      <title>{t("pages.account.AccountPage.myAccountAgrosense")}</title>
      <div className="relative h-[230px] overflow-hidden md:h-[280px]">
        <img src={region} alt="" aria-hidden="true" className="absolute inset-0 size-full object-cover" />
        <SceneAmbient contained />
        <SceneLife className="relative mx-auto flex h-full max-w-[1440px] items-end justify-between px-3 pb-5 md:px-12 lg:px-24">
          {/* De noche el paisaje se oscurece: el título pasa a claro para que se siga leyendo. */}
          <h1
            className={`text-[clamp(2.25rem,4vw,3rem)] ${
              night ? "text-texto-sobre-oscuro [text-shadow:0_2px_0_rgb(11_18_38/0.7)]" : "[text-shadow:0_2px_0_rgb(255_255_255/0.6)]"
            }`}
          >
            {t("nav.account")}
          </h1>
          <div onPointerDown={poke}>
            <Mascot mood={act ?? "idle"} lively decorative className="block h-auto w-[120px] md:w-[200px]" />
          </div>
        </SceneLife>
      </div>
      <div ref={page} className="mx-auto mt-6 flex max-w-[1440px] flex-col gap-7 px-3 md:px-12 lg:px-24">
        {notice && (
          <p role="status" data-enter className="border-l-8 border-oscuro-oliva bg-superficie-panel px-4 py-3 font-bold">
            {notice}
          </p>
        )}
        <div className="grid grid-cols-1 items-start gap-7 lg:grid-cols-2">
          <div className="flex flex-col gap-7">
            <DataCard user={user} />
            <div data-enter>
              <PrioritiesCard user={user} />
            </div>
            <div data-enter>
              <SessionCard user={user} />
            </div>
          </div>
          <div className="flex flex-col gap-7">
            <div data-enter>
              <StoredCard user={user} />
            </div>
            <div data-enter>
              <PreferencesCard />
            </div>
          </div>
        </div>
        {/* Abajo, lado a lado: ver lo que se hizo con la cuenta y borrarla. */}
        <div className="grid grid-cols-1 items-start gap-7 lg:grid-cols-2">
          <div data-enter>
            <ActivityCard />
          </div>
          <div data-enter>
            <DangerCard user={user} />
          </div>
        </div>
      </div>
    </div>
  );
}
