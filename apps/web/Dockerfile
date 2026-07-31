FROM node:22-alpine

RUN corepack enable && corepack prepare pnpm@10.17.1 --activate

WORKDIR /workspace

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/package.json

RUN pnpm install --filter gowild-web...

COPY apps/web apps/web

RUN pnpm --filter gowild-web build

EXPOSE 3000

CMD ["pnpm", "--filter", "gowild-web", "start"]
