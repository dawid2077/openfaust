# 🦊 OpenFaust (v2)

An asynchronous, event-driven, multi-processed AI companion framework built for Discord. OpenFaust doesn't just passively reply to messages—it actively monitors conversation momentum, autonomously decides when to engage, and wakes itself up to break long silences using a custom routing engine.

Developed on **NixOS**, written in **Python**, and deployed seamlessly via **Docker**.

---

## 🗺️ System Architecture

The ecosystem is built out of isolated modules separating core Discord events, LLM orchestration, and background processes:

<img src="image_9593f6.jpg" alt="OpenFaust Architecture Diagram" width="750">

*The detailed interaction routing diagram mapping context.py, kairos.py, and the background execution loops as visualized in image_9593f6.jpg.*

---

## ✨ Key Features

*   **🧠 Kairos Semantic Router:** Uses a fast, deterministic model (`gpt-4o-mini`) as a traffic cop to evaluate whether a user's message warrants a response based on timing, direct tags, or conversational continuity before passing it to a heavier model.
*   **💓 Decoupled Heartbeat Loop:** A background `multiprocessing.Process` completely separate from the Discord thread that evaluates chat silences every 30 minutes and can autonomously trigger interactions.
*   **📂 Persistent Local Memory:** Powered by an optimized SQLite database factory tracking clean, structured user histories and metadata context.
*   **🎭 Dynamic Persona Engine:** Fully personality-agnostic. Drop any markdown profile into the data directory, and the framework automatically re-extracts the identity and re-aligns the routing logic.

---

## 🚀 Quick Start

### 1. Environment Configuration
Create a `.env` file in the root directory:

```env
DISCORD_TOKEN=your_discord_bot_token
OPENROUTER_API_KEY=your_openrouter_api_key
APP_DATA_PATH=/app/data
APP_PERSONALITY_PATH=/app/data/personality.md
```

### 2. Docker Compose Configuration
Create a `docker-compose.yml` file in the root directory:

```yaml
services:
  openfaust:
    build: .
    container_name: openfaust
    restart: unless-stopped
    env_file:
      - .env  
    volumes:
      - ./data:/app/data
```

### 3. Run the Framework
Launch the containerized application in detached mode:

```bash
docker compose up -d
```

---

## 🎭 Dynamic Personality Customization

To swap your bot's behavior profile dynamically:

1. Stop the current deployment container:
   ```bash
   docker compose stop
   ```
2. Open and modify the `./data/personality.md` file (or your custom file path if you changed it) to design your new custom personality prompt rules.
3. Bring the framework back online:
   ```bash
   docker compose up -d
   ```

---

## 🛠️ My Design Choices 

### 🐍 Python
> I decided to use python because i have most expierience in it and like to use it , it has a good discord andapi for models library.

### 🧠 The Kairos Router & Heartbeat
> I added kairos to make openfaust feel more human have it interact with the user on its own. and to save costs

### 🗄️ SQLite & Context
> I choosed sqlite because its just a one file it handles well json and i needed a database for persistent storage and context because docker on its own is stateless

### 🐋 Multi-Process Containerization (Docker)
> I decided to go with docker because i care about plug and play component of it and also it provides security, isolation, and seamless management
### 🌐 Hosting & Deployment (OCI & NixOS)

> I developed it on nixos and on my server it runs on nixos because i love nixos and i think its underrated for development and especially as a server distro .I  personally host it on oci because it has a very generous free tier and i have already knew it because i have a certificate

---



##  LICENSE

*   **This project is licensed under the GNU Affero General Public License v3.0 - see the [LICENSE](LICENSE) file for details.** 
*   **Copyright (c) 2026 dawid2077** 


