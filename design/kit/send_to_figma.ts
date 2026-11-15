// Envía un archivo SVG al plugin local de Figma por el relé WebSocket (mismo protocolo que el MCP TalkToFigma).
// Uso: bun send_to_figma.ts <canal> <archivo.svg> <x> <y> <nombre> [idDelPadre]
// Con idDelPadre (una sección o un marco), x e y son relativas a él.
const [channel, file, x, y, name, parentId] = process.argv.slice(2);
const svg = await Bun.file(file).text();
const ws = new WebSocket("ws://localhost:3055");
const id = crypto.randomUUID();
const send = (o: unknown) => ws.send(JSON.stringify(o));
const timer = setTimeout(() => { console.error("Tiempo agotado"); process.exit(1); }, 60000);
ws.onopen = () => send({ id: crypto.randomUUID(), type: "join", channel });
let joined = false;
ws.onmessage = (ev) => {
  const data = JSON.parse(String(ev.data));
  if (!joined) {
    joined = true;
    send({ id, type: "message", channel, message: { id, command: "create_svg", params: { svg, x: Number(x), y: Number(y), name, parentId, commandId: id } } });
    return;
  }
  const m = data.message;
  if (m && m.id === id && (m.result || m.error)) {
    console.log(JSON.stringify(m.result ?? { error: m.error }));
    clearTimeout(timer);
    ws.close();
    process.exit(m.error ? 1 : 0);
  }
};
