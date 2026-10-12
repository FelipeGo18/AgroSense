import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router";
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
  if (!(error instanceof ApiError)) return "Algo falló. Intente de nuevo.";
  if (error.status === 403) return "La contraseña actual no es correcta. Su sesión sigue abierta.";
  return error.message;
}

/** Cambiar la contraseña (HU-160). Diseño: design/pantallas/cuenta.py, `change_password`. */
export function PasswordPage() {
  const navigate = useNavigate();
  const change = useChangePassword();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [repeat, setRepeat] = useState("");
  const [tried, setTried] = useState(false);

  const errors = {
    current: current ? undefined : "Escriba su contraseña actual.",
    next:
      next.length < PASSWORD_MIN
        ? `La contraseña debe tener al menos ${PASSWORD_MIN} caracteres.`
        : next === current
          ? "La contraseña nueva debe ser distinta de la actual."
          : undefined,
    repeat: repeat === next ? undefined : "Las dos contraseñas nuevas no son iguales.",
  };
  const valid = Object.values(errors).every((error) => error === undefined);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setTried(true);
    if (!valid) return;
    change.mutate(
      { current_password: current, new_password: next },
      { onSuccess: () => navigate(PATHS.account, { state: { notice: "Su contraseña quedó cambiada. Las demás sesiones se cerraron." } }) },
    );
  };

  return (
    <RequireSession>
      {() => (
        <FormScene scene="region" mood="idle">
          <title>Cambiar contraseña · AgroSense</title>
          <header>
            <p className="text-[15px] font-bold tracking-wide text-texto-secundario uppercase">Mi cuenta</p>
            <h1 className="text-[clamp(1.75rem,2.6vw,2.25rem)]">Cambiar contraseña</h1>
            {!change.error && <p>Se cierra su sesión en los demás dispositivos.</p>}
          </header>
          {change.error && <Alert>{message(change.error)}</Alert>}
          <form onSubmit={submit} noValidate className="flex flex-col gap-3">
            <TextField
              label="Contraseña actual"
              name="current_password"
              type="password"
              autoComplete="current-password"
              maxLength={128}
              value={current}
              onChange={(event) => setCurrent(event.target.value)}
              error={tried ? errors.current : undefined}
            />
            <TextField
              label="Contraseña nueva"
              name="new_password"
              type="password"
              autoComplete="new-password"
              maxLength={128}
              value={next}
              onChange={(event) => setNext(event.target.value)}
              hint="Al menos 8 caracteres. No se puede recuperar."
              error={tried ? errors.next : undefined}
            />
            <TextField
              label="Repita la contraseña nueva"
              name="repeat_password"
              type="password"
              autoComplete="new-password"
              maxLength={128}
              value={repeat}
              onChange={(event) => setRepeat(event.target.value)}
              error={tried ? errors.repeat : undefined}
            />
            <Button type="submit" className="mt-1" loading={change.isPending} loadingText="Guardando…">
              Guardar contraseña
            </Button>
          </form>
          <Link to={PATHS.account} className={`${LINK} self-start`}>
            Volver a Mi cuenta
          </Link>
        </FormScene>
      )}
    </RequireSession>
  );
}
