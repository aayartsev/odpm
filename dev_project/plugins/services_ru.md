В данном файле указаны примеры сервисов, которые вы можете использовать в виде отдельных контейнеров в одном контексте вместе с инстансом odoo, просто добавив их в файл шаблона в раздел services

```yml
  redis:
    image: redis/redis-stack-server:latest
    container_name: redis
    hostname: redis
    # restart: always
    command:
      - redis-server
      - --appendonly
      - "yes"
      - --appendfilename
      - "appendonly.aof"
      - --requirepass 
      - "$1234657Qw_"
      - --dir
      - "/data"
      - --appendfsync
      - "everysec"
    ports:
    - 6379:6379
    volumes:
    - "/etc/localtime:/etc/localtime:ro"
    - "/etc/timezone:/etc/timezone:ro"
    - ".data/redis:/data"
```

```yml
  redisinsight:
    image: redis/redisinsight:latest
    # container_name: redisinsight
    hostname: redisinsight
    # restart: always
    volumes:
      - .data/redisinsight:/data
    environment:
      - REDIS_HOSTS=local:redis:6379
    ports:
      - 5540:5540
```

```yml
  minio:
    image: minio/minio:latest
    # container_name: minio-local-2
    ports:
      - 9000:9000      # API порт
      - 9001:9001      # Консольный веб-интерфейс
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - .data/minio:/data
    command: server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://minio:9000/minio/health/live"]
      interval: 1s
      timeout: 1s
      retries: 3
    restart: unless-stopped
```

Тестовый почтовый сервер. Имеет web интерфейс на порту 8025
```yml
mailpit:
   container_name: mailpit
   image: axllent/mailpit
   restart: unless-stopped
   volumes:
    - ./data/mailpit:/data
   ports:
    - 8025:8025
    - 1025:1025
    - 1110:1110
   environment:
    - MP_MAX_MESSAGES=5000
    - MP_POP3_BIND_ADDR=0.0.0.0:1110
    - MP_DATABASE=/data/mailpit.db
    - MP_SMTP_AUTH_ACCEPT_ANY=1
    - MP_SMTP_AUTH_ALLOW_INSECURE=1
    - MP_POP3_AUTH=user1:user1 user2:user2
```
```bash
mkdir -p ./data/nginx/conf.d
nano ./data/nginx/conf.d/default.conf
```
```conf
server {
    listen 80;
    server_name bashflag.pro;

    client_max_body_size 100M;
    
    access_log /var/log/nginx/odoo.access.log;
    error_log /var/log/nginx/odoo.error.log;

    # Acme-challenge для Let's Encrypt
    location ^~ /.well-known/acme-challenge/ {
        root /var/www/certbot;
        default_type "text/plain";
    }

    # Проксирование на Odoo
    location / {
        proxy_pass http://odoo:8069;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```yml
  nginx:
    image: nginx:alpine
    depends_on:
      - odoo
    ports:
      -  "80:80"
      -  "443:443"
    volumes:
      - ./data/nginx/conf.d:/etc/nginx/conf.d
      - ./data/nginx/nginx/certbot/conf:/etc/letsencrypt:ro
      - ./data/nginx/nginx/nginx/certbot/www:/var/www/certbot:ro
    command:
      - /bin/sh
      - -c
      - "if [ -d /etc/nginx/conf.d/nginx.conf ]; then rm -rf /etc/nginx/conf.d/nginx.conf; fi; exec nginx -g 'daemon off;'"
```

```yml
  certbot:
    image: certbot/certbot
    depends_on:
      - nginx
    volumes:
      - ./data/certbot/conf:/etc/letsencrypt
      - ./data/certbot/www:/var/www/certbot
    entrypoint: >
      sh -c "trap exit TERM;
      while :; do
        certbot renew;
        sleep 12h & wait $${{!}};
      done"
```

# https://github.com/vernu/textbee - проект для тестирования отправки sms сообщений
