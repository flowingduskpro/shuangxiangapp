-- Baseline migration for PR-2 MVP
-- Generated via: prisma migrate diff --from-empty --to-schema prisma/schema.prisma --script

-- CreateSchema
CREATE SCHEMA IF NOT EXISTS "public";

-- CreateTable
CREATE TABLE "ClassSession" (
    "id" TEXT NOT NULL,
    "classId" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ClassSession_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ClassEvent" (
    "id" TEXT NOT NULL,
    "classSessionId" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "role" TEXT NOT NULL,
    "classId" TEXT NOT NULL,
    "eventType" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "correlationId" TEXT,

    CONSTRAINT "ClassEvent_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "ClassSession_classId_idx" ON "ClassSession"("classId");

-- CreateIndex
CREATE INDEX "ClassEvent_classSessionId_createdAt_idx" ON "ClassEvent"("classSessionId", "createdAt");

-- CreateIndex
CREATE INDEX "ClassEvent_eventType_createdAt_idx" ON "ClassEvent"("eventType", "createdAt");

-- AddForeignKey
ALTER TABLE "ClassEvent" ADD CONSTRAINT "ClassEvent_classSessionId_fkey" FOREIGN KEY ("classSessionId") REFERENCES "ClassSession"("id") ON DELETE CASCADE ON UPDATE CASCADE;

