import "@fontsource-variable/inter";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "@fontsource/ibm-plex-mono/600.css";
import "@fontsource/ibm-plex-mono/700.css";
import "./theme/tokens.css";
import "./theme/ui.css";

import React from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { DesignSystemPreview } from "./DesignSystemPreview";

const preview = new URLSearchParams(location.search).has("preview");

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>{preview ? <DesignSystemPreview /> : <App />}</React.StrictMode>,
);
