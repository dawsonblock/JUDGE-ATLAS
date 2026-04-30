FROM node:20-slim

ENV NEXT_TELEMETRY_DISABLED=1

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

ENV NODE_ENV=production
RUN groupadd --system --gid 1001 nodejs && useradd --system --uid 1001 --gid nodejs nextjs && chown -R nextjs:nodejs /app
USER nextjs

EXPOSE 3000
CMD ["npm", "run", "start"]
