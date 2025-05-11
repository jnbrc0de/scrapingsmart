#!/bin/bash
# Backup simples do banco de dados PostgreSQL/Supabase

# Variáveis de ambiente necessárias:
#   PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE

DATA=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_DIR="../backup"
BACKUP_FILE="$BACKUP_DIR/backup_$DATA.sql"

mkdir -p $BACKUP_DIR

pg_dump -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -F c -b -v -f "$BACKUP_FILE"

if [ $? -eq 0 ]; then
  echo "Backup realizado com sucesso: $BACKUP_FILE"
else
  echo "Erro ao realizar backup!"
fi 