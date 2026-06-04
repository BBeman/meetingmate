# Example Meeting Transcripts

This folder contains sample meeting transcripts for testing and demonstration.

## Files

- `sample_meeting.txt` - A product planning review meeting with action items and decisions

## Usage

### Ingest the sample transcript

```bash
# First, get an auth token
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "yourpassword"}' \
  | jq -r '.access_token')

# Ingest the meeting transcript
curl -X POST http://localhost:8000/meetings/ingest \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @- << 'EOF'
{
  "title": "Q4 Product Planning Review",
  "transcript": "'"$(cat examples/sample_meeting.txt)"'"
}
EOF
```

### Query the meeting with the agent

```bash
# Ask about action items
curl -X POST http://localhost:8000/agent/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "What action items came out of the Q4 planning meeting?"}'

# Ask about decisions
curl -X POST http://localhost:8000/agent/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "What decisions were made about the API rate limiting feature?"}'

# Search for topics
curl -X POST http://localhost:8000/agent/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Find meetings that discuss OAuth or authentication"}'
```
