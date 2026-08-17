SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS dw DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE meta;

CREATE TABLE IF NOT EXISTS table_info (
    id          VARCHAR(64)  NOT NULL COMMENT '表编号',
    name        VARCHAR(128)          COMMENT '表名称',
    role        VARCHAR(32)           COMMENT '表类型(fact/dim)',
    description TEXT                  COMMENT '表描述',
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS column_info (
    id          VARCHAR(64)  NOT NULL COMMENT '列编号',
    name        VARCHAR(128)          COMMENT '列名称',
    type        VARCHAR(64)           COMMENT '数据类型',
    role        VARCHAR(32)           COMMENT '列类型',
    examples    JSON                  COMMENT '数据示例',
    description TEXT                  COMMENT '列描述',
    alias       JSON                  COMMENT '列别名',
    table_id    VARCHAR(64)           COMMENT '所属表编号',
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS metric_info (
    id               VARCHAR(64)  NOT NULL COMMENT '指标编码',
    name             VARCHAR(128)          COMMENT '指标名称',
    description      TEXT                  COMMENT '指标描述',
    relevant_columns JSON                  COMMENT '关联字段',
    alias            JSON                  COMMENT '指标别名',
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS column_metric (
    column_id VARCHAR(64) NOT NULL COMMENT '列编号',
    metric_id VARCHAR(64) NOT NULL COMMENT '指标编号',
    PRIMARY KEY (column_id, metric_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS semantic_config (
    id         VARCHAR(32) NOT NULL COMMENT '配置编号',
    config     JSON        NOT NULL COMMENT '语义配置',
    updated_at DATETIME    NOT NULL COMMENT '更新时间',
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS chat_session (
    id         VARCHAR(64)  NOT NULL COMMENT '会话编号',
    title      VARCHAR(255) NOT NULL DEFAULT '新会话' COMMENT '标题',
    created_at DATETIME     NOT NULL,
    updated_at DATETIME     NOT NULL,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS chat_turn (
    id         VARCHAR(64)  NOT NULL COMMENT '轮次编号',
    session_id VARCHAR(64)  NOT NULL COMMENT '会话编号',
    seq        INT          NOT NULL DEFAULT 0,
    query      TEXT         NOT NULL,
    kind       VARCHAR(16)  NOT NULL DEFAULT 'query',
    local_text TEXT         NULL,
    steps      JSON         NULL,
    result     JSON         NULL,
    error      TEXT         NULL,
    status     VARCHAR(16)  NOT NULL DEFAULT 'success',
    created_at DATETIME     NOT NULL,
    PRIMARY KEY (id),
    KEY idx_turn_session (session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
