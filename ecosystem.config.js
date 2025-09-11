module.exports = {
  apps: [{
    name: 'weather-station',
    script: 'weather_station.py',
    interpreter: 'venv/bin/python',
    cwd: '/home/pi/Raspi-iot-version', // Ganti dengan path yang sesuai
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'production',
      FLASK_ENV: 'production'
    },
    log_file: 'logs/pm2-combined.log',
    out_file: 'logs/pm2-out.log',
    error_file: 'logs/pm2-error.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    merge_logs: true,
    max_restarts: 10,
    min_uptime: '10s',
    restart_delay: 4000,
    kill_timeout: 5000,
    listen_timeout: 3000,
    shutdown_with_message: true
  }]
};
