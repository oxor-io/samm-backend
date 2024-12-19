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

#### `Relayer` service structure:

```
.
├── Dockerfile
├── __init__.py
├── blockchain.py
├── conf.py
├── crud.py
├── db.py
├── imap_client.py
├── logger.py
├── mailer
│   ├── __init__.py
│   ├── body_parser.py
│   ├── dkim_extractor.py
│   └── sender.py
├── main.py
├── member_message.py
├── models.py
├── package-lock.json
├── package.json
├── prover.py
├── requirements.txt
├── scripts
│   └── generateWitness.js
├── target
│   ├── samm_1024.json
│   ├── samm_2048.json
├── tests.py
├── txn_execution.py
└── utils.py

```

**Key files of the `relayer` service:**

- **`imap_client.py`** - Contains functions for retrieving raw emails using the IMAP protocol.
- **`member_message.py`** - Handles core email processing, including parsing, validation, saving members' email data to the database, and sending response messages to members.
- **`prover.py`** - Manages zk-proof generation through subprocesses. The `scripts` and `target` folders are used by the Prover.
- **`txn_execution.py`** - Contains functions for verifying approval thresholds and executing transactions.

#### `Web` service structure:

```
.
├── Dockerfile
├── api
│   ├── __init__.py
│   ├── blockchain.py
│   ├── conf.py
│   ├── db.py
│   ├── main.py
│   ├── member
│   │   ├── crud.py
│   │   ├── models.py
│   │   ├── router.py
│   │   ├── service.py
│   │   └── utils.py
│   ├── owner
│   │   ├── crud.py
│   │   ├── models.py
│   │   └── service.py
│   ├── samm
│   │   ├── crud.py
│   │   ├── models.py
│   │   ├── router.py
│   │   └── service.py
│   ├── sender.py
│   ├── token
│   │   ├── dependencies.py
│   │   ├── models.py
│   │   ├── router.py
│   │   └── utils.py
│   └── txn
│       ├── models.py
│       └── router.py
└── requirements.txt

```

**`Web` service submodules:**

The `web` service is divided into submodules: `owner`, `samm`, `member`, `txn`, and `token`. Each submodule has a similar structure:

- **`models.py`** - Defines the submodule’s data models.
- **`router.py`** - Describes API endpoints.
- **`crud.py`** - Contains database queries.
- **`service.py`** - Implements business logic.

The `token` module has distinct functionality as it handles user authentication, role assignment, and owner signature verification.

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
