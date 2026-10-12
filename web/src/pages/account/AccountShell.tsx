import { useState, type ReactNode } from "react";
import { Navigate } from "react-router";
import { PATHS } from "@/app/paths";
import { Footer } from "@/components/layout/Footer";
import { TopBar } from "@/components/layout/TopBar";
import { useSession, type Profile } from "@/features/auth/session";

/**
 * Marco de las páginas de la cuenta: barra, contenido y pie. Son páginas con sesión: mientras se averigua quién
 * entró se espera, y quien no tiene sesión va a «Entrar».
 */
export function RequireSession({ children }: { children: (user: Profile) => ReactNode }) {
  const { user, loading } = useSession();
  // Si en esta página hubo sesión y ya no la hay, es que la persona salió: va al inicio. Si nunca la hubo, llegó sin entrar: va a «Entrar».
  const [hadSession, setHadSession] = useState(false);
  if (user && !hadSession) setHadSession(true);
  if (loading) {
    return (
      <p role="status" className="p-8">
        Cargando…
      </p>
    );
  }
  if (!user) return <Navigate to={hadSession ? PATHS.home : PATHS.login} replace />;
  return children(user);
}

/** Marco de las páginas largas de la cuenta (Mi cuenta, Mi actividad): barra, contenido y pie sobre fondo claro. */
export function AccountShell({ children }: { children: (user: Profile) => ReactNode }) {
  return (
    <div className="min-h-svh bg-paleta-niebla">
      <TopBar />
      {/* El espacio de abajo es para los cerros del pie de página. */}
      <main className="pb-40 md:pb-48">
        <RequireSession>{children}</RequireSession>
      </main>
      <Footer />
    </div>
  );
}

export const LINK = "font-bold text-oscuro-oliva underline decoration-2 underline-offset-4";
