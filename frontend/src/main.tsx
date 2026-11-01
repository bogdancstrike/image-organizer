import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App as AntApp, ConfigProvider } from "antd";
import "./index.css";
import App from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: "#b8467d",
          colorText: "#4a1d3b",
          colorTextSecondary: "rgba(74,29,59,.6)",
          borderRadius: 12,
          fontFamily: '"Inter Variable", ui-sans-serif, system-ui, sans-serif',
          colorBgElevated: "#fffafc",
          colorBorderSecondary: "#f6dde8",
        },
        components: {
          Drawer: { colorBgElevated: "#fffafc" },
          Segmented: { itemSelectedBg: "#fff", trackBg: "#f8e8ef" },
        },
      }}
    >
      <AntApp>
        <App />
      </AntApp>
    </ConfigProvider>
  </StrictMode>,
);
