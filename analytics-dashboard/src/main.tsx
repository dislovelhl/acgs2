/**
 * ACGS-2 Analytics Dashboard Entry Point
 */

import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

// Styles
import "./index.css";
// react-grid-layout requires both CSS files
import "react-grid-layout/css/styles.css";
import "react-resizable/css/styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
