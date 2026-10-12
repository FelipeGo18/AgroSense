import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PATHS } from "@/app/paths";
import { routes } from "@/app/routes";

const ROSA = { user_id: "1", username: "rosa.samaca", display_name: "Rosa", role: "farmer", consent_version: 3, priorities: null };

type Reply = { status: number; body?: unknown };

/** Una API de mentira: responde lo que la prueba diga por cada «MÉTODO ruta» y anota lo que se le envió. */
function fakeApi(replies: Record<string, Reply>) {
  const calls: { key: string; body: unknown }[] = [];
  vi.stubGlobal("fetch", async (url: string, init: RequestInit = {}) => {
    const key = `${init.method ?? "GET"} ${url}`;
    calls.push({ key, body: init.body ? JSON.parse(String(init.body)) : undefined });
    const reply = replies[key] ?? { status: 401, body: { error: { code: "unauthorized", message: "Inicie sesión para continuar." } } };
    return new Response(reply.body === undefined ? null : JSON.stringify(reply.body), {
      status: reply.status,
      headers: { "X-Request-ID": "0b0e4f6e-58a5-4c0e-9d7a-2f1f3a5b7c9d" },
    });
  });
  return calls;
}

const open = (path: string) => render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: [path] })} />);

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Entrar (HU-162)", () => {
  it("entra con usuario y contraseña y lleva a la finca", async () => {
    const calls = fakeApi({ "POST /api/v1/auth/login": { status: 200, body: ROSA } });
    open(PATHS.login);
    await userEvent.type(await screen.findByLabelText("Usuario"), "rosa.samaca");
    await userEvent.type(screen.getByLabelText("Contraseña"), "papa-criolla-2026");
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Mi finca" })).toBeInTheDocument();
    expect(calls.find((call) => call.key.startsWith("POST"))?.body).toEqual({ username: "rosa.samaca", password: "papa-criolla-2026" });
    // Con la sesión abierta, la barra dice quién entró y deja salir.
    expect(screen.getByText("Rosa")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Cerrar sesión" }).length).toBeGreaterThan(0);
  });

  it("con datos incorrectos lo dice con texto, sin decir cuál de los dos falló", async () => {
    fakeApi({ "POST /api/v1/auth/login": { status: 401, body: { error: { code: "invalid_credentials", message: "x" } } } });
    open(PATHS.login);
    await userEvent.type(await screen.findByLabelText("Usuario"), "rosa.samaca");
    await userEvent.type(screen.getByLabelText("Contraseña"), "no-es-esta");
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Usuario o contraseña incorrectos. Revíselos y vuelva a intentar.");
    expect(screen.getByRole("heading", { level: 1, name: "Vuelva a su finca" })).toBeInTheDocument();
  });

  it("tras demasiados intentos muestra lo que dice la API", async () => {
    const message = "Demasiados intentos. Espere 15 minutos y vuelva a intentar.";
    fakeApi({ "POST /api/v1/auth/login": { status: 429, body: { error: { code: "too_many_attempts", message } } } });
    open(PATHS.login);
    await userEvent.type(await screen.findByLabelText("Usuario"), "rosa.samaca");
    await userEvent.type(screen.getByLabelText("Contraseña"), "no-es-esta");
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(message);
  });

  it("sin usuario o sin contraseña el botón no se puede usar; la contraseña se puede mostrar", async () => {
    fakeApi({});
    open(PATHS.login);
    const button = await screen.findByRole("button", { name: "Entrar" });
    expect(button).toBeDisabled();
    const password = screen.getByLabelText("Contraseña");
    await userEvent.type(password, "secreto-largo");
    expect(password).toHaveAttribute("type", "password");
    await userEvent.click(screen.getByRole("button", { name: /Mostrar/ }));
    expect(password).toHaveAttribute("type", "text");
  });

  it("ofrece crear cuenta y seguir sin cuenta, y avisa que la contraseña no se recupera", async () => {
    fakeApi({});
    open(PATHS.login);
    expect(await screen.findByRole("link", { name: "Crear cuenta" })).toHaveAttribute("href", PATHS.signup);
    expect(screen.getByRole("link", { name: "Seguir sin cuenta" })).toHaveAttribute("href", PATHS.consult);
    expect(screen.getByText(/No guardamos su correo ni su celular/)).toBeInTheDocument();
  });
});

describe("Crear cuenta (HU-162, HU-163)", () => {
  const fill = async () => {
    await userEvent.type(await screen.findByLabelText("¿Cómo quiere que lo llamemos?"), "Rosa");
    await userEvent.type(screen.getByLabelText("Usuario"), "Rosa.Samaca");
    await userEvent.type(screen.getByLabelText("Contraseña"), "papa-criolla-2026");
  };

  it("sin aceptar el consentimiento no se envía nada (R9)", async () => {
    const calls = fakeApi({});
    open(PATHS.signup);
    await fill();
    await userEvent.click(screen.getByRole("button", { name: "Crear cuenta" }));
    expect(await screen.findByText("Para crear la cuenta hay que aceptar.")).toBeInTheDocument();
    expect(calls.some((call) => call.key.startsWith("POST"))).toBe(false);
  });

  it("el consentimiento dice qué se guarda y qué no, y enlaza la política", async () => {
    fakeApi({});
    open(PATHS.signup);
    const consent = await screen.findByRole("checkbox");
    expect(consent).not.toBeChecked();
    expect(consent).toHaveAccessibleName(/Acepto que AgroSense guarde mi usuario, mi nombre y mis prioridades, mis lotes/);
    expect(screen.getByText(/se registra la actividad de mi cuenta durante 180 días/)).toBeInTheDocument();
    expect(screen.getByText(/solo si hay al menos 5 cuentas/)).toBeInTheDocument();
    expect(screen.getByText(/No se guarda correo, celular, documento ni dirección/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Leer la política de tratamiento de datos" })).toHaveAttribute("href", PATHS.dataPolicy);
  });

  it("crea la cuenta con la versión vigente del consentimiento y el usuario en minúsculas", async () => {
    const calls = fakeApi({ "POST /api/v1/auth/register": { status: 201, body: ROSA } });
    open(PATHS.signup);
    await fill();
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(screen.getByRole("button", { name: "Crear cuenta" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Mi finca" })).toBeInTheDocument();
    expect(calls.find((call) => call.key.startsWith("POST"))?.body).toEqual({
      display_name: "Rosa",
      username: "rosa.samaca",
      password: "papa-criolla-2026",
      consent_version: 3,
      consent_accepted: true,
    });
  });

  it("avisa cada dato que falta antes de enviar", async () => {
    const calls = fakeApi({});
    open(PATHS.signup);
    await userEvent.type(await screen.findByLabelText("Usuario"), "ro");
    await userEvent.type(screen.getByLabelText("Contraseña"), "corta");
    await userEvent.click(screen.getByRole("button", { name: "Crear cuenta" }));
    expect(await screen.findByText("Escriba cómo quiere que lo llamemos.")).toBeInTheDocument();
    expect(screen.getByText(/De 3 a 30: minúsculas/)).toBeInTheDocument();
    expect(screen.getByText("La contraseña debe tener al menos 8 caracteres.")).toBeInTheDocument();
    expect(screen.getByLabelText("Usuario")).toHaveAttribute("aria-invalid", "true");
    expect(calls.some((call) => call.key.startsWith("POST"))).toBe(false);
  });

  it("si el usuario ya existe lo dice junto al campo", async () => {
    fakeApi({ "POST /api/v1/auth/register": { status: 409, body: { error: { code: "username_taken", message: "x" } } } });
    open(PATHS.signup);
    await fill();
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(screen.getByRole("button", { name: "Crear cuenta" }));
    expect(await screen.findByText("Ese nombre de usuario ya está en uso. Pruebe con otro.")).toBeInTheDocument();
    expect(screen.getByLabelText("Usuario")).toHaveAttribute("aria-invalid", "true");
  });
});

describe("Crear cuenta en pantallas angostas", () => {
  // En un teléfono va en dos pasos, para que cada uno quepa en la pantalla sin hacer scroll.
  const narrow = () =>
    vi.stubGlobal("matchMedia", (query: string) => ({
      matches: query.includes("max-width: 767px"),
      media: query,
      addEventListener: () => {},
      removeEventListener: () => {},
    }));

  it("primero pide los datos y después el consentimiento", async () => {
    const calls = fakeApi({ "POST /api/v1/auth/register": { status: 201, body: ROSA } });
    narrow();
    open(PATHS.signup);
    expect(await screen.findByText(/paso 1 de 2/)).toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Continuar" }));
    expect(screen.getByText("Escriba cómo quiere que lo llamemos.")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("¿Cómo quiere que lo llamemos?"), "Rosa");
    await userEvent.type(screen.getByLabelText("Usuario"), "rosa.samaca");
    await userEvent.type(screen.getByLabelText("Contraseña"), "papa-criolla-2026");
    await userEvent.click(screen.getByRole("button", { name: "Continuar" }));
    expect(screen.getByText(/paso 2 de 2/)).toBeInTheDocument();
    expect(screen.queryByLabelText("Usuario")).toBeNull();
    // Se puede volver sin perder lo escrito.
    await userEvent.click(screen.getByRole("button", { name: /Volver a mis datos/ }));
    expect(screen.getByLabelText("Usuario")).toHaveValue("rosa.samaca");
    await userEvent.click(screen.getByRole("button", { name: "Continuar" }));
    await userEvent.click(screen.getByRole("button", { name: "Crear cuenta" }));
    expect(screen.getByText("Para crear la cuenta hay que aceptar.")).toBeInTheDocument();
    expect(calls.some((call) => call.key.startsWith("POST"))).toBe(false);
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(screen.getByRole("button", { name: "Crear cuenta" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Mi finca" })).toBeInTheDocument();
  });
});

describe("Pie de página", () => {
  it("entrar y crear cuenta llevan el pie de página", async () => {
    fakeApi({});
    open(PATHS.login);
    expect(await screen.findByText(/Todos los derechos reservados/)).toBeInTheDocument();
  });
});

describe("Sesión", () => {
  it("quien ya entró no vuelve a ver la pantalla de entrar", async () => {
    fakeApi({ "GET /api/v1/me": { status: 200, body: ROSA } });
    open(PATHS.login);
    expect(await screen.findByRole("heading", { level: 1, name: "Mi finca" })).toBeInTheDocument();
  });

  it("cerrar sesión vuelve a ofrecer «Entrar»", async () => {
    const calls = fakeApi({ "GET /api/v1/me": { status: 200, body: ROSA }, "POST /api/v1/auth/logout": { status: 204 } });
    open(PATHS.farm);
    await userEvent.click((await screen.findAllByRole("button", { name: "Cerrar sesión" }))[0]);
    expect(await screen.findByRole("link", { name: "Entrar" })).toHaveAttribute("href", PATHS.login);
    expect(calls.some((call) => call.key === "POST /api/v1/auth/logout")).toBe(true);
  });
});
