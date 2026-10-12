import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { ApiError, api, type Schemas } from "@/api/client";
import { PATHS } from "@/app/paths";

export type Profile = Schemas["Profile"];
export type LoginBody = Schemas["LoginBody"];
export type RegisterBody = Schemas["RegisterBody"];
export type ProfilePatch = Schemas["ProfilePatch"];
export type PasswordBody = Schemas["PasswordBody"];
export type ActivityItem = Schemas["ActivityItem"];
export type ActivityPage = Schemas["ActivityPage"];

/** Versión vigente del consentimiento (HU-163). La API rechaza cualquier otra. */
export const CONSENT_VERSION = 3;

const ME = ["me"] as const;

/**
 * Quién tiene la sesión abierta: su perfil, o `null` si no hay sesión. La sesión vive en una cookie que el
 * JavaScript no puede leer, así que la única forma de saberlo es preguntarle a la API.
 */
export function useSession() {
  const query = useQuery({
    queryKey: ME,
    queryFn: async () => {
      try {
        return await api<Profile>("/me");
      } catch (error) {
        // Sin sesión, sin conexión con la API o con las cuentas apagadas (503): la web sigue funcionando en modo sin cuenta.
        if (error instanceof ApiError && [401, 503, 0].includes(error.status)) return null;
        throw error;
      }
    },
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
  return { user: query.data ?? null, loading: query.isPending };
}

/**
 * Lo que pasa al salir (cerrar sesión o borrar la cuenta), desde cualquier página:
 * 1. La sesión queda en «nadie». Se actualiza, no se quita: así la barra y todo lo que la mira se entera en el acto.
 *    (Con `client.clear()` quedaban mirando una consulta que ya no existía y seguían mostrando a quien acababa de salir.)
 * 2. Se borra de la memoria lo que era de esa persona: su actividad y lo que venga después.
 * 3. Se va al inicio.
 */
function useLeave() {
  const client = useQueryClient();
  const navigate = useNavigate();
  return () => {
    client.setQueryData(ME, null);
    client.removeQueries({ predicate: (query) => query.queryKey.length !== ME.length || query.queryKey[0] !== ME[0] });
    void navigate(PATHS.home);
  };
}

export function useLogin() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: LoginBody) => api<Profile>("/auth/login", { body }),
    onSuccess: (profile) => client.setQueryData(ME, profile),
  });
}

export function useRegister() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: RegisterBody) => api<Profile>("/auth/register", { body }),
    onSuccess: (profile) => client.setQueryData(ME, profile),
  });
}

export function useLogout() {
  const leave = useLeave();
  return useMutation({
    mutationFn: () => api<void>("/auth/logout", { method: "POST" }),
    // Pase lo que pase con la petición, en esta pantalla la sesión se da por cerrada.
    onSettled: leave,
  });
}

export function useUpdateProfile() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: ProfilePatch) => api<Profile>("/me", { method: "PATCH", body }),
    onSuccess: (profile) => {
      client.setQueryData(ME, profile);
      // Editar el perfil deja un evento: «Mi actividad» se vuelve a pedir la próxima vez.
      void client.invalidateQueries({ queryKey: ACTIVITY });
    },
  });
}

export function useChangePassword() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: PasswordBody) => api<void>("/me/password", { body }),
    onSettled: () => void client.invalidateQueries({ queryKey: ACTIVITY }),
  });
}

export function useDeleteAccount() {
  const leave = useLeave();
  return useMutation({
    mutationFn: () => api<void>("/me", { method: "DELETE" }),
    onSuccess: leave,
  });
}

const ACTIVITY = ["me", "activity"] as const;
/** Cuántos eventos trae cada página de «Mi actividad» (el tope de la API). */
export const ACTIVITY_PAGE = 50;

/** Mi actividad, de lo más reciente a lo más antiguo. Cada página pide la anterior con `before`. */
export function useActivity() {
  return useInfiniteQuery({
    queryKey: ACTIVITY,
    queryFn: ({ pageParam }) =>
      api<ActivityPage>(`/me/activity?limit=${ACTIVITY_PAGE}${pageParam ? `&before=${encodeURIComponent(pageParam)}` : ""}`),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next_before ?? null,
  });
}
