-- CreateTable
CREATE TABLE "class_sessions" (
    "id" TEXT NOT NULL,
    "class_id" TEXT NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'active',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "class_sessions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "class_events" (
    "id" TEXT NOT NULL,
    "class_session_id" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "event_type" TEXT NOT NULL,
    "event_data" JSONB,
    "correlation_id" TEXT NOT NULL,
    "timestamp" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "class_events_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "class_sessions_class_id_idx" ON "class_sessions"("class_id");

-- CreateIndex
CREATE INDEX "class_events_class_session_id_idx" ON "class_events"("class_session_id");

-- CreateIndex
CREATE INDEX "class_events_correlation_id_idx" ON "class_events"("correlation_id");

-- CreateIndex
CREATE INDEX "class_events_timestamp_idx" ON "class_events"("timestamp");

-- AddForeignKey
ALTER TABLE "class_events" ADD CONSTRAINT "class_events_class_session_id_fkey" FOREIGN KEY ("class_session_id") REFERENCES "class_sessions"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
