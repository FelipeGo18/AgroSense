import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PATHS } from "@/app/paths";
import { routes } from "@/app/routes";
import type { ActivityItem } from "@/features/auth/session";
import { describe as describeEvent, keptSince, when, who } from "./activity";

const ROSA = {
  user_id: "1",
  username: "rosa.samaca",
  display_name: "Rosa",
  role: "farmer",
  consent_version: 3,
  consent_at: "2026-08-02T13:40:00Z",
  priorities: null,
  created_at: "2026-08-02T13:40:00Z",
};

type Reply = { status: number; body?: unknown };

/** Una API de mentira: responde lo que la prueba diga por cada «MÉTODO ruta» y anota lo que se le envió. */
function fakeApi(replies: Record<string, Reply>) {
  const calls: { key: string; body: unknown }[] = [];
  vi.stubGlobal("fetch", async (url: string, init: RequestInit = {}) => {
    const key = `${init.method ?? "GET"} ${url}`;
    calls.push({ key, body: init.body ? JSON.parse(String(init.body)) : undefined });
    const reply = replies[key] ?? { status: 401, body: { error: { code: "unauthorized", message: "Inicie sesión para continuar." } } };
    return new Response(reply.body === undefined ? null : JSON.stringify(reply.body), { status: reply.status });
  });
  return calls;
}

const ME = { "GET /api/v1/me": { status: 200, body: ROSA } };
const open = (path: string) => render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: [path] })} />);
const card = (title: string) =>
  screen.getByRole("heading", { level: 2, name: title }).closest("div.relative")!.parentElement as HTMLElement;

// Al salir de la cuenta se llega al inicio: se prueba como lo ve quien pide «reducir movimiento» (sin recorrido ni lienzo).
beforeEach(() => {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: query.includes("prefers-reduced-motion"),
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  }));
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  localStorage.clear();
});

describe("Mi cuenta (HU-160, HU-163)", () => {
  it("sin sesión lleva a entrar", async () => {
    fakeApi({});
    open(PATHS.account);
    expect(await screen.findByRole("heading", { level: 1, name: "Vuelva a su finca" })).toBeInTheDocument();
  });

  it("muestra sus datos, lo que se guarda y cuándo aceptó el consentimiento", async () => {
    fakeApi(ME);
    open(PATHS.account);
    expect(await screen.findByRole("heading", { level: 1, name: "Mi cuenta" })).toBeInTheDocument();
    const data = card("Sus datos");
    expect(within(data).getByText("rosa.samaca")).toBeInTheDocument();
    expect(within(data).getByText("2 de agosto de 2026")).toBeInTheDocument();
    expect(screen.getByText(/Aceptó el tratamiento de datos \(versión 3\) el 2 de agosto de 2026/)).toBeInTheDocument();
    expect(screen.getByText("No guardamos correo, celular, documento ni dirección.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ver mi actividad" })).toHaveAttribute("href", PATHS.activity);
    expect(screen.getByRole("link", { name: "Cambiar contraseña" })).toHaveAttribute("href", PATHS.password);
  });

  it("edita el nombre y el usuario y vuelve a mostrarlos", async () => {
    const calls = fakeApi({
      ...ME,
      "PATCH /api/v1/me": { status: 200, body: { ...ROSA, display_name: "Rosa Elvira", username: "rosa.elvira" } },
    });
    open(PATHS.account);
    await userEvent.click(await screen.findByRole("button", { name: /Editar/ }));
    const name = screen.getByLabelText("Nombre");
    await userEvent.clear(name);
    await userEvent.type(name, "Rosa Elvira");
    const username = screen.getByLabelText("Usuario");
    await userEvent.clear(username);
    await userEvent.type(username, "Rosa.Elvira");
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(await within(card("Sus datos")).findByText("rosa.elvira")).toBeInTheDocument();
    expect(calls.find((call) => call.key.startsWith("PATCH"))?.body).toEqual({ display_name: "Rosa Elvira", username: "rosa.elvira" });
  });

  it("si el usuario ya existe lo dice junto al campo y no cierra la edición", async () => {
    fakeApi({ ...ME, "PATCH /api/v1/me": { status: 409, body: { error: { code: "username_taken", message: "x" } } } });
    open(PATHS.account);
    await userEvent.click(await screen.findByRole("button", { name: /Editar/ }));
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(await screen.findByText("Ese usuario ya existe. Pruebe con otro.")).toBeInTheDocument();
    expect(screen.getByLabelText("Usuario")).toHaveAttribute("aria-invalid", "true");
  });

  it("cancelar deja los datos como estaban", async () => {
    const calls = fakeApi(ME);
    open(PATHS.account);
    await userEvent.click(await screen.findByRole("button", { name: /Editar/ }));
    await userEvent.type(screen.getByLabelText("Nombre"), " cambiado");
    await userEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(within(card("Sus datos")).getByText("Rosa")).toBeInTheDocument();
    expect(calls.some((call) => call.key.startsWith("PATCH"))).toBe(false);
  });

  it("el modo ligero se prende y se apaga, se recuerda en el navegador y quita el movimiento", async () => {
    // Un equipo que no pide reducir movimiento: sin el modo ligero, el inicio tendría su recorrido.
    vi.stubGlobal("matchMedia", (query: string) => ({
      matches: false,
      media: query,
      addEventListener: () => {},
      removeEventListener: () => {},
    }));
    fakeApi(ME);
    open(PATHS.account);
    const light = await screen.findByRole("switch", { name: "Modo ligero" });
    expect(light).toHaveAttribute("aria-checked", "false");
    await userEvent.click(light);
    expect(light).toHaveAttribute("aria-checked", "true");
    expect(localStorage.getItem("agrosense:modo-ligero")).toBe("1");
    expect(document.documentElement).toHaveClass("modo-ligero");
    await userEvent.click(light);
    expect(light).toHaveAttribute("aria-checked", "false");
    expect(localStorage.getItem("agrosense:modo-ligero")).toBe("0");
    expect(document.documentElement).not.toHaveClass("modo-ligero");
  });

  it("el sonido se prende y se apaga desde Mi cuenta, igual que con el botón de la barra", async () => {
    fakeApi(ME);
    open(PATHS.account);
    const sound = await screen.findByRole("switch", { name: "Sonido" });
    expect(sound).toHaveAttribute("aria-checked", "false");
    await userEvent.click(sound);
    expect(sound).toHaveAttribute("aria-checked", "true");
    // Los dos controles dicen lo mismo.
    expect(screen.getByRole("button", { name: "Sonido" })).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(sound);
    expect(sound).toHaveAttribute("aria-checked", "false");
  });

  it("borrar la cuenta pide confirmar, dice qué se pierde y solo entonces borra", async () => {
    const calls = fakeApi({ ...ME, "DELETE /api/v1/me": { status: 204 } });
    open(PATHS.account);
    await userEvent.click(await screen.findByRole("button", { name: "Borrar mi cuenta" }));
    const dialog = await screen.findByRole("dialog", { name: "¿Borrar su cuenta?" });
    expect(within(dialog).getByText("Su usuario «rosa.samaca» y su nombre.")).toBeInTheDocument();
    expect(within(dialog).getByText("No se puede deshacer.")).toBeInTheDocument();
    // «No, volver» cierra sin borrar nada.
    await userEvent.click(within(dialog).getByRole("button", { name: "No, volver" }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(calls.some((call) => call.key.startsWith("DELETE"))).toBe(false);
    await userEvent.click(screen.getByRole("button", { name: "Borrar mi cuenta" }));
    await userEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Sí, borrar todo" }));
    expect(await screen.findByRole("heading", { level: 1, name: "AgroSense" })).toBeInTheDocument();
    expect(calls.some((call) => call.key === "DELETE /api/v1/me")).toBe(true);
  });

  it("cerrar sesión desde la barra lleva al inicio y no deja nada de la cuenta en pantalla", async () => {
    // El caso que falló: la barra pasaba a «Entrar», pero la página seguía mostrando los datos de quien salió.
    const calls = fakeApi({ ...ME, "POST /api/v1/auth/logout": { status: 204 } });
    open(PATHS.account);
    await screen.findByRole("heading", { level: 1, name: "Mi cuenta" });
    expect(screen.getAllByText("rosa.samaca").length).toBeGreaterThan(0);
    await userEvent.click(within(screen.getByRole("banner")).getByRole("button", { name: "Cerrar sesión" }));
    expect(await screen.findByRole("heading", { level: 1, name: "AgroSense" })).toBeInTheDocument();
    expect(screen.queryByText("rosa.samaca")).toBeNull();
    expect(screen.queryByRole("heading", { name: "Mi cuenta" })).toBeNull();
    expect(within(screen.getByRole("banner")).getByRole("link", { name: "Entrar" })).toBeInTheDocument();
    expect(calls.some((call) => call.key === "POST /api/v1/auth/logout")).toBe(true);
  });

  it("cerrar sesión lleva al inicio", async () => {
    const calls = fakeApi({ ...ME, "POST /api/v1/auth/logout": { status: 204 } });
    open(PATHS.account);
    await screen.findByRole("heading", { level: 1, name: "Mi cuenta" });
    await userEvent.click(within(screen.getByRole("main")).getByRole("button", { name: "Cerrar sesión" }));
    expect(await screen.findByRole("heading", { level: 1, name: "AgroSense" })).toBeInTheDocument();
    expect(calls.some((call) => call.key === "POST /api/v1/auth/logout")).toBe(true);
  });
});

describe("Cambiar contraseña (HU-160)", () => {
  const fill = async (current: string, next: string, repeat: string) => {
    await userEvent.type(await screen.findByLabelText("Contraseña actual"), current);
    await userEvent.type(screen.getByLabelText("Contraseña nueva"), next);
    await userEvent.type(screen.getByLabelText("Repita la contraseña nueva"), repeat);
    await userEvent.click(screen.getByRole("button", { name: "Guardar contraseña" }));
  };

  it("avisa antes de enviar si es corta, igual a la actual o no coincide", async () => {
    const calls = fakeApi(ME);
    open(PATHS.password);
    await fill("papa-criolla-2026", "corta", "otra");
    expect(screen.getByText("La contraseña debe tener al menos 8 caracteres.")).toBeInTheDocument();
    expect(screen.getByText("Las dos contraseñas nuevas no son iguales.")).toBeInTheDocument();
    await userEvent.clear(screen.getByLabelText("Contraseña nueva"));
    await userEvent.type(screen.getByLabelText("Contraseña nueva"), "papa-criolla-2026");
    expect(screen.getByText("La contraseña nueva debe ser distinta de la actual.")).toBeInTheDocument();
    expect(calls.some((call) => call.key.startsWith("POST"))).toBe(false);
  });

  it("si la actual no es correcta lo dice y aclara que la sesión sigue abierta", async () => {
    fakeApi({ ...ME, "POST /api/v1/me/password": { status: 403, body: { error: { code: "wrong_password", message: "x" } } } });
    open(PATHS.password);
    await fill("no-es-esta", "arveja-verde-2027", "arveja-verde-2027");
    expect(await screen.findByRole("alert")).toHaveTextContent("La contraseña actual no es correcta. Su sesión sigue abierta.");
  });

  it("al cambiarla vuelve a Mi cuenta y lo confirma; no envía la repetición", async () => {
    const calls = fakeApi({ ...ME, "POST /api/v1/me/password": { status: 204 } });
    open(PATHS.password);
    await fill("papa-criolla-2026", "arveja-verde-2027", "arveja-verde-2027");
    expect(await screen.findByRole("heading", { level: 1, name: "Mi cuenta" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Su contraseña quedó cambiada. Las demás sesiones se cerraron.");
    expect(calls.find((call) => call.key.startsWith("POST"))?.body).toEqual({
      current_password: "papa-criolla-2026",
      new_password: "arveja-verde-2027",
    });
  });
});

const event = (changes: Partial<ActivityItem>): ActivityItem => ({
  event_id: crypto.randomUUID(),
  occurred_at: "2026-10-12T15:42:00Z",
  action: "auth.login",
  actor_role: "farmer",
  object_type: "session",
  object_id: null,
  outcome: "ok",
  ticket_id: null,
  details: null,
  ...changes,
});

describe("Mi actividad (HU-178)", () => {
  it("cuenta cada evento en palabras, con quién lo hizo y su resultado", async () => {
    const items = [
      event({ action: "profile.updated", details: { fields: ["display_name", "username"] } }),
      event({ action: "auth.password_changed", outcome: "failed" }),
      event({ action: "admin.lot_deleted", actor_role: "admin", object_type: "lot" }),
      event({ action: "auth.login" }),
    ];
    fakeApi({ ...ME, "GET /api/v1/me/activity?limit=50": { status: 200, body: { items, next_before: null } } });
    open(PATHS.activity);
    const rows = within(await screen.findByRole("list", { name: /Actividad/ })).getAllByRole("listitem");
    expect(rows).toHaveLength(4);
    expect(rows[0]).toHaveTextContent("Editó sus datos");
    expect(rows[0]).toHaveTextContent("Cambió: nombre, usuario");
    expect(rows[1]).toHaveTextContent("Intentó cambiar la contraseña");
    expect(rows[1]).toHaveTextContent("La contraseña actual no era correcta");
    expect(rows[1]).toHaveTextContent("Falló");
    expect(rows[2]).toHaveTextContent("Soporte");
    expect(rows[3]).toHaveTextContent("Entró a su cuenta");
    expect(rows[3]).toHaveTextContent("Hecho");
    expect(screen.queryByRole("button", { name: "Ver más antiguos" })).toBeNull();
  });

  it("«Ver más antiguos» pide la página anterior", async () => {
    const before = "2026-10-01T10:00:00Z";
    const calls = fakeApi({
      ...ME,
      "GET /api/v1/me/activity?limit=50": { status: 200, body: { items: [event({})], next_before: before } },
      [`GET /api/v1/me/activity?limit=50&before=${encodeURIComponent(before)}`]: {
        status: 200,
        body: { items: [event({ action: "auth.registered" })], next_before: null },
      },
    });
    open(PATHS.activity);
    await userEvent.click(await screen.findByRole("button", { name: "Ver más antiguos" }));
    expect(await screen.findByText("Creó su cuenta")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Ver más antiguos" })).toBeNull();
    expect(calls.filter((call) => call.key.includes("/me/activity"))).toHaveLength(2);
  });

  it("sin eventos lo dice, y siempre ofrece cambiar la contraseña si algo no cuadra", async () => {
    fakeApi({ ...ME, "GET /api/v1/me/activity?limit=50": { status: 200, body: { items: [], next_before: null } } });
    open(PATHS.activity);
    expect(await screen.findByText("Todavía no hay actividad en su cuenta.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Cambie su contraseña" })).toHaveAttribute("href", PATHS.password);
  });

  it("pasa cada evento a palabras sin mostrar nunca valores", () => {
    expect(describeEvent(event({ action: "auth.login_failed", outcome: "failed" }))).toEqual({
      what: "Intento de entrar a su cuenta",
      detail: "La contraseña no era correcta",
    });
    expect(describeEvent(event({ action: "algo.nuevo" })).what).toBe("Hubo actividad en su cuenta");
    expect(describeEvent(event({ action: "lot.updated", details: { fields: ["irrigated", "geometry"] } })).detail).toBe(
      "Cambió: riego, contorno en el mapa",
    );
    expect(who(event({ actor_role: "admin" }))).toBe("Soporte");
    expect(who(event({}))).toBe("Usted");
  });

  it("dice «Hoy», «Ayer» o la fecha, y desde cuándo se conserva", () => {
    const now = new Date(2026, 9, 12, 18, 0);
    expect(when(new Date(2026, 9, 12, 10, 42).toISOString(), now)).toBe("Hoy, 10:42");
    expect(when(new Date(2026, 9, 11, 17, 50).toISOString(), now)).toBe("Ayer, 17:50");
    expect(when(new Date(2026, 9, 3, 9, 5).toISOString(), now)).toBe("3 oct, 09:05");
    expect(when(new Date(2025, 11, 24, 8, 0).toISOString(), now)).toBe("24 dic 2025, 08:00");
    expect(keptSince(now)).toBe("15 de abril de 2026");
  });
});
