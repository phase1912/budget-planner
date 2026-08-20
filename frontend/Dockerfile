# Frontend dev image: installs dependencies with npm and runs the Vite dev
# server. docker-compose.yml bind-mounts the source over /app, so editing a
# file on the host hot-reloads without rebuilding the image (F0.4.1).

FROM node:22-alpine

WORKDIR /app

# Dependencies first so the layer is cached until package*.json change.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173

# node_modules is a named volume (see docker-compose.yml), so it can still
# hold whatever was installed the last time the image was built. `npm ci`
# again at startup — fast and a no-op when the lockfile hasn't changed —
# keeps it current with the bind-mounted package-lock.json instead of
# silently shadowing a dependency added since the volume was first
# populated. --host so the dev server accepts connections from outside the
# container, not just localhost inside it.
CMD ["sh", "-c", "npm ci && npm run dev -- --host 0.0.0.0"]
