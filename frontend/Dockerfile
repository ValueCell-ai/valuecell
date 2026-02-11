FROM oven/bun:1-alpine

WORKDIR /app

COPY package.json bun.lockb* ./
RUN bun install

COPY . .

EXPOSE 1420

CMD ["bun", "x", "react-router", "dev", "--host", "0.0.0.0"]
