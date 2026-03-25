-- Migration 0010: adiciona coluna reward_source em training_episodes
-- Idempotente: ALTER TABLE ignora erro se coluna ja existir (SQLite nao suporta IF NOT EXISTS)
-- Executar via: migrate.py up
ALTER TABLE training_episodes ADD COLUMN reward_source TEXT NOT NULL DEFAULT 'none';
