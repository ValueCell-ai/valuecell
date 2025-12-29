FROM node:18-alpine

WORKDIR /app

# Install bun (project uses bun)
RUN npm install -g bun

# Copy dependency files
COPY package.json bun.lockb* ./

# Install dependencies
RUN bun install

# Copy rest of frontend code
COPY . .

# Expose frontend port
EXPOSE 1420

# Bind to all interfaces so it's accessible remotely
ENV HOST=0.0.0.0
ENV PORT=1420

# Start dev server
CMD ["bun", "run", "dev"]
