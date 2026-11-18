#!/bin/sh
# Chỉ chạy một lần khi volume dữ liệu còn trống: tạo DB riêng cho pytest.
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<EOSQL
CREATE DATABASE "$POSTGRES_TEST_DB";
EOSQL
