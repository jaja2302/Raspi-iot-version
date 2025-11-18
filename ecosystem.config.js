module.exports = {
  apps: [
    {
      name: 'weather-station',
      script: '/home/pi/Raspi-iot-version/weather_station.py',
      interpreter: '/home/pi/Raspi-iot-version/.venv/bin/python',
      cwd: '/home/pi/Raspi-iot-version',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1'
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
      script: '/home/pi/Raspi-iot-version/misol_hybrid.py',
      interpreter: '/home/pi/Raspi-iot-version/.venv/bin/python',
      cwd: '/home/pi/Raspi-iot-version',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1',
        INTERCEPTOR_MODE: 'auto'
      },
      log_file: 'logs/pm2-weather-interceptor.log',
      out_file: 'logs/pm2-weather-interceptor-out.log',
      error_file: 'logs/pm2-weather-interceptor-error.log',
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
