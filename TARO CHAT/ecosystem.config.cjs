module.exports = {
  apps: [{
    name: 'tarot-backend',
    script: 'main.py',
    interpreter: '/root/tarot-luna/backend/venv/bin/python',
    autorestart: true,
    watch: false,
    env: {
      PYTHONUNBUFFERED: '1'
    }
  }]
};
