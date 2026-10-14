/**
 * Si la página está arrancando sobre HTML que ya venía pintado (el que se genera en el build, scripts/prerender.mjs).
 *
 * Mientras dura ese arranque no se anima la entrada de nada: la persona ya está viendo el contenido, y esconderlo
 * para volver a mostrarlo sería un parpadeo. Las entradas vuelven en las navegaciones siguientes.
 */
let starting = false;

export const isFirstLoad = () => starting;

export function markFirstLoad(value: boolean) {
  starting = value;
  if (!value) typed.clear(); // lo escrito antes de arrancar solo vale para ese arranque
}

const typed = new Map<string, string>();

/**
 * Guarda lo que la persona alcanzó a escribir en los campos antes de que arrancara la aplicación (el HTML ya estaba
 * pintado y los campos ya recibían teclas). Se llama justo antes de arrancar: al arrancar, React los deja vacíos.
 */
export function rememberTyped(root: HTMLElement) {
  for (const input of root.querySelectorAll<HTMLInputElement>("input[name]")) {
    if (input.value && input.type !== "checkbox") typed.set(input.name, input.value);
  }
}

/** Lo que había escrito en un campo antes de arrancar; vacío si no había nada o si el arranque ya terminó. */
export const typedBefore = (name: string) => typed.get(name) ?? "";
