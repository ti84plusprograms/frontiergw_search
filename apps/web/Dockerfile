FROM node:22-alpine

WORKDIR /workspace
RUN corepack enable

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/package.json
RUN pnpm install --frozen-lockfile --filter gowild-web...

COPY apps/web ./apps/web
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ARG NEXT_PUBLIC_APP_ENV=development
ARG NEXT_PUBLIC_APP_RELEASE=development
ARG NEXT_PUBLIC_SENTRY_DSN
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_APP_ENV=$NEXT_PUBLIC_APP_ENV
ENV NEXT_PUBLIC_APP_RELEASE=$NEXT_PUBLIC_APP_RELEASE
ENV NEXT_PUBLIC_SENTRY_DSN=$NEXT_PUBLIC_SENTRY_DSN
RUN pnpm --dir apps/web build

RUN chown -R node:node /workspace
USER node

EXPOSE 3000
CMD ["pnpm", "--dir", "apps/web", "start"]
