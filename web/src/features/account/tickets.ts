import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Schemas } from "@/api/client";

/** Un mensaje al responsable de los datos (HU-163, HU-170): `POST` y `GET /api/v1/me/tickets`. */
export type Ticket = Schemas["TicketOut"];
export type TicketCreate = Schemas["TicketCreate"];

const TICKETS = ["me", "tickets"] as const;
export const MESSAGE_MAX = 2000;

/** Los mensajes de quien tiene la sesión, del más reciente al más antiguo. */
export function useTickets() {
  return useQuery({ queryKey: TICKETS, queryFn: () => api<Ticket[]>("/me/tickets"), retry: false });
}

export function useOpenTicket() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: TicketCreate) => api<Ticket>("/me/tickets", { body }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: TICKETS });
      void client.invalidateQueries({ queryKey: ["me", "activity"] });
    },
  });
}
