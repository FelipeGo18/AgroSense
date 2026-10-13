import { useState, useSyncExternalStore, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router";
import { ApiError } from "@/api/client";
import { PATHS } from "@/app/paths";
import { FormScene } from "@/components/layout/FormScene";
import { celebrateThen } from "@/components/mascot/reactions";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { useLogin, useSession } from "@/features/auth/session";
import { typedBefore } from "@/lib/firstLoad";

const LINK = "font-bold text-oscuro-oliva underline decoration-2 underline-offset-4";

/** Lo que se le dice a la persona según lo que respondió la API. Nunca dice si el usuario existe. */
function message(error: Error) {
  if (!(error instanceof ApiError)) return "Algo falló. Intente de nuevo.";
  if (error.status === 401) return "Usuario o contraseña incorrectos. Revíselos y vuelva a intentar.";
  return error.message;
}

/** Entrar (HU-162). Diseño: design/pantallas/cuenta.py, `login`. */
export function LoginPage() {
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
    login.mutate({ username, password }, { onSuccess: () => celebrateThen(() => navigate(PATHS.farm)) });
  };
  const failed = login.error;

  return (
    <FormScene mood="guide" signs={["Su finca lo espera"]} rejected={failed}>
      <title>Entrar · AgroSense</title>
      <header>
        <p className="text-[15px] font-bold tracking-wide text-texto-secundario uppercase">Entrar</p>
        <h1 className="text-[clamp(1.75rem,2.6vw,2.25rem)]">Vuelva a su finca</h1>
        {!failed && <p>Entre con su usuario y contraseña.</p>}
      </header>
      {failed && (
        <Alert>
          <p>{message(failed)}</p>
          {failed instanceof ApiError && failed.status >= 500 && failed.requestId && (
            <p className="font-normal">Código para soporte: {failed.requestId}</p>
          )}
        </Alert>
      )}
      <form onSubmit={submit} noValidate className="flex flex-col gap-3">
        <TextField
          label="Usuario"
          name="username"
          placeholder="Su usuario"
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          required
          value={username}
          onChange={(event) => setUsername(event.target.value)}
        />
        <TextField
          label="Contraseña"
          name="password"
          type="password"
          placeholder="Su contraseña"
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        <Button type="submit" className="mt-1" loading={login.isPending} loadingText="Entrando…" disabled={!username.trim() || !password}>
          Entrar
        </Button>
      </form>
      <p className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
        <span>
          ¿No tiene cuenta?{" "}
          <Link to={PATHS.signup} className={LINK}>
            Crear cuenta
          </Link>
        </span>
        <Link to={PATHS.consult} className={`${LINK} inline-flex min-h-11 items-center`}>
          Seguir sin cuenta
        </Link>
      </p>
      <p className="border-t-2 border-superficie-borde pt-2 text-[15px] leading-snug text-texto-secundario">
        Si olvida su contraseña, por ahora no se puede recuperar. No guardamos su correo ni su celular.
      </p>
    </FormScene>
  );
}
