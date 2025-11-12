import React from "react";
import ReactDOM from "react-dom/client";
import Chat from "./components/Chat";

const rootEl = document.getElementById("root")!;
ReactDOM.createRoot(rootEl).render(
  <React.StrictMode>
    <Chat />
  </React.StrictMode>
);

