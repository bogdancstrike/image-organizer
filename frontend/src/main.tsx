import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App";
import { ThemeRoot } from "./theme";
import { LangProvider } from "./i18n";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeRoot>
      <LangProvider>
        <App />
      </LangProvider>
    </ThemeRoot>
  </StrictMode>,
);
