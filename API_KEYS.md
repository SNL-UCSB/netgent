# API Keys Configuration

NetGent requires API keys for LLM (Large Language Model) access when running in **Code Generation Mode** (`-g`). The framework supports Google's Gemini models through two authentication methods.

## Supported LLM Providers

NetGent currently supports:

- **Google Generative AI** (Gemini) - via API key
- **Google Vertex AI** (Gemini) - via service account credentials

## API Key File Format

Create a JSON file (e.g., `api_keys.json`) with the following structure:

```json
{
  "google_api_key": "YOUR_API_KEY_HERE"
}
```

**OR** for Vertex AI authentication, use a Google Cloud service account JSON file:

```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "...",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "...",
  "universe_domain": "googleapis.com"
}
```

## How to Get API Keys

### Option 1: Google Generative AI API Key (Recommended)

1. **Go to Google AI Studio**

   - Visit: https://aistudio.google.com/app/apikey

2. **Sign in**

   - Use your Google account to sign in

3. **Create API Key**

   - Click "Create API Key" or "Get API Key"
   - Select an existing Google Cloud project or create a new one
   - Copy the generated API key

4. **Save the API Key**

   - Create a JSON file (e.g., `api_keys.json`) with:
     ```json
     {
       "google_api_key": "YOUR_API_KEY_HERE"
     }
     ```
   - **Important**: Never commit this file to version control. Add it to `.gitignore`

5. **Usage**
   - The API key will be used automatically when provided in the API keys file
   - NetGent uses the `gemini-2.0-flash-exp` model by default

### Option 2: Google Vertex AI (Service Account)

If you prefer using Vertex AI or need enterprise features:

1. **Set up Google Cloud Project**

   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Vertex AI API:
     - Navigate to "APIs & Services" > "Library"
     - Search for "Vertex AI API"
     - Click "Enable"

2. **Create Service Account**

   - Go to "IAM & Admin" > "Service Accounts"
   - Click "Create Service Account"
   - Provide a name and description
   - Click "Create and Continue"

3. **Grant Permissions**

   - Add the role: "Vertex AI User" (or "AI Platform User")
   - Click "Continue" and then "Done"

4. **Create and Download Key**

   - Click on the created service account
   - Go to the "Keys" tab
   - Click "Add Key" > "Create new key"
   - Select "JSON" format
   - Download the JSON file

5. **Save the Credentials**

   - Use the downloaded JSON file directly as your API keys file
   - **Important**: Never commit this file to version control. Add it to `.gitignore`

6. **Set Environment Variable (Optional)**
   - You can also set `GOOGLE_APPLICATION_CREDENTIALS` environment variable:
     ```bash
     export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
     ```
   - If this is set, NetGent will use Vertex AI automatically (fallback behavior)

## Authentication Priority

NetGent checks for API keys in the following order:

1. **`google_api_key` in API keys file** → Uses Google Generative AI
2. **Service account JSON in API keys file** → Uses Google Vertex AI
3. **`GOOGLE_APPLICATION_CREDENTIALS` environment variable** → Uses Google Vertex AI

## Security Best Practices

1. **Never commit API keys to version control**

   - Add `api_keys.json`, `google_creds.json`, and similar files to `.gitignore`
   - Use environment variables or secure secret management in production

2. **Restrict API key permissions**

   - For Google Generative AI: Set usage quotas and restrictions in Google AI Studio
   - For Vertex AI: Use least-privilege IAM roles

3. **Rotate keys regularly**

   - Periodically regenerate and update your API keys
   - Monitor usage for any suspicious activity

4. **Use separate keys for development and production**
   - Maintain different API keys for different environments

## Example Usage

### CLI Usage

```bash
# Using API keys file
docker run --platform=linux/amd64 --rm -d \
  -p 8080:8080 \
  -v "$PWD/api_keys.json:/keys.json:ro" \
  -v "$PWD/examples/prompts/google_prompts.json:/prompts.json:ro" \
  -v "$PWD/out:/out" \
  netgent:amd64 \
  -g /keys.json '{}' /prompts.json \
  -o /out/state_repository.json \
  -s
```

### Python SDK Usage

```python
from netgent import NetGent, StatePrompt
from langchain_google_vertexai import ChatVertexAI
from langchain_google_genai import ChatGoogleGenerativeAI

# Option 1: Using Google Generative AI API key
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-exp",
    temperature=0.2,
    api_key="YOUR_API_KEY_HERE"
)

# Option 2: Using Vertex AI (requires GOOGLE_APPLICATION_CREDENTIALS or service account)
llm = ChatVertexAI(
    model="gemini-2.0-flash-exp",
    temperature=0.2
)

agent = NetGent(llm=llm, llm_enabled=True)
```

## Troubleshooting

### "API keys file not found"

- Ensure the path to your API keys file is correct
- Check file permissions (should be readable)

### "Invalid JSON format"

- Validate your JSON file syntax using a JSON validator
- Ensure proper escaping of special characters

### Authentication Errors

- **Google Generative AI**: Verify your API key is valid and has not expired
- **Vertex AI**: Ensure the Vertex AI API is enabled in your Google Cloud project
- Check that your service account has the necessary permissions

### Rate Limiting

- Google APIs have rate limits based on your quota
- Monitor usage in Google Cloud Console or AI Studio
- Consider implementing retry logic for production use

## Additional Resources

- [Google AI Studio Documentation](https://ai.google.dev/docs)
- [Google Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [LangChain Google Integration](https://python.langchain.com/docs/integrations/platforms/google)
