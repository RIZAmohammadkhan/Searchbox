# AI Search Widget

A modern, embeddable AI chat widget powered by OpenAI's Assistant API. Add an intelligent search interface to your website with just a few lines of code.

## Quick Start

### 1. Prerequisites

- Python 3.7+
- OpenAI API key
- OpenAI Assistant ID

### 2. Installation

```bash
# Clone the repository (or download the files)
git clone https://github.com/yourusername/automee-widget

# Install dependencies
pip install fastapi uvicorn pandas openai python-multipart
```

### 3. Configuration

1. Create `assistants.csv` with your credentials:

```csv
client_id,assistant_id,api_key
your_client_id,asst_your_assistant_id,your_openai_api_key
```

2. Start the server:

```bash
uvicorn server:app --reload
```

### 4. Add to Your Website

Add this code where you want the widget to appear:

```html
<script>
    fetch('http://localhost:8000/api/generate-script/your_client_id')
        .then(response => response.json())
        .then(data => {
            const script = document.createElement('script');
            script.textContent = data.script.replace('YOUR_SERVER_URL', 'http://localhost:8000');
            document.body.appendChild(script);
        });
</script>
```

## Customization

### Theme Colors

Add these CSS variables to your website to match your brand:

```css
:root {
    --ai-primary-color: #b38bfa;      /* Main accent color */
    --ai-primary-light: rgba(179, 139, 250, 0.1);  /* Light accent color */
    --ai-background: #ffffff;         /* Widget background */
    --ai-secondary-bg: #f9fafb;      /* Secondary background */
    --ai-border: #e5e7eb;           /* Border color */
    --ai-text: #1F2937;             /* Main text color */
    --ai-secondary-text: #6B7280;   /* Secondary text */
}
```

## Production Deployment

For production environments:

1. Update CORS in `server.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

2. Use environment variables for sensitive data
3. Deploy behind HTTPS
4. Update widget script URL to your production server

## Features

- 🎨 Fully customizable theme
- 📝 Markdown support in responses
- ⚡ Real-time typing animation
- 🔄 Conversation memory
- 🎯 Click-away to reset
- 📱 Responsive design

## Security Best Practices

- Store API keys securely on the server
- Use HTTPS in production
- Implement rate limiting
- Add authentication if needed
- Regularly rotate API keys

## Common Issues

### Widget Not Appearing
- Check browser console for errors
- Verify your client_id in assistants.csv
- Ensure server is running

### CORS Errors
- Add your domain to allowed origins
- Check server URL in widget script

### API Errors
- Verify API key and Assistant ID
- Check OpenAI API status

## Support

For issues and feature requests, please open an issue in the repository.

## License

MIT License
