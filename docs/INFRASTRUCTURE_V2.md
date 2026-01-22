# War Room Infrastructure (v2.0 - Migration)

> **Status**: Migrated to Neural-Home Homelab (LXC 106)
> **Date**: 2026-01-22

## 1. Architecture Overview
The War Room runs in a dedicated, isolated container (**The Bunker**) within the Neural-Home architecture.

### Hardware Topology
*   **Container**: `LXC 106` (Ubuntu 24.04 via Docker 24.04 template?)
    *   **Hostname**: `WarRoom`
    *   **IP**: `192.168.1.106`
    *   **Resources**: 2 vCPU, 2GB RAM
*   **Database Host**: `LXC 105` (Postgres)
    *   **IP**: `192.168.1.105`
    *   **Database**: `warroom_db`
    *   **Isolation**: Accessed via user `warroom_user`.
*   **AI Intelligence**: `VM 100` (Orchestrator)
    *   **IP**: `192.168.1.20`
    *   **Port**: `8000` (OpenAI-compatible /v1/chat/completions)
    *   **RAG**: Uses isolated collection `warroom_rag` (LXC 101).

## 2. Service Configuration
### Backend
*   **Service**: `warroom-backend.service` (Systemd)
*   **Port**: `8090`
*   **Workdir**: `/opt/war-room` (or `~/Projects/war-room` on deployment)
*   **Env Variables**:
    *   `DATABASE_URL=postgresql://warroom_user:XXX@192.168.1.105:5432/warroom_db`
    *   `OLLAMA_API_BASE=http://192.168.1.20:8000/v1`

### Frontend
*   **Service**: Nginx (Reverse Proxy)
*   **Port**: `80` (Exposed), `5173` (Internal Vite)
*   **URL**: `http://192.168.1.106`

## 3. Data Ingestion (Hybrid)
*   **Legacy**: Windows Scripts (Ingest_*.bat) -> Point to DB 192.168.1.105.
*   **Modern**: Python Scripts on LXC 106 reading from **GDrive** via Service Account.
*   **Storage**: `WAR_ROOM_DATA` on Google Drive (Mounted/Synced to `/mnt/warroom_data`).

## 4. Credentials
Credentials are stored in the secure vault `docs/CREDENTIALS_MAP.md` in the `neural-home-repo`.
