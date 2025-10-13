module.exports = {
  apps: [
    {
      name: 'weather-system',
      script: '/home/daraspi01/Desktop/IOT/Raspi-iot-version/main.py',
      interpreter: '/home/daraspi01/Desktop/IOT/Raspi-iot-version/venv/bin/python',
      cwd: '/home/daraspi01/Desktop/IOT/Raspi-iot-version',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1'
      },
      log_file: 'logs/pm2-weather-system.log',
      out_file: 'logs/pm2-weather-system-out.log',
      error_file: 'logs/pm2-weather-system-error.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      max_restarts: 10,
      min_uptime: '10s',
      restart_delay: 4000,
      kill_timeout: 5000,
      listen_timeout: 3000,
      shutdown_with_message: true
    }
  ]
};
