#!/bin/bash
set -e

AGENT_SPEC="$1"

if [[ -z "$AGENT_SPEC" ]]; then
  echo "Ошибка: не передан аргумент AGENT_SPEC"
  exit 1
fi

if [[ "$AGENT_SPEC" == /serve_app/* ]]; then
  echo "Используем локальную версию агента..."
  cd /serve_app
  # Install local py-libp2p first
  if [ -d "/serve_app/py-libp2p" ]; then
    echo "Устанавливаю локальную версию py-libp2p..."
    pip install -e /serve_app/py-libp2p
  fi
  pip install -e .
else
  echo "Устанавливаю $AGENT_SPEC..."
  pip install "$AGENT_SPEC"
fi

echo "Ожидаю готовности Ray head..."
for i in {1..60}; do
  if ray status > /dev/null 2>&1; then
    echo "Ray head готов!"
    break
  fi
  echo "Попытка $i/60: Ray head еще не готов, жду..."
  sleep 2
done

if ! ray status > /dev/null 2>&1; then
  echo "Ошибка: Ray head не запустился за отведенное время"
  exit 1
fi

echo "Запускаю Ray Serve напрямую..."
cd /serve_app
echo "Текущая директория: $(pwd)"
echo "Проверяю entrypoint.py:"
ls -la entrypoint.py
echo "Запускаю serve run..."
exec python entrypoint.py