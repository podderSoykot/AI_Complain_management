import { defineConfig } from "vite";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.html"),
        "list-user": resolve(__dirname, "list-user.html"),
        "list-ticket": resolve(__dirname, "list-ticket.html"),
        "create-user": resolve(__dirname, "create-user.html"),
        "my-assigned-tickets": resolve(__dirname, "my-assigned-tickets.html"),
      },
    },
  },
});
