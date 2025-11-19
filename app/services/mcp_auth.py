import os
from fastmcp.server.auth.providers.jwt import RSAKeyPair
from app.utils.logger import logger  # Adjust this path if needed
from pydantic import SecretStr

async def authenticate_mcp_servers():
    try:
        logger.info("Authenticating MCP servers...")
        base_dir = os.getcwd()
        credentials_dir = os.path.join(base_dir, "credentials")

        # Create credentials folder if it doesn't exist
        os.makedirs(credentials_dir, exist_ok=True)

        private_key_path = os.path.join(credentials_dir, "private_key.pem")
        public_key_path = os.path.join(credentials_dir, "public_key.pem")

        # Check if both key files exist
        if os.path.exists(private_key_path) and os.path.exists(public_key_path):
            logger.info("RSA keys found. Loading existing keys...")

            with open(private_key_path, "r") as f:
                private_key_content = f.read()

            with open(public_key_path, "r") as f:
                public_key_content = f.read()

            key_pair = RSAKeyPair(
                private_key=SecretStr(private_key_content),
                public_key=public_key_content
            )
        else:
            logger.info("RSA keys not found. Generating new key pair...")

            # Generate new RSA Key Pair
            key_pair = RSAKeyPair.generate()

            # Save keys to files
            with open(private_key_path, "w") as f:
                f.write(key_pair.private_key.get_secret_value())

            with open(public_key_path, "w") as f:
                f.write(key_pair.public_key)

            logger.info("New RSA keys generated and saved successfully.")

        # Create JWT using the key pair
        agent_token = key_pair.create_token(
            subject="triage-agent",
            issuer="https://agents.kivo.ai/agent",
            audience="mcp-server",
            scopes=["read", "write"]
        )

        logger.info("JWT token generated successfully.")
        return agent_token, key_pair.public_key

    except Exception as e:
        logger.error(f"Failed to load/generate RSA keys or token: {e}", exc_info=True)
        return None, None
