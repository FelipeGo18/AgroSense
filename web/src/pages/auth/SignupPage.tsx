import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { useId, useRef, useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router";
import { ApiError } from "@/api/client";
import { PATHS } from "@/app/paths";
import { FormScene } from "@/components/layout/FormScene";
import { celebrateThen } from "@/components/mascot/reactions";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { CONSENT_VERSION, useRegister, useSession } from "@/features/auth/session";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { useReducedMotion } from "@/hooks/useReducedMotion";

const LINK = "font-bold text-oscuro-oliva underline decoration-2 underline-offset-4";

/** Las mismas reglas del contrato (specs/02-contratos.md). La API las vuelve a revisar: aquí solo se avisa antes. */
const USERNAME = /^[a-z0-9._]{3,30}$/;
const USERNAME_RULE = "De 3 a 30: minúsculas sin tilde, números, punto o guion bajo.";
const PASSWORD_MIN = 8;

/**
 * Crear cuenta (HU-162) con el consentimiento (HU-163). Diseño: design/pantallas/cuenta.py, `register`.
 *
 * Para que quepa en una pantalla sin hacer scroll: en pantallas anchas va en dos columnas (los datos y el
 * consentimiento); en las angostas, en dos pasos (primero los datos, después el consentimiento).
 */
export function SignupPage() {
  const navigate = useNavigate();
  const consentId = useId();
  const { user } = useSession();
  const register = useRegister();
  const narrow = useMediaQuery("(max-width: 767px)");
  const [step, setStep] = useState<1 | 2>(1);
  const [displayName, setDisplayName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [consent, setConsent] = useState(false);
  // Los avisos de cada campo aparecen cuando la persona ya intentó seguir, no mientras escribe.
  const [tried, setTried] = useState(false);
  const [triedConsent, setTriedConsent] = useState(false);
  // Al cambiar de paso, lo nuevo entra de lado: hacia adelante desde la derecha, de vuelta desde la izquierda.
  const form = useRef<HTMLFormElement>(null);
  const shownStep = useRef(step);
  const animated = !useReducedMotion();
  useGSAP(
    () => {
      const from = shownStep.current;
      shownStep.current = step;
      if (!animated || !narrow || from === step || !form.current) return;
      gsap.from(form.current, {
        x: step > from ? 36 : -36,
        opacity: 0,
        duration: 0.3,
        ease: "power2.out",
        clearProps: "transform,opacity",
      });
    },
    { dependencies: [step] },
  );

  // Quien acaba de crear su cuenta se queda un instante: la mascota celebra.
  if (user && (register.isIdle || register.isError)) return <Navigate to={PATHS.farm} replace />;

  const errors = {
    displayName: displayName.trim() ? undefined : "Escriba cómo quiere que lo llamemos.",
    username: USERNAME.test(username) ? undefined : USERNAME_RULE,
    password: password.length >= PASSWORD_MIN ? undefined : `La contraseña debe tener al menos ${PASSWORD_MIN} caracteres.`,
  };
  const dataValid = Object.values(errors).every((error) => error === undefined);
  const failed = register.error;
  const taken = failed instanceof ApiError && failed.status === 409;
  // En dos pasos solo se ve una parte a la vez; en dos columnas, las dos.
  const showData = !narrow || step === 1;
  const showConsent = !narrow || step === 2;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setTried(true);
    if (!dataValid) {
      setStep(1);
      return;
    }
    if (narrow && step === 1) {
      setStep(2);
      return;
    }
    setTriedConsent(true);
    if (!consent) return;
    register.mutate(
      { display_name: displayName.trim(), username, password, consent_version: CONSENT_VERSION, consent_accepted: true },
      // Si el usuario ya existe, en pantallas angostas se vuelve al paso donde se corrige.
      {
        onSuccess: () => celebrateThen(() => navigate(PATHS.farm)),
        onError: (error) => error instanceof ApiError && error.status === 409 && setStep(1),
      },
    );
  };

  return (
    <FormScene mood="celebrate" signs={["Sus lotes, guardados", "Su historial de siembras"]} wide rejected={failed}>
      <title>Crear cuenta · AgroSense</title>
      <header>
        <p className="text-[15px] font-bold tracking-wide text-texto-secundario uppercase">
          Crear cuenta{narrow && <span> · paso {step} de 2</span>}
        </p>
        {/* En el segundo paso de las pantallas angostas el título es el rótulo de arriba: así cabe el consentimiento entero. */}
        <h1 className={`text-[clamp(1.75rem,2.6vw,2.25rem)] ${narrow && step === 2 ? "sr-only" : ""}`}>Guarde su finca</h1>
        {/* En pantallas angostas cada línea cuenta: la frase de apoyo solo va donde sobra alto. */}
        {!narrow && <p>Solo un nombre, un usuario y una contraseña.</p>}
      </header>
      {failed && !taken && (
        <Alert>
          <p>{failed instanceof ApiError ? failed.message : "Algo falló. Intente de nuevo."}</p>
          {failed instanceof ApiError && failed.status >= 500 && failed.requestId && (
            <p className="font-normal">Código para soporte: {failed.requestId}</p>
          )}
        </Alert>
      )}
      <form ref={form} onSubmit={submit} noValidate className="grid grid-cols-1 gap-x-8 gap-y-3 md:grid-cols-2">
        {showData && (
          <div className="flex flex-col gap-2.5">
            <TextField
              label="¿Cómo quiere que lo llamemos?"
              name="display_name"
              autoComplete="nickname"
              maxLength={40}
              required
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
              required
              value={username}
              // El usuario va siempre en minúsculas: se convierte al escribir para que no haya sorpresas al entrar.
              onChange={(event) => setUsername(event.target.value.toLowerCase().replace(/\s/g, ""))}
              hint={narrow ? undefined : "Con este usuario va a entrar."}
              error={taken ? "Ese nombre de usuario ya está en uso. Pruebe con otro." : tried ? errors.username : undefined}
            />
            <TextField
              label="Contraseña"
              name="password"
              type="password"
              autoComplete="new-password"
              maxLength={128}
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              hint="Al menos 8 caracteres. No se puede recuperar."
              error={tried ? errors.password : undefined}
            />
            {narrow && (
              <Button type="submit" className="mt-1">
                Continuar
              </Button>
            )}
            {!narrow && (
              <p>
                ¿Ya tiene cuenta?{" "}
                <Link to={PATHS.login} className={LINK}>
                  Entrar
                </Link>
              </p>
            )}
          </div>
        )}
        {showConsent && (
          <div className="flex flex-col gap-3">
            {/* Consentimiento (HU-163): qué se guarda y para qué, en primera persona. Sin aceptar no se crea la cuenta (R9). */}
            <div className="flex flex-col gap-1.5 bg-superficie-panel-suave p-3 [clip-path:polygon(12px_0,calc(100%-12px)_0,100%_12px,100%_calc(100%-12px),calc(100%-12px)_100%,12px_100%,0_calc(100%-12px),0_12px)]">
              <div className="flex items-start gap-3">
                <input
                  id={consentId}
                  type="checkbox"
                  checked={consent}
                  onChange={(event) => setConsent(event.target.checked)}
                  aria-invalid={triedConsent && !consent ? true : undefined}
                  aria-describedby={`${consentId}-text`}
                  className="mt-0.5 size-7 shrink-0 accent-accion-primaria"
                />
                <div id={`${consentId}-text`} className="flex flex-col gap-1.5 text-xs leading-snug md:text-[15px]">
                  <label htmlFor={consentId}>
                    Acepto que AgroSense guarde mi usuario, mi nombre y mis prioridades, mis lotes con su ubicación en el mapa, si tienen
                    riego y lo que siembro, para mostrarme mi finca.
                  </label>
                  <p>Soporte puede ver mis lotes para ayudarme, y se registra la actividad de mi cuenta durante 180 días.</p>
                  <p>Lo que siembro se suma, sin mi nombre, a los totales de mi municipio, solo si hay al menos 5 cuentas.</p>
                  <p>No se guarda correo, celular, documento ni dirección. Puedo borrar todo cuando quiera.</p>
                  <Link to={PATHS.dataPolicy} className={`${LINK} inline-flex min-h-11 items-center self-start`}>
                    Leer la política de {narrow ? "" : "tratamiento de "}datos
                  </Link>
                </div>
              </div>
              {triedConsent && !consent && <p className="text-[15px] font-bold text-oscuro-rojo">Para crear la cuenta hay que aceptar.</p>}
            </div>
            <Button type="submit" loading={register.isPending} loadingText="Creando su cuenta…">
              Crear cuenta
            </Button>
          </div>
        )}
      </form>
      {narrow && step === 1 && (
        <p>
          ¿Ya tiene cuenta?{" "}
          <Link to={PATHS.login} className={LINK}>
            Entrar
          </Link>
        </p>
      )}
      {narrow && step === 2 && (
        <button type="button" onClick={() => setStep(1)} className={`${LINK} min-h-11 self-start`}>
          <span aria-hidden="true">← </span>Volver a mis datos
        </button>
      )}
    </FormScene>
  );
}
