#!/usr/bin/env bash
set -Eeuo pipefail

readonly_user="${XI_WEN_DW_USER:-xiwen_readonly}"
readonly_password="${XI_WEN_DW_PASSWORD:-xiwen-readonly-local-only}"

if [[ ! "${readonly_user}" =~ ^[A-Za-z0-9_]+$ ]]; then
  echo "XI_WEN_DW_USER may contain only letters, digits, and underscores" >&2
  exit 1
fi

escaped_password="${readonly_password//\\/\\\\}"
escaped_password="${escaped_password//\'/\'\'}"

MYSQL_PWD="${MYSQL_ROOT_PASSWORD}" mysql --protocol=socket -uroot <<SQL
CREATE USER IF NOT EXISTS '${readonly_user}'@'%' IDENTIFIED BY '${escaped_password}';
ALTER USER '${readonly_user}'@'%' IDENTIFIED BY '${escaped_password}';
GRANT SELECT, SHOW VIEW ON \`dw\`.* TO '${readonly_user}'@'%';
SQL
