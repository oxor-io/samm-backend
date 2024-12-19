# samm-backend

### Repository Structure  

The SAMM backend repository includes a `docker-compose.yml` file that launches three backend services:  
- **`relayer`** - Receives emails from the IMAP server, parses them, generates proofs using the Prover subprocess, stores data in the database, and executes transactions when the approval threshold is reached.  
- **`web`** - An API service that provides transaction and SAMM data for the UI.  
- **`database`** - A PostgreSQL database where the Relayer stores transactions and approvals, accessed by the Web service to support the UI.  

The database runs as a Postgres container. The remaining two services are built from the source code in their respective folders using `Dockerfile` files.  

Sample environment variable files are located in the project root:  
- `.env_relayer.example`  
- `.env_web.example`  

### Environment Variables  

Before running the project, create and populate the environment variable files `.env_relayer` and `.env_web` based on the provided examples.  

**Sample `.env_relayer` configuration:**  

```env
# .env_relayer  

# SMTP server host/port for sending emails to members  
SMTP_HOST=smtp.gmail.com  
SMTP_PORT=465  

# IMAP server host/port for receiving emails from members  
IMAP_HOST=imap.gmail.com  
IMAP_PORT=993  

# IMAP idle timeout in seconds (Relayer waits for new emails from the IMAP server)  
IMAP_IDLE_TIMEOUT=900  

# Initialize the database with default values(useful for debugging) 
# Comment the line for disable
INIT_DATABASE=true  

# Relayer's email and password for sending emails via SMTP  
RELAYER_EMAIL=samm@oxor.io  
RELAYER_PASSWORD=**********  

# Google OAuth2 credentials for IMAP server access  
GMAIL_REFRESH_TOKEN=**********  
GMAIL_CLIENT_ID=**********.apps.googleusercontent.com  
GMAIL_CLIENT_SECRET=**********  

# Frontend application URL used in email responses  
SAMM_APP_URL=https://samm-demo.oxor.io/  

# Ethereum RPC URL  
RPC_URL=https://ethereum-sepolia-rpc.publicnode.com  

# Private key for executing transactions on-chain after confirmation  
PRIVATE_KEY=**********  
```

**How to Obtain the `RELAYER_PASSWORD`:**  
1. Go to [Google Account Security](https://myaccount.google.com/security) for your `RELAYER_EMAIL`.  
2. Ensure "2-Step Verification" is enabled.  
3. After enabling it, look for "App Passwords" at the bottom. Assign a name to your application and generate a password.  

**How to Obtain Google OAuth2 Tokens:**  
Follow the [official documentation](https://developers.google.com/identity/protocols/oauth2/web-server#python_1) for guidance on obtaining `GMAIL_REFRESH_TOKEN`, `GMAIL_CLIENT_ID`, and `GMAIL_CLIENT_SECRET`.  


**Sample `.env_web` Configuration:**  

```env
# .env_web  

# SMTP server host/port for sending emails to members  
SMTP_HOST=smtp.gmail.com  
SMTP_PORT=465  

# Relayer's email and password for sending emails via SMTP  
RELAYER_EMAIL=samm@oxor.io  
RELAYER_PASSWORD=**********  

# JWT secret key for service authentication  
# Generate a random value using the command:  
# openssl rand -hex 32  
JWT_SECRET_KEY=**********  

# Ethereum RPC URL  
RPC_URL=https://ethereum-sepolia-rpc.publicnode.com  
```

### Deployment  

After populating environment variables in `.env_relayer` and `.env_web`, deploy the project using Docker Compose:  

1. Build and start the containers:  
   ```sh
   docker-compose up -d --build  
   ```  

2. Stop and remove old containers and volumes:  
   ```sh
   docker-compose down -v  
   ```  

### Running Tests  

To run tests locally, set up a virtual environment first:  

1. Create and activate a virtual environment:  
   ```sh
   python -m venv .venv  
   source .venv/bin/activate  
   ```  

2. Install required packages:  
   ```sh
   pip install -r relayer/requirements.txt  
   ```  

3. Execute tests:  
   ```sh
   python relayer/tests.py  
   ```
