# LLM Configuration Guide

BoardFlow supports two LLM providers for Claude models: **Anthropic Native API** and **AWS Bedrock**.

## Configuration Options

### Environment Variables

Configure the LLM provider in your `.env` file:

```bash
# LLM Provider Selection
LLM_PROVIDER=anthropic  # Options: 'anthropic' or 'bedrock'

# Anthropic Native API (when LLM_PROVIDER=anthropic)
ANTHROPIC_API_KEY=sk-ant-xxxxx
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# AWS Bedrock (when LLM_PROVIDER=bedrock)
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
```

## Provider Comparison

| Feature | Anthropic Native | AWS Bedrock |
|---------|-----------------|-------------|
| **Setup** | API key only | AWS credentials + IAM permissions |
| **Best For** | Development, rapid iteration | Production, enterprise deployments |
| **Cost Management** | Anthropic billing | AWS billing with detailed cost tracking |
| **Security** | API key | IAM roles, VPC endpoints, KMS encryption |
| **Latency** | Direct API calls | Slight overhead from AWS SDK |
| **Models** | Latest Claude models immediately | AWS-approved models (may lag behind) |

## Using Anthropic Native API

### Setup

1. Get API key from https://console.anthropic.com/
2. Configure in `.env`:

```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-xxxxx
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

### Available Models

- `claude-3-5-sonnet-20241022` - Latest Sonnet (recommended)
- `claude-3-opus-20240229` - Most capable
- `claude-3-haiku-20240307` - Fastest, cheapest

## Using AWS Bedrock

### Setup

1. **Configure AWS Credentials**

   Use one of these methods:
   - AWS CLI: `aws configure`
   - Environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
   - IAM role (for EC2/ECS/Lambda)

2. **Request Model Access**

   - Go to AWS Bedrock console → Model access
   - Request access to Anthropic Claude models
   - Wait for approval (usually instant)

3. **Configure in `.env`**:

```bash
LLM_PROVIDER=bedrock
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
```

### Available Bedrock Model IDs

- `anthropic.claude-3-5-sonnet-20241022-v2:0` - Latest Sonnet
- `anthropic.claude-3-opus-20240229-v1:0` - Most capable
- `anthropic.claude-3-haiku-20240307-v1:0` - Fastest

Check AWS Bedrock console for latest model IDs.

### IAM Permissions Required

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-*"
      ]
    }
  ]
}
```

## Programmatic Usage

The service automatically uses configuration from `.env`:

```python
from services import LLMService

# Uses settings from .env
llm = LLMService()

# Extract intent from user query
intent = llm.extract_intent("I love Catan, suggest something similar")

# Generate explanation
explanation = llm.generate_explanation(
    game_name="Ticket to Ride",
    user_profile={"top_mechanics": ["trading", "set collection"]},
    score_breakdown={"profile_score": 0.85}
)
```

### Override Configuration

You can override settings programmatically:

```python
from config import LLMProvider
from services import LLMService

# Force Anthropic with specific model
llm = LLMService(
    provider=LLMProvider.ANTHROPIC,
    api_key="sk-ant-xxxxx",
    model="claude-3-opus-20240229"
)

# Force Bedrock with specific model
llm = LLMService(
    provider=LLMProvider.BEDROCK,
    model="anthropic.claude-3-haiku-20240307-v1:0",
    aws_region="us-west-2"
)
```

## Troubleshooting

### Anthropic Native API

**Error: `ANTHROPIC_API_KEY must be set`**
- Ensure `.env` has `ANTHROPIC_API_KEY=sk-ant-xxxxx`
- Restart FastAPI server after changing `.env`

**Error: `401 Unauthorized`**
- Check API key is valid
- Verify key has not expired

### AWS Bedrock

**Error: `Could not connect to the endpoint URL`**
- Check `AWS_REGION` is correct
- Verify AWS credentials are configured: `aws sts get-caller-identity`

**Error: `AccessDeniedException`**
- Request model access in AWS Bedrock console
- Check IAM permissions include `bedrock:InvokeModel`

**Error: `ValidationException: Malformed input request`**
- Verify `BEDROCK_MODEL_ID` is correct
- Check model is available in your region

## Cost Considerations

### Anthropic Native API Pricing (as of 2024)

- Claude 3.5 Sonnet: $3/MTok input, $15/MTok output
- Claude 3 Opus: $15/MTok input, $75/MTok output
- Claude 3 Haiku: $0.25/MTok input, $1.25/MTok output

### AWS Bedrock Pricing

- Similar to Anthropic native, but with AWS billing
- Use AWS Cost Explorer for detailed tracking
- Set up billing alarms for cost management

## Recommendations

- **Development**: Use Anthropic native for simplicity
- **Production**: Use Bedrock for:
  - Enterprise compliance requirements
  - AWS-native infrastructure
  - Advanced cost tracking
  - VPC integration needed
