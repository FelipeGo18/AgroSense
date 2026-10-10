import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource/fredoka/600.css";
import "@fontsource/atkinson-hyperlegible/400.css";
import "@fontsource/atkinson-hyperlegible/700.css";
import "./styles/index.css";
import { KitPage } from "./kit/KitPage";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <KitPage />
  </StrictMode>,
);
