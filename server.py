from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import pandas as pd
from openai import OpenAI
import asyncio
import json
from typing import Dict

app = FastAPI()

# Store active runs
active_runs: Dict[str, Dict] = {}

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with actual domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/")
async def read_root():
    return FileResponse("test.html")

# Load assistants mapping from CSV
assistants_df = pd.read_csv('assistants.csv')
assistants_map = dict(zip(assistants_df['client_id'], zip(assistants_df['assistant_id'], assistants_df['api_key'])))

class QueryRequest(BaseModel):
    client_id: str
    query: str
    thread_id: str | None = None

@app.post("/api/query")
async def process_query(request: QueryRequest):
    if request.client_id not in assistants_map:
        raise HTTPException(status_code=404, detail="Client ID not found")
    
    assistant_id, api_key = assistants_map[request.client_id]
    client = OpenAI(api_key=api_key)
    
    try:
        # Create or use existing thread
        if not request.thread_id:
            thread = client.beta.threads.create()
            thread_id = thread.id
        else:
            thread_id = request.thread_id
            
        # Add message to thread
        message = client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=request.query
        )
        
        # Run assistant
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )
        
        # Store run information
        active_runs[run.id] = {
            "thread_id": thread_id,
            "client": client,
            "status": "running"
        }
        
        # Wait for completion
        while True:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            
            # Check if run was cancelled
            if active_runs[run.id]["status"] == "cancelled":
                client.beta.threads.runs.cancel(
                    thread_id=thread_id,
                    run_id=run.id
                )
                del active_runs[run.id]
                return {"status": "cancelled", "thread_id": thread_id}
                
            if run_status.status == 'completed':
                break
            elif run_status.status == 'failed':
                raise HTTPException(status_code=500, detail="Assistant run failed")
            await asyncio.sleep(0.5)
        
        # Get messages
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        latest_message = messages.data[0].content[0].text.value
        
        # Clean up
        del active_runs[run.id]
        
        return {
            "response": latest_message,
            "thread_id": thread_id,
            "run_id": run.id
        }
        
    except Exception as e:
        if 'run' in locals() and run.id in active_runs:
            del active_runs[run.id]
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stop")
async def stop_generation(run_id: str):
    if run_id not in active_runs:
        raise HTTPException(status_code=404, detail="Run not found or already completed")
    
    active_runs[run_id]["status"] = "cancelled"
    return {"status": "stopping"}

@app.get("/api/generate-script/{client_id}")
async def generate_script(client_id: str, primary_color: str = "#b894f7"):
    if client_id not in assistants_map:
        raise HTTPException(status_code=404, detail="Client ID not found")
    
    # Convert primary color to RGB for creating transparent version
    primary_rgb = None
    if primary_color.startswith('#'):
        primary_rgb = tuple(int(primary_color[i:i+2], 16) for i in (1, 3, 5))
    
    script = generate_widget_script(client_id, primary_color, primary_rgb)
    return {"script": script}

def generate_widget_script(client_id: str, primary_color: str, primary_rgb: tuple = None):
    # Create rgba string for light variant
    primary_light = f"rgba({primary_rgb[0]}, {primary_rgb[1]}, {primary_rgb[2]}, 0.1)" if primary_rgb else "rgba(184, 148, 247, 0.1)"
    
    return f"""
    (function() {{
        const clientId = "{client_id}";
        
        // Add marked.js for markdown rendering
        const markedScript = document.createElement('script');
        markedScript.src = 'https://cdn.jsdelivr.net/npm/marked/marked.min.js';
        document.head.appendChild(markedScript);

        const styles = `
            <style>
                :root {{
                    --ai-primary-color: {primary_color};
                    --ai-primary-light: {primary_light};
                    --ai-background: #ffffff;
                    --ai-secondary-bg: #f8f9fa;
                    --ai-border: #eef0f2;
                    --ai-text: #111827;
                    --ai-secondary-text: #6b7280;
                }}

                #ai-search-widget {{
                    width: 600px;
                    max-width: 90%;
                    margin: 12px auto;
                    background: var(--ai-background);
                    border-radius: 16px;
                    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.12);
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                    transition: all 0.3s ease;
                    overflow: hidden;
                }}

                #ai-search-container {{
                    padding: 12px;
                    position: relative;
                }}

                .input-wrapper {{
                    position: relative;
                    display: flex;
                    align-items: center;
                }}

                #ai-search-input {{
                    width: 100%;
                    padding: 12px 40px 12px 16px;
                    border: 2px solid var(--ai-border);
                    border-radius: 12px;
                    font-size: 16px;
                    outline: none;
                    transition: all 0.2s ease;
                    background: var(--ai-secondary-bg);
                    box-sizing: border-box;
                    color: var(--ai-text);
                }}

                #ai-search-input:focus {{
                    border-color: var(--ai-primary-color);
                    background: var(--ai-background);
                    box-shadow: 0 0 0 4px var(--ai-primary-light);
                }}

                #ai-search-input::placeholder {{
                    color: var(--ai-secondary-text);
                }}

                .send-button, .stop-button {{
                    position: absolute;
                    right: 12px;
                    top: 50%;
                    transform: translateY(-50%);
                    background: none;
                    border: none;
                    cursor: pointer;
                    padding: 8px;
                    border-radius: 8px;
                    transition: all 0.2s ease;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }}

                .stop-button {{
                    display: none;
                }}

                .stop-button.active {{
                    display: flex;
                }}

                .send-button.hidden {{
                    display: none;
                }}

                .send-button:hover, .stop-button:hover {{
                    background: var(--ai-secondary-bg);
                }}

                .send-icon, .stop-icon {{
                    width: 20px;
                    height: 20px;
                    fill: var(--ai-primary-color);
                }}

                #ai-search-results {{
                    display: none;
                    padding: 20px;
                    max-height: 500px;
                    overflow-y: auto;
                    border-top: 1px solid var(--ai-border);
                    margin-top: 20px;
                }}

                #ai-search-results.active {{
                    display: block;
                }}

                .message {{
                    margin-bottom: 20px;
                    line-height: 1.6;
                    font-size: 15px;
                    color: var(--ai-text);
                }}

                .message:last-child {{
                    margin-bottom: 0;
                }}

                .message-content {{
                    padding: 16px 20px;
                    border-radius: 12px;
                    background: var(--ai-primary-light);
                    font-size: 15px;
                    line-height: 1.6;
                }}

                /* Markdown styles */
                .message-content pre {{
                    background: var(--ai-background);
                    border-radius: 8px;
                    padding: 12px 16px;
                    overflow-x: auto;
                    margin: 8px 0;
                }}

                .message-content code {{
                    font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
                    font-size: 13px;
                    background: var(--ai-background);
                    padding: 2px 4px;
                    border-radius: 4px;
                }}

                .message-content p {{
                    margin: 0 0 12px 0;
                }}

                .message-content p:last-child {{
                    margin-bottom: 0;
                }}

                .message-content ul, 
                .message-content ol {{
                    margin: 8px 0;
                    padding-left: 24px;
                }}

                .message-content li {{
                    margin: 4px 0;
                }}

                .message-content a {{
                    color: var(--ai-primary-color);
                    text-decoration: none;
                }}

                .message-content a:hover {{
                    text-decoration: underline;
                }}

                .message-content blockquote {{
                    border-left: 4px solid var(--ai-border);
                    margin: 8px 0;
                    padding-left: 16px;
                    color: var(--ai-secondary-text);
                }}

                .message-content table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 12px 0;
                }}

                .message-content th,
                .message-content td {{
                    border: 1px solid var(--ai-border);
                    padding: 8px 12px;
                    text-align: left;
                }}

                .message-content th {{
                    background: var(--ai-secondary-bg);
                }}

                #typing-indicator {{
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 20px;
                }}

                .generating {{
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    padding: 16px 20px;
                    background: var(--ai-primary-light);
                    border-radius: 12px;
                    color: var(--ai-primary-color);
                }}

                .typing-animation {{
                    display: flex;
                    align-items: center;
                    gap: 4px;
                }}

                .typing-dot {{
                    width: 4px;
                    height: 4px;
                    background: currentColor;
                    border-radius: 50%;
                    animation: typingAnimation 1.4s infinite;
                    opacity: 0.3;
                }}

                .typing-dot:nth-child(1) {{ animation-delay: 0s; }}
                .typing-dot:nth-child(2) {{ animation-delay: 0.2s; }}
                .typing-dot:nth-child(3) {{ animation-delay: 0.4s; }}

                @keyframes typingAnimation {{
                    0% {{ opacity: 0.3; transform: translateY(0); }}
                    50% {{ opacity: 1; transform: translateY(-4px); }}
                    100% {{ opacity: 0.3; transform: translateY(0); }}
                }}

                #ai-search-results::-webkit-scrollbar {{
                    width: 8px;
                }}

                #ai-search-results::-webkit-scrollbar-track {{
                    background: transparent;
                }}

                #ai-search-results::-webkit-scrollbar-thumb {{
                    background: var(--ai-border);
                    border-radius: 4px;
                }}

                #ai-search-results::-webkit-scrollbar-thumb:hover {{
                    background: var(--ai-secondary-text);
                }}
            </style>
        `;

        const widgetHtml = `
            <div id="ai-search-widget">
                <div id="ai-search-container">
                    <div class="input-wrapper">
                        <input type="text" id="ai-search-input" placeholder="Ask anything..." autocomplete="off">
                        <button class="send-button" aria-label="Send message">
                            <svg class="send-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                            </svg>
                        </button>
                        <button class="stop-button" aria-label="Stop generation">
                            <svg class="stop-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                <path d="M6 6h12v12H6z"/>
                            </svg>
                        </button>
                    </div>
                    <div id="ai-search-results"></div>
                </div>
            </div>
        `;

        // Inject styles and widget HTML
        document.head.insertAdjacentHTML('beforeend', styles);
        document.currentScript.insertAdjacentHTML('afterend', widgetHtml);

        let threadId = null;
        let currentRunId = null;
        let isGenerating = false;
        const widget = document.getElementById('ai-search-widget');
        const input = document.getElementById('ai-search-input');
        const results = document.getElementById('ai-search-results');
        const sendButton = document.querySelector('.send-button');
        const stopButton = document.querySelector('.stop-button');

        // Add click event listener to document
        document.addEventListener('click', async (e) => {{
            const isClickInside = widget.contains(e.target);
            
            if (!isClickInside) {{
                // If there's an ongoing generation, stop it
                if (isGenerating) {{
                    await stopGeneration();
                }}
                
                // Clear results and remove active class
                results.innerHTML = '';
                results.classList.remove('active');
                input.value = '';
                threadId = null; // Reset thread ID to start fresh conversation
                currentRunId = null;
                isGenerating = false;
                stopButton.classList.remove('active');
                sendButton.classList.remove('hidden');
            }}
        }});

        // Prevent clicks inside widget from bubbling to document
        widget.addEventListener('click', (e) => {{
            e.stopPropagation();
        }});

        async function stopGeneration() {{
            if (currentRunId) {{
                try {{
                    await fetch('/api/stop', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ run_id: currentRunId }})
                    }});
                    
                    // Reset UI
                    stopButton.classList.remove('active');
                    sendButton.classList.remove('hidden');
                    isGenerating = false;
                    currentRunId = null;
                }} catch (error) {{
                    console.error('Error stopping generation:', error);
                }}
            }}
        }}

        async function handleQuery() {{
            if (isGenerating) return;
            
            const query = input.value.trim();
            if (!query) return;
            
            isGenerating = true;
            input.value = '';
            results.classList.add('active');
            stopButton.classList.add('active');
            sendButton.classList.add('hidden');

            results.innerHTML = `
                <div id="typing-indicator">
                    <div class="generating">
                        <div class="typing-animation">
                            <div class="typing-dot"></div>
                            <div class="typing-dot"></div>
                            <div class="typing-dot"></div>
                        </div>
                    </div>
                </div>
            `;

            try {{
                const response = await fetch('/api/query', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        client_id: clientId,
                        query: query,
                        thread_id: threadId
                    }})
                }});

                const data = await response.json();
                
                if (data.status === 'cancelled') {{
                    results.innerHTML = `
                        <div class="message">
                            <div class="message-content">
                                Generation stopped.
                            </div>
                        </div>
                    `;
                    return;
                }}
                
                threadId = data.thread_id;
                currentRunId = data.run_id;

                // Initialize for typing effect
                results.innerHTML = `<div class="message"><div class="message-content"></div></div>`;
                const messageContent = results.querySelector('.message-content');
                const response_text = data.response;
                let charIndex = 0;
                let markdown = '';
                
                function typeNextChar() {{
                    if (charIndex < response_text.length && isGenerating) {{
                        markdown += response_text[charIndex];
                        // Render markdown as we type
                        messageContent.innerHTML = marked.parse(markdown, {{
                            breaks: true,
                            gfm: true
                        }});
                        charIndex++;
                        results.scrollTop = results.scrollHeight;
                        setTimeout(typeNextChar, Math.random() * 20 + 10);
                    }} else {{
                        // Reset UI when typing is complete or stopped
                        stopButton.classList.remove('active');
                        sendButton.classList.remove('hidden');
                        isGenerating = false;
                        currentRunId = null;
                    }}
                }}
                
                // Wait for marked.js to load before starting
                if (typeof marked === 'undefined') {{
                    markedScript.onload = () => {{
                        marked.setOptions({{
                            highlight: function(code, lang) {{
                                return code;
                            }}
                        }});
                        typeNextChar();
                    }};
                }} else {{
                    typeNextChar();
                }}

            }} catch (error) {{
                console.error('Error:', error);
                results.innerHTML = `
                    <div class="message">
                        <div class="message-content" style="color: var(--ai-error-color, #dc2626);">
                            Sorry, there was an error generating the response.
                        </div>
                    </div>
                `;
                stopButton.classList.remove('active');
                sendButton.classList.remove('hidden');
                isGenerating = false;
                currentRunId = null;
            }}
        }}

        input.addEventListener('keypress', (e) => {{
            if (e.key === 'Enter' && !isGenerating) {{
                handleQuery();
            }}
        }});

        sendButton.addEventListener('click', handleQuery);
        stopButton.addEventListener('click', stopGeneration);
    }})();
    """ 