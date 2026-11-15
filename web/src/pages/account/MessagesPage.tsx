import { useId, useState, type FormEvent } from "react";
import { Link } from "react-router";
import { ApiError } from "@/api/client";
import { PATHS } from "@/app/paths";
import { FormScene } from "@/components/layout/FormScene";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { SelectField } from "@/components/ui/SelectField";
import { MESSAGE_MAX, useOpenTicket, useTickets, type Ticket } from "@/features/account/tickets";
import { useLots } from "@/features/farm/lots";
import { LINK, RequireSession } from "./AccountShell";

const STATUS: Record<string, string> = { open: "Recibido", in_progress: "En revisión", closed: "Respondido" };
const DATE = new Intl.DateTimeFormat("es-CO", { day: "numeric", month: "long", year: "numeric" });

function message(error: Error) {
  if (!(error instanceof ApiError)) return "No pudimos enviar su mensaje. Intente de nuevo.";
  return error.message;
}

/**
 * Escribir al responsable de los datos (HU-163; `POST /api/v1/me/tickets`). Es el canal de contacto que nombra la
 * política (Ley 1581 de 2012): para preguntar qué se guarda, pedir que se corrija o reportar un problema, sobre la
 * cuenta o sobre un lote. Debajo, los mensajes enviados con su estado.
 */
export function MessagesPage() {
  return <RequireSession>{() => <Messages />}</RequireSession>;
}

function Messages() {
  const open = useOpenTicket();
  const tickets = useTickets();
  const lots = useLots();
  const textId = useId();
  const [text, setText] = useState("");
  const [lotId, setLotId] = useState("");
  const [tried, setTried] = useState(false);
  const [sent, setSent] = useState(false);
  const error = text.trim() ? undefined : "Escriba su mensaje.";
  const names = new Map((lots.data ?? []).map((lot) => [lot.lot_id, lot.name]));

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setTried(true);
    setSent(false);
    if (error) return;
    open.mutate(
      { message: text.trim(), lot_id: lotId || null },
      {
        onSuccess: () => {
          setText("");
          setLotId("");
          setTried(false);
          setSent(true);
        },
      },
    );
  };

  return (
    <FormScene scene="region" mood="idle" rejected={open.error}>
      <title>Escribir al responsable · AgroSense</title>
      <header>
        <p className="text-[15px] font-bold tracking-wide text-texto-secundario uppercase">Mi cuenta</p>
        <h1 className="text-[clamp(1.75rem,2.6vw,2.25rem)]">Escribir al responsable</h1>
        <p>Para preguntar qué datos suyos guardamos, pedir que los corrijamos o reportar un problema.</p>
        <p className="text-[15px] text-texto-secundario">
          Le respondemos aquí mismo, en «Mis mensajes», en máximo 10 días hábiles si es una consulta y 15 si es un reclamo (Ley 1581 de
          2012).
        </p>
      </header>
      {open.error && <Alert>{message(open.error)}</Alert>}
      {sent && (
        <p role="status" className="font-bold">
          Recibimos su mensaje. Abajo puede ver cómo va.
        </p>
      )}
      <form onSubmit={submit} noValidate className="flex flex-col gap-3">
        <div className="flex flex-col gap-1">
          <label htmlFor={textId} className="font-bold">
            Su mensaje
          </label>
          <textarea
            id={textId}
            name="message"
            rows={5}
            maxLength={MESSAGE_MAX}
            value={text}
            onChange={(event) => setText(event.target.value)}
            aria-invalid={tried && error ? true : undefined}
            aria-describedby={`${textId}-note`}
            className={`w-full rounded-sm border-2 bg-superficie-panel px-4 py-3 outline-none focus:border-accion-foco ${
              tried && error ? "border-oscuro-rojo" : "border-superficie-borde"
            }`}
          />
          <p id={`${textId}-note`} className={`text-[14px] ${tried && error ? "text-oscuro-rojo" : "text-texto-secundario"}`}>
            {tried && error ? error : `Hasta ${MESSAGE_MAX} caracteres. No escriba su contraseña.`}
          </p>
        </div>
        {(lots.data?.length ?? 0) > 0 && (
          <SelectField
            label="¿Es sobre un lote?"
            name="lot_id"
            value={lotId}
            onChange={(event) => setLotId(event.target.value)}
            options={[
              { value: "", label: "No, sobre mi cuenta" },
              ...(lots.data ?? []).map((lot) => ({ value: lot.lot_id, label: lot.name })),
            ]}
          />
        )}
        <Button type="submit" className="mt-1" loading={open.isPending} loadingText="Enviando…">
          Enviar mensaje
        </Button>
      </form>

      <section aria-labelledby="mis-mensajes" className="flex flex-col gap-2">
        <h2 id="mis-mensajes" className="text-[20px]">
          Mis mensajes
        </h2>
        {tickets.isPending ? (
          <p role="status">Cargando sus mensajes…</p>
        ) : tickets.isError ? (
          <Alert>No pudimos cargar sus mensajes. Intente de nuevo en un momento.</Alert>
        ) : tickets.data.length === 0 ? (
          <p className="text-texto-secundario">Todavía no nos ha escrito.</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {tickets.data.map((ticket) => (
              <TicketRow key={ticket.ticket_id} ticket={ticket} lot={ticket.lot_id ? names.get(ticket.lot_id) : undefined} />
            ))}
          </ul>
        )}
      </section>
      <Link to={PATHS.account} className={`${LINK} min-h-11 self-start py-2`}>
        Volver a Mi cuenta
      </Link>
    </FormScene>
  );
}

function TicketRow({ ticket, lot }: { ticket: Ticket; lot?: string }) {
  return (
    <li className="flex flex-col gap-1 border-l-4 border-paleta-calabaza pl-3">
      <p className="text-[14px] text-texto-secundario">
        {DATE.format(new Date(ticket.created_at))} · {STATUS[ticket.status] ?? ticket.status}
        {lot ? ` · ${lot}` : ""}
      </p>
      <p className="break-words whitespace-pre-line">{ticket.message}</p>
      {ticket.reply && (
        <div className="mt-1 rounded-sm bg-paleta-niebla px-3 py-2">
          <p className="text-[14px] font-bold">Respuesta{ticket.replied_at ? ` · ${DATE.format(new Date(ticket.replied_at))}` : ""}</p>
          <p className="break-words whitespace-pre-line">{ticket.reply}</p>
        </div>
      )}
    </li>
  );
}
