module.exports = {
  apps: [
    {
      name: 'valuecell-backend',
      script: 'uv',
      args: 'run python -m valuecell.server.main',
      cwd: '/root/.openclaw/apps/valuecell/python',
      env: {
        NODE_ENV: 'production',
        HOST: '0.0.0.0',
        PORT: '8000',
      },
      interpreter: 'none',
    },
    {
      name: 'valuecell-frontend',
      script: 'bun',
      args: 'run start',
      cwd: '/root/.openclaw/apps/valuecell/frontend',
      env: {
        NODE_ENV: 'production',
        PORT: '3200',
        HOST: '0.0.0.0',
      },
      interpreter: 'none',
    }
  ]
};
