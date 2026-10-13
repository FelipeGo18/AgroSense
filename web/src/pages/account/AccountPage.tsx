import gsap from "gsap";
import { useLayoutEffect, useRef, useState, type FormEvent } from "react";
import { Link, useLocation } from "react-router";
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

const USERNAME = /^[a-z0-9._]{3,30}$/;
const DATE = new Intl.DateTimeFormat("es-CO", { day: "numeric", month: "long", year: "numeric" });
const date = (iso: string) => DATE.format(new Date(iso));

function Title({ children }: { children: string }) {
  return <h2 className="text-[24px]">{children}</h2>;
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-b-2 border-superficie-panel-suave pb-2">
      <dt className="text-sm text-texto-secundario">{label}</dt>
      <dd className="text-[20px] font-bold break-words">{value}</dd>
    </div>
  );
}

/** Nombre y usuario: se leen y se editan en la misma tarjeta (HU-160). */
function DataCard({ user }: { user: Profile }) {
  const update = useUpdateProfile();
  const [editing, setEditing] = useState(false);
  const [displayName, setDisplayName] = useState(user.display_name);
  const [username, setUsername] = useState(user.username);
  const [tried, setTried] = useState(false);

  const errors = {
    displayName: displayName.trim() ? undefined : "Escriba cómo quiere que lo llamemos.",
    username: USERNAME.test(username) ? undefined : "De 3 a 30: minúsculas sin tilde, números, punto o guion bajo.",
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
    if (changed) {
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
          <Title>Sus datos</Title>
          {failed && <Alert>{failed instanceof ApiError ? failed.message : "Algo falló. Intente de nuevo."}</Alert>}
          <form onSubmit={submit} noValidate className="flex flex-col gap-3">
            <TextField
              label="Nombre"
              name="display_name"
              autoComplete="nickname"
              maxLength={40}
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              error={tried ? errors.displayName : undefined}
            />
            <TextField
              label="Usuario"
              name="username"
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              maxLength={30}
              value={username}
              onChange={(event) => setUsername(event.target.value.toLowerCase().replace(/\s/g, ""))}
              hint="Con este usuario va a entrar. Cambiarlo no cierra su sesión."
              error={taken ? "Ese usuario ya existe. Pruebe con otro." : tried ? errors.username : undefined}
            />
            <div className="mt-1 grid gap-3 sm:grid-cols-2">
              <Button type="submit" loading={update.isPending} loadingText="Guardando…">
                Guardar
              </Button>
              <Button variant="secondary" onClick={() => setEditing(false)} disabled={update.isPending}>
                Cancelar
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
          <Title>Sus datos</Title>
          <button type="button" onClick={open} className={`${LINK} min-h-11`}>
            Editar<span className="sr-only"> mi nombre y mi usuario</span>
          </button>
        </div>
        <dl className="flex flex-col gap-3">
          <Row label="Nombre" value={user.display_name} />
          <Row label="Usuario" value={user.username} />
          <Row label="Cuenta creada" value={date(user.created_at)} />
        </dl>
        <p className="text-[15px] text-texto-secundario">Puede cambiar su nombre y su usuario cuando quiera.</p>
      </Card>
    </div>
  );
}

/** Qué se guarda y qué no, en palabras claras, con el consentimiento que aceptó (HU-163). */
function StoredCard({ user }: { user: Profile }) {
  return (
    <Card>
      <Title>Lo que guardamos de usted</Title>
      <ul className="flex flex-col gap-1">
        <li>Su usuario, su nombre y sus prioridades.</li>
        <li>Sus lotes, con su ubicación en el mapa y si tienen riego, y sus temporadas de siembra.</li>
        <li>Sus sesiones abiertas y la actividad de su cuenta (180 días).</li>
        <li>Sus siembras cuentan, sin su nombre, en los totales del municipio.</li>
        <li>No guardamos correo, celular, documento ni dirección.</li>
      </ul>
      <p>
        Aceptó el tratamiento de datos (versión {user.consent_version}) el {date(user.consent_at)}.
      </p>
      <Link to={PATHS.dataPolicy} className={`${LINK} self-start`}>
        Leer la política de tratamiento de datos
      </Link>
    </Card>
  );
}

/** Preferencias que viven en este navegador, no en la cuenta. */
function PreferencesCard() {
  const [light, setLight] = useLightMode();
  const [sound, setSound] = useSound();
  return (
    <Card bodyClassName="gap-5">
      <Title>Preferencias de este dispositivo</Title>
      <Toggle label="Modo ligero" note="Sin animaciones, recorridos ni movimiento." checked={light} onChange={setLight} />
      <Toggle label="Sonido" note="Música y efectos. Empieza apagado." checked={sound} onChange={setSound} />
    </Card>
  );
}

function SessionCard({ user }: { user: Profile }) {
  const logout = useLogout();
  return (
    <Card>
      <Title>Sesión y contraseña</Title>
      <p>Entró como {user.username}.</p>
      <div className="grid gap-3 sm:grid-cols-2">
        <ButtonLink to={PATHS.password} variant="secondary">
          Cambiar contraseña
        </ButtonLink>
        <Button variant="secondary" loading={logout.isPending} loadingText="Cerrando…" onClick={() => logout.mutate()}>
          Cerrar sesión
        </Button>
      </div>
    </Card>
  );
}

/** Acceso a «Mi actividad» (HU-178): lo que se hizo con la cuenta, también lo que hizo soporte. */
function ActivityCard() {
  return (
    <Card>
      <Title>Mi actividad</Title>
      <p>Lo que se hizo con su cuenta y sus lotes, también lo que hizo soporte. Se guarda 180 días.</p>
      <ButtonLink to={PATHS.activity} variant="secondary" className="self-start">
        Ver mi actividad
      </ButtonLink>
    </Card>
  );
}

/** Borrar la cuenta: dice qué se pierde y pide confirmar. No se puede deshacer (R9). */
function DangerCard({ user }: { user: Profile }) {
  const remove = useDeleteAccount();
  const [open, setOpen] = useState(false);
  return (
    <Card className="border-l-8 border-paleta-rojo">
      <Title>Borrar mi cuenta</Title>
      <p>
        Se borran su usuario, sus sesiones, sus lotes, sus temporadas, sus reportes y el registro de su actividad. No se puede deshacer.
      </p>
      <Button variant="danger" className="self-start" onClick={() => setOpen(true)}>
        Borrar mi cuenta
      </Button>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        title="¿Borrar su cuenta?"
        cancelLabel="No, volver"
        confirmLabel="Sí, borrar todo"
        busy={remove.isPending}
        busyLabel="Borrando…"
        onConfirm={() => remove.mutate()}
      >
        <p>Se va a borrar todo esto, para siempre:</p>
        <ul className="flex flex-col gap-1.5">
          {[
            `Su usuario «${user.username}» y su nombre.`,
            "Sus sesiones en todos los dispositivos.",
            "Sus lotes y sus temporadas de siembra.",
            "Sus reportes y el registro de su actividad.",
          ].map((item) => (
            <li key={item} className="flex gap-3">
              <span aria-hidden="true" className="mt-1.5 block size-3.5 shrink-0 bg-oscuro-rojo" />
              {item}
            </li>
          ))}
        </ul>
        <p className="font-bold">No se puede deshacer.</p>
        {remove.error && <Alert>{remove.error instanceof ApiError ? remove.error.message : "Algo falló. Intente de nuevo."}</Alert>}
      </ConfirmDialog>
    </Card>
  );
}

/** Mi cuenta (HU-160, HU-163). Diseño: design/pantallas/cuenta.py, `profile`. */
export function AccountPage() {
  // Al volver de cambiar la contraseña se avisa que quedó guardada.
  const notice = (useLocation().state as { notice?: string } | null)?.notice;
  return <AccountShell>{(user) => <Account user={user} notice={notice} />}</AccountShell>;
}

function Account({ user, notice }: { user: Profile; notice?: string }) {
  const page = useEntrance<HTMLDivElement>();
  // La franja tiene la misma vida que el paisaje de los formularios: la hora del día, la mariposa, el viento y una
  // mascota que mira el campo que se edita, se ríe si la tocan y se duerme si nadie hace nada.
  const stage = useRef<HTMLDivElement>(null);
  const { act, poke } = useMascotReactions(stage, null);
  const night = useDayPhase() === "night";
  return (
    <div ref={stage}>
      <title>Mi cuenta · AgroSense</title>
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
            Mi cuenta
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
