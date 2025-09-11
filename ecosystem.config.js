module.exports = {
  apps: [
    {
      name: 'weather-station',
      script: '/home/pi/Raspi-iot-version/weather_station.py',
      interpreter: '/home/pi/Raspi-iot-version/venv/bin/python',
      cwd: '/home/pi/Raspi-iot-version',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production',
        FLASK_ENV: 'production'
      },
      log_file: 'logs/pm2-weather-station.log',
      out_file: 'logs/pm2-weather-station-out.log',
      error_file: 'logs/pm2-weather-station-error.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      max_restarts: 10,
      min_uptime: '10s',
      restart_delay: 4000,
      kill_timeout: 5000,
      listen_timeout: 3000,
      shutdown_with_message: true
    },
    {
      name: 'weather-interceptor',
      script: '/home/pi/Raspi-iot-version/weather_interceptor.py',
      interpreter: '/home/pi/Raspi-iot-version/venv/bin/python',
      cwd: '/home/pi/Raspi-iot-version',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      env: {
        NODE_ENV: 'production',
        INTERCEPTOR_MODE: 'auto' // Auto start intercepting
      },
      log_file: 'logs/pm2-interceptor.log',
      out_file: 'logs/pm2-interceptor-out.log',
      error_file: 'logs/pm2-interceptor-error.log',
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
