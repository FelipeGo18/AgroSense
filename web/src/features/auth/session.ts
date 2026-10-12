import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, api, type Schemas } from "@/api/client";

export type Profile = Schemas["Profile"];
export type LoginBody = Schemas["LoginBody"];
export type RegisterBody = Schemas["RegisterBody"];

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
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api<void>("/auth/logout", { method: "POST" }),
    // Pase lo que pase con la petición, en esta pantalla la sesión se da por cerrada y se borra lo que había en memoria.
    onSettled: () => {
      client.clear();
      client.setQueryData(ME, null);
    },
  });
}
