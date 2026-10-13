import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router/dom";
import "@fontsource/fredoka/600.css";
import "@fontsource/atkinson-hyperlegible/400.css";
import "@fontsource/atkinson-hyperlegible/700.css";
import "@/styles/index.css";
import { initLightMode } from "@/lib/lightMode";
import { createRouter } from "./routes";

// El modo ligero se fija antes de pintar: así nada se anima si la persona pidió quietud.
initLightMode();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RouterProvider router={createRouter()} />
  </StrictMode>,
);
