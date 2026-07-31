FROM node:22-alpine

WORKDIR /app

COPY package.json pnpm-lock.yaml* package-lock.json* npm-shrinkwrap.json* ./

RUN npm install --legacy-peer-deps || npm install

COPY . .

RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
