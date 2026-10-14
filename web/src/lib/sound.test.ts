import { afterEach, describe, expect, it, vi } from "vitest";

/** Un contexto de audio de mentira que anota qué nodo se conecta a la salida y cuándo se desconecta. */
function fakeAudio() {
  const destination = { name: "salida" };
  const outputs: { disconnect: ReturnType<typeof vi.fn> }[] = [];
  const param = () => ({ value: 0, setValueAtTime: vi.fn(), linearRampToValueAtTime: vi.fn(), exponentialRampToValueAtTime: vi.fn() });
  class FakeAudioContext {
    state = "running";
    currentTime = 0;
    sampleRate = 8000;
    destination = destination;
    resume = () => Promise.resolve();
    createGain() {
      const node = {
        gain: param(),
        disconnect: vi.fn(),
        connect: (target: unknown) => {
          if (target === destination) outputs.push(node);
          return target;
        },
      };
      return node;
    }
    createOscillator() {
      return { type: "sine", frequency: param(), connect: (target: unknown) => target, start: vi.fn(), stop: vi.fn() };
    }
  }
  vi.stubGlobal("AudioContext", FakeAudioContext);
  return outputs;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.resetModules();
  localStorage.clear();
});

describe("Sonido", () => {
  it("al quitarlo calla de inmediato, también las notas que ya estaban programadas", async () => {
    const outputs = fakeAudio();
    const { setSoundEnabled, soundEnabled } = await import("./sound");
    setSoundEnabled(true);
    await Promise.resolve(); // el navegador deja sonar: suena el efecto de prender y arranca la música
    await Promise.resolve();
    expect(outputs).toHaveLength(1);
    expect(outputs[0].disconnect).not.toHaveBeenCalled();

    setSoundEnabled(false);
    expect(soundEnabled()).toBe(false);
    // Todo pasaba por una sola salida, y se desconectó: nada de lo programado llega a sonar.
    expect(outputs[0].disconnect).toHaveBeenCalledTimes(1);
  });

  it("al volver a ponerlo usa una salida nueva: lo que se calló no vuelve a sonar", async () => {
    const outputs = fakeAudio();
    const { setSoundEnabled } = await import("./sound");
    setSoundEnabled(true);
    await Promise.resolve();
    await Promise.resolve();
    setSoundEnabled(false);
    setSoundEnabled(true);
    await Promise.resolve();
    await Promise.resolve();
    expect(outputs).toHaveLength(2);
    expect(outputs[1].disconnect).not.toHaveBeenCalled();
  });
});
