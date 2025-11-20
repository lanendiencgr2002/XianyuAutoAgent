/*
 Navicat Premium Dump SQL

 Source Server         : 咸鱼单子
 Source Server Type    : SQLite
 Source Server Version : 3045000 (3.45.0)
 Source Schema         : main

 Target Server Type    : SQLite
 Target Server Version : 3045000 (3.45.0)
 File Encoding         : 65001

 Date: 19/07/2025 15:09:14
*/

PRAGMA foreign_keys = false;

-- ----------------------------
-- Table structure for messages
-- ----------------------------
DROP TABLE IF EXISTS "messages";
CREATE TABLE "messages" (
  "id" INTEGER PRIMARY KEY AUTOINCREMENT,
  "user_id" TEXT NOT NULL,
  "item_id" TEXT NOT NULL,
  "role" TEXT NOT NULL,
  "content" TEXT NOT NULL,
  "timestamp" DATETIME DEFAULT CURRENT_TIMESTAMP,
  "chat_id" TEXT
);

-- ----------------------------
-- Auto increment value for messages
-- ----------------------------
UPDATE "sqlite_sequence" SET seq = 620 WHERE name = 'messages';

-- ----------------------------
-- Indexes structure for table messages
-- ----------------------------
CREATE INDEX "idx_chat_id"
ON "messages" (
  "chat_id" ASC
);
CREATE INDEX "idx_timestamp"
ON "messages" (
  "timestamp" ASC
);
CREATE INDEX "idx_user_item"
ON "messages" (
  "user_id" ASC,
  "item_id" ASC
);

PRAGMA foreign_keys = true;
